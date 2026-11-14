import { createApp, analytics, files, genie, lakebase, server, serving } from '@databricks/appkit';
import type { Request } from 'express';
import { z } from 'zod';

/**
 * Pacific Isles Auto Group — aged-inventory pricing copilot.
 * Reads:  Lakebase `serving.*` (published from governed Unity Catalog gold tables) for low-latency lookups,
 *         SQL warehouse (config/queries) for KPIs and charts.
 * Model:  real-time Model Serving endpoint `piag-pricing-model` (hazard model + profit optimiser).
 * Writes: Lakebase `pricing_ops.pricing_decisions` — Model/DS value vs override value + reason; Lakehouse Sync
 *         streams every change back into Unity Catalog.
 */
const AS_OF = process.env.PIAG_AS_OF_DATE ?? '2026-11-13';
const MEDIA_PREFIX = '/Volumes/serverless_stable_69fppe_catalog/piag_pricing/media/';

type Row = Record<string, unknown>;
const isRecord = (v: unknown): v is Row => typeof v === 'object' && v !== null && !Array.isArray(v);
const num = (v: unknown): number => (typeof v === 'number' ? v : Number(v ?? 0));
const str = (v: unknown): string =>
  typeof v === 'string' ? v
    : typeof v === 'number' || typeof v === 'boolean' || typeof v === 'bigint' ? `${v}`
      : v instanceof Date ? v.toISOString() // pg returns DATE/TIMESTAMP columns as Date objects
        : v == null ? '' : JSON.stringify(v);

function whoAmI(req: Request) {
  const email = req.header('x-forwarded-email') ?? req.header('x-forwarded-preferred-username') ?? 'local-dev@databricks.com';
  return { email, user: req.header('x-forwarded-user') ?? email };
}

/** Columns the pricing pyfunc expects (see ml/pyfunc_model.py INPUT_COLUMNS). */
const MODEL_INPUT = [
  'vin', 'current_price', 'unit_cost', 'market_price', 'daily_market_depreciation', 'daily_holding_cost',
  'flat_rule_additional_discount', 'days_in_stock', 'model_year', 'mileage', 'market_days_supply',
  'vdp_views_last_week', 'leads_last_week', 'test_drives_last_week', 'weeks_listed', 'condition', 'body_class',
  'make', 'model', 'exterior_colour', 'rooftop_id', 'as_of_date',
] as const;
const INT_COLS = new Set(['days_in_stock', 'model_year', 'mileage', 'vdp_views_last_week', 'leads_last_week', 'test_drives_last_week', 'weeks_listed']);
const TEXT_COLS = new Set(['vin', 'condition', 'body_class', 'make', 'model', 'exterior_colour', 'rooftop_id', 'as_of_date']);

function modelRecord(inv: Row, priceOverride: number | null): Row {
  const rec: Row = {};
  for (const c of MODEL_INPUT) {
    const v = inv[c];
    if (TEXT_COLS.has(c)) rec[c] = c === 'as_of_date' ? str(v).slice(0, 10) || AS_OF : str(v);
    else if (INT_COLS.has(c)) rec[c] = Math.round(num(v));
    else rec[c] = num(v);
  }
  rec.price_override = priceOverride;
  return rec;
}

/** Serving may return the raw body or an ExecutionResult wrapper. */
function predictionsOf(result: unknown): Row[] {
  let body: unknown = result;
  if (isRecord(body) && 'ok' in body) {
    if (body.ok === false) throw new Error(`model endpoint call failed (status ${str(body.status ?? 'unknown')})`);
    body = body.data;
  }
  if (isRecord(body) && Array.isArray(body.predictions)) return body.predictions.filter(isRecord);
  throw new Error('unexpected model endpoint response');
}

const imageFile = (p: unknown) => str(p).replace(MEDIA_PREFIX, '');

const RecommendBody = z.object({
  vin: z.string().min(11).max(17),
  priceOverride: z.number().positive().max(500000).nullable().default(null),
});

const DecisionBody = z.object({
  vin: z.string().min(11).max(17),
  decision: z.enum(['accepted', 'overridden', 'held']),
  model: z.object({
    value: z.number().min(0).max(20000),
    version: z.string().min(1).max(20),
    source: z.enum(['realtime_endpoint', 'batch_score']),
    expectedProfit: z.number().nullable(),
    pSell30d: z.number().min(0).max(1).nullable(),
  }),
  overrideValue: z.number().min(0).max(20000).nullable().default(null),
  overrideExpectedProfit: z.number().nullable().default(null),
  reasonCode: z.string().max(40).nullable().default(null),
  reasonText: z.string().max(1000).default(''),
});

createApp({
  plugins: [analytics(), files({ volumes: { files: { policy: files.policy.publicRead() } } }), genie(), lakebase(), server(), serving()],
  onPluginsReady(appkit) {
    /** Lakebase query with rows narrowed to plain records. */
    const pg = async (text: string, params: unknown[] = []): Promise<{ rows: Row[] }> => {
      const r: unknown = await appkit.lakebase.query(text, params);
      const rows: unknown = isRecord(r) ? r.rows : [];
      return { rows: Array.isArray(rows) ? rows.filter(isRecord) : [] };
    };

    appkit.server.extend((app) => {
      app.get('/api/whoami', (req, res) => {
        res.json({ ...whoAmI(req), asOf: AS_OF, genieRunsAs: 'signed-in user (on-behalf-of)', dataRunsAs: 'app service principal' });
      });

      app.get('/api/rooftops', async (_req, res) => {
        try {
          const r = await pg('SELECT rooftop_id, rooftop_name FROM serving.rooftops ORDER BY rooftop_id');
          res.json(r.rows);
        } catch (e) {
          res.status(503).json({ error: 'Rooftops unavailable', detail: (e as Error).message });
        }
      });

      app.get('/api/reasons', async (_req, res) => {
        try {
          const r = await pg('SELECT reason_code, label FROM pricing_ops.override_reasons ORDER BY sort_order');
          res.json(r.rows);
        } catch (e) {
          res.status(503).json({ error: 'Override reasons unavailable', detail: (e as Error).message });
        }
      });

      // ---- Pricing queue: every aged unit, model value vs flat rule, latest decision -----------------
      app.get('/api/queue', async (req, res) => {
        const rooftop = str(req.query.rooftop);
        const bucket = str(req.query.bucket);
        const status = str(req.query.status);
        const minAge = Math.max(0, Math.min(400, Number(req.query.minAge ?? 45) || 0));
        const limit = Math.max(1, Math.min(200, Number(req.query.limit ?? 50) || 50));
        const offset = Math.max(0, Number(req.query.offset ?? 0) || 0);
        try {
          const r = await pg(
            `WITH latest AS (
               SELECT DISTINCT ON (vin) vin, decision, final_discount, decided_by, decided_at
               FROM pricing_ops.pricing_decisions ORDER BY vin, decided_at DESC)
             SELECT r.vin, r.stock_number, r.rooftop_id, r.rooftop_name, r.make, r.model, r.trim, r.model_year,
                    r.condition, r.days_in_stock, r.aging_bucket, r.current_price, r.price_to_market, r.daily_holding_cost,
                    r.recommended_discount, r.flat_rule_discount, r.uplift_vs_flat_rule, r.guardrail_applied,
                    r.expected_days_to_sell_now, r.expected_days_to_sell_recommended, r.model_version,
                    i.image_path, i.exterior_colour, coalesce(l.decision, 'pending') AS decision_status,
                    l.final_discount, l.decided_by, l.decided_at, count(*) OVER () AS total_rows
             FROM serving.recommendations r
             JOIN serving.inventory_current i USING (vin)
             LEFT JOIN latest l USING (vin)
             WHERE r.days_in_stock >= $1
               AND ($2 = '' OR r.rooftop_id = $2)
               AND ($3 = '' OR r.aging_bucket = $3)
               AND ($4 = '' OR coalesce(l.decision, 'pending') = $4)
             ORDER BY (l.decision IS NULL) DESC, r.uplift_vs_flat_rule DESC, r.days_in_stock DESC
             LIMIT $5 OFFSET $6`,
            [minAge, rooftop, bucket, status, limit, offset],
          );
          const rows: Row[] = r.rows.map((row: Row): Row => ({ ...row, image_file: imageFile(row.image_path) }));
          res.json({ rows, total: rows.length ? num(rows[0].total_rows) : 0, asOf: AS_OF });
        } catch (e) {
          res.status(503).json({ error: 'Pricing queue unavailable', detail: (e as Error).message });
        }
      });

      // ---- Vehicle detail: facts, batch recommendation, grounded rationale, target segments, history ----
      app.get('/api/vehicle/:vin', async (req, res) => {
        const vin = str(req.params.vin);
        try {
          const inv = await pg('SELECT * FROM serving.inventory_current WHERE vin = $1', [vin]);
          if (inv.rows.length === 0) {
            res.status(404).json({ error: 'Vehicle not on hand' });
            return;
          }
          const vehicle: Row = inv.rows[0];
          const [rec, rat, hist] = await Promise.all([
            pg('SELECT * FROM serving.recommendations WHERE vin = $1', [vin]),
            pg('SELECT rationale, promo_headline, promo_message, top_segment, second_segment, grounded, llm_model FROM serving.rationale WHERE vin = $1', [vin]),
            pg(`SELECT decision_id, decision, model_value, model_version, model_source, override_value, final_discount,
                       reason_code, reason_text, model_expected_profit, override_expected_profit, decided_by, decided_at
                FROM pricing_ops.pricing_decisions WHERE vin = $1 ORDER BY decided_at DESC LIMIT 20`, [vin]),
          ]);
          const segs = await pg(
            `SELECT segment, segment_rank, leads_per_1000_sends, lift_vs_body_class_avg, sends
             FROM serving.segment_targeting WHERE body_class = $1 ORDER BY segment_rank LIMIT 3`,
            [str(vehicle.body_class)],
          );
          const rationale: Row | null = rat.rows[0] ?? null;
          res.json({
            vehicle: { ...vehicle, image_file: imageFile(vehicle.image_path) },
            batch: rec.rows[0] ?? null,
            // ungrounded LLM text is never shown to a pricing manager
            rationale: rationale && rationale.grounded === true ? rationale : null,
            rationaleSuppressed: Boolean(rationale && rationale.grounded !== true),
            segments: segs.rows,
            history: hist.rows,
            asOf: AS_OF,
          });
        } catch (e) {
          res.status(503).json({ error: 'Vehicle unavailable', detail: (e as Error).message });
        }
      });

      // ---- Real-time model call (Model/DS value) incl. what-if on a different list price -------------
      app.post('/api/recommend', async (req, res) => {
        const parsed = RecommendBody.safeParse(req.body);
        if (!parsed.success) {
          res.status(400).json({ error: 'Invalid request', issues: parsed.error.issues });
          return;
        }
        const { vin, priceOverride } = parsed.data;
        try {
          const inv = await pg('SELECT * FROM serving.inventory_current WHERE vin = $1', [vin]);
          if (inv.rows.length === 0) {
            res.status(404).json({ error: 'Vehicle not on hand' });
            return;
          }
          const t0 = Date.now();
          // features come from the governed serving copy, never from the browser
          const raw: unknown = await appkit.serving().invoke({ dataframe_records: [modelRecord(inv.rows[0], priceOverride)] });
          const latencyMs = Date.now() - t0;
          const p = predictionsOf(raw)[0];
          let curve: unknown = [];
          try {
            curve = JSON.parse(str(p.curve_json));
          } catch {
            curve = [];
          }
          res.json({ prediction: { ...p, curve_json: undefined }, curve, latencyMs, endpoint: process.env.DATABRICKS_SERVING_ENDPOINT_NAME, priceOverride });
        } catch (e) {
          res.status(502).json({ error: 'Model endpoint unavailable — showing the overnight batch recommendation instead', detail: (e as Error).message });
        }
      });

      // ---- Record a pricing decision: Model/DS value vs Override value + Reason -----------------------
      app.post('/api/decisions', async (req, res) => {
        const parsed = DecisionBody.safeParse(req.body);
        if (!parsed.success) {
          res.status(400).json({ error: 'Invalid decision', issues: parsed.error.issues });
          return;
        }
        const d = parsed.data;
        try {
          const inv = await pg('SELECT vin, stock_number, rooftop_id, days_in_stock, current_price FROM serving.inventory_current WHERE vin = $1', [d.vin]);
          if (inv.rows.length === 0) {
            res.status(404).json({ error: 'Vehicle not on hand' });
            return;
          }
          const v: Row = inv.rows[0];
          const price = num(v.current_price);
          if (d.decision === 'overridden') {
            if (d.overrideValue === null || !d.reasonCode) {
              res.status(400).json({ error: 'An override needs an override value and a reason' });
              return;
            }
            if (d.overrideValue === d.model.value) {
              res.status(400).json({ error: 'Override value equals the model value — accept the model value instead' });
              return;
            }
            if (d.overrideValue > 0.15 * price) {
              res.status(400).json({ error: 'Override above 15% of list price needs group sign-off' });
              return;
            }
            if (d.reasonCode === 'other' && d.reasonText.trim().length < 5) {
              res.status(400).json({ error: "Reason 'Other' needs a short explanation" });
              return;
            }
            const ok = await pg('SELECT 1 FROM pricing_ops.override_reasons WHERE reason_code = $1', [d.reasonCode]);
            if (ok.rows.length === 0) {
              res.status(400).json({ error: 'Unknown reason code' });
              return;
            }
          }
          const finalDiscount = d.decision === 'accepted' ? d.model.value : d.decision === 'overridden' ? (d.overrideValue ?? 0) : 0;
          const r = await pg(
            `INSERT INTO pricing_ops.pricing_decisions
               (vin, stock_number, rooftop_id, days_in_stock, list_price_before, model_value, model_version, model_source,
                model_expected_profit, model_p_sell_30d, override_value, final_discount, decision, reason_code, reason_text,
                override_expected_profit, decided_by)
             VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17) RETURNING *`,
            [d.vin, str(v.stock_number), str(v.rooftop_id), num(v.days_in_stock), price, d.model.value, d.model.version,
              d.model.source, d.model.expectedProfit, d.model.pSell30d, d.decision === 'overridden' ? d.overrideValue : null,
              finalDiscount, d.decision, d.decision === 'overridden' ? d.reasonCode : null, d.reasonText.trim() || null,
              d.decision === 'overridden' ? d.overrideExpectedProfit : null, whoAmI(req).email],
          );
          res.status(201).json(r.rows[0]);
        } catch (e) {
          res.status(503).json({ error: 'Could not record the decision', detail: (e as Error).message });
        }
      });

      // ---- Decisions & impact ------------------------------------------------------------------------
      app.get('/api/decisions', async (_req, res) => {
        try {
          const [list, summary, reasons] = await Promise.all([
            pg(`SELECT d.decision_id, d.vin, d.stock_number, d.rooftop_id, d.days_in_stock, d.list_price_before, d.model_value,
                       d.model_version, d.override_value, d.final_discount, d.decision, d.reason_code, o.label AS reason_label,
                       d.reason_text, d.model_expected_profit, d.override_expected_profit, d.decided_by, d.decided_at
                FROM pricing_ops.pricing_decisions d LEFT JOIN pricing_ops.override_reasons o USING (reason_code)
                ORDER BY d.decided_at DESC LIMIT 100`),
            pg(`SELECT count(*) AS decisions, count(*) FILTER (WHERE decision = 'accepted') AS accepted,
                       count(*) FILTER (WHERE decision = 'overridden') AS overridden, count(*) FILTER (WHERE decision = 'held') AS held,
                       coalesce(sum(final_discount), 0) AS total_discount_committed,
                       coalesce(sum(final_discount - model_value) FILTER (WHERE decision = 'overridden'), 0) AS override_delta_total,
                       coalesce(sum(override_expected_profit - model_expected_profit) FILTER (WHERE decision = 'overridden'), 0) AS override_expected_profit_gap
                FROM pricing_ops.pricing_decisions`),
            pg(`SELECT coalesce(o.label, d.reason_code) AS reason, count(*) AS n, round(avg(d.final_discount - d.model_value)) AS avg_delta
                FROM pricing_ops.pricing_decisions d LEFT JOIN pricing_ops.override_reasons o USING (reason_code)
                WHERE d.decision = 'overridden' GROUP BY 1 ORDER BY n DESC`),
          ]);
          res.json({ rows: list.rows, summary: summary.rows[0], reasons: reasons.rows });
        } catch (e) {
          res.status(503).json({ error: 'Decision log unavailable', detail: (e as Error).message });
        }
      });
    });
  },
}).catch((error: unknown) => {
  // Fail fast: a half-started app that serves nothing must not report as healthy.
  console.error('[startup] AppKit failed to start', error);
  process.exit(1);
});
