import {
  Alert, AlertDescription, AlertTitle, Badge, Button, Card, CardContent, CardDescription, CardFooter, CardHeader,
  CardTitle, Input, Label, LineChart, RadioGroup, RadioGroupItem, Select, SelectContent, SelectItem, SelectTrigger,
  SelectValue, Separator, Skeleton, Spinner, Table, TableBody, TableCell, TableHead, TableHeader, TableRow, Textarea,
} from '@databricks/appkit-ui/react';
import { ArrowLeft, ShieldCheck, Sparkles, Zap } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router';
import { VehiclePhoto } from '../components/VehiclePhoto';
import { api, ApiError, type Row } from '../lib/api';
import { days, int, label, money, pct, ptmLabel, signedMoney, toNum, when, text } from '../lib/format';
import { StatusBadge } from './QueuePage';

type Detail = { vehicle: Row; batch: Row | null; rationale: Row | null; rationaleSuppressed: boolean; segments: Row[]; history: Row[] };
type Live = { prediction: Row; curve: Row[]; latencyMs: number; endpoint: string };

function Stat({ label: l, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div>
      <div className="text-xs text-muted-foreground">{l}</div>
      <div className="text-lg font-semibold tabular-nums">{value}</div>
      {sub && <div className="text-xs text-muted-foreground">{sub}</div>}
    </div>
  );
}

export function VehiclePage() {
  const { vin = '' } = useParams();
  const [detail, setDetail] = useState<Detail | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [live, setLive] = useState<Live | null>(null);
  const [liveErr, setLiveErr] = useState<string | null>(null);
  const [liveReq, setLiveReq] = useState(0);
  const [liveDone, setLiveDone] = useState(-1);
  const liveLoading = liveReq !== liveDone;
  const [reasons, setReasons] = useState<Row[]>([]);
  const [mode, setMode] = useState<'accept' | 'override'>('accept');
  const [overrideValue, setOverrideValue] = useState('');
  const [reasonCode, setReasonCode] = useState('');
  const [reasonText, setReasonText] = useState('');
  const [check, setCheck] = useState<Row | null>(null);
  const [checking, setChecking] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState<string | null>(null);
  const [saveErr, setSaveErr] = useState<string | null>(null);

  const load = useCallback(() => {
    api<Detail>(`/api/vehicle/${vin}`).then((d) => { setDetail(d); setErr(null); }).catch((e: Error) => setErr(e.message));
  }, [vin]);

  const askModel = () => setLiveReq((n) => n + 1);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    let cancelled = false;
    api<Live>('/api/recommend', { method: 'POST', body: JSON.stringify({ vin }) })
      .then((r) => { if (!cancelled) { setLive(r); setLiveErr(null); } })
      .catch((e: ApiError) => { if (!cancelled) setLiveErr(e.message); })
      .finally(() => { if (!cancelled) setLiveDone(liveReq); });
    return () => { cancelled = true; };
  }, [vin, liveReq]);
  useEffect(() => { api<Row[]>('/api/reasons').then(setReasons).catch(() => setReasons([])); }, []);

  if (err) return <Alert variant="destructive"><AlertTitle>Vehicle unavailable</AlertTitle><AlertDescription>{err}</AlertDescription></Alert>;
  if (!detail) return <Skeleton className="h-[600px] w-full" />;

  const v = detail.vehicle;
  const src = live?.prediction ?? detail.batch ?? {};
  const isLive = Boolean(live);
  const modelValue = toNum(src.recommended_discount);
  const price = toNum(v.current_price);
  const ov = overrideValue === '' ? null : Number(overrideValue);
  const ovValid = ov !== null && Number.isFinite(ov) && ov >= 0 && ov <= 0.15 * price && ov !== modelValue;
  const canSubmit = mode === 'accept' ? Boolean(src.recommended_discount !== undefined) : ovValid && Boolean(reasonCode) && (reasonCode !== 'other' || reasonText.trim().length >= 5);
  const curveData = (live?.curve ?? []).map((c) => ({
    discount: `$${int(c.discount)}`, expected_profit: toNum(c.expected_profit), expected_days: toNum(c.expected_days_to_sell),
  }));

  const checkOverride = () => {
    if (!ovValid || ov === null) return;
    setChecking(true);
    api<Live>('/api/recommend', { method: 'POST', body: JSON.stringify({ vin, priceOverride: price - ov }) })
      .then((r) => setCheck(r.prediction))
      .catch((e: ApiError) => setSaveErr(`Could not check the override with the model: ${e.message}`))
      .finally(() => setChecking(false));
  };

  const submit = () => {
    setSaving(true);
    setSaveErr(null);
    const body = {
      vin,
      decision: mode === 'accept' ? 'accepted' : 'overridden',
      model: {
        value: modelValue, version: text(src.model_version ?? 'unknown'), source: isLive ? 'realtime_endpoint' : 'batch_score',
        expectedProfit: src.expected_profit_recommended === undefined ? null : toNum(src.expected_profit_recommended),
        pSell30d: src.p_sell_30d_recommended === undefined ? null : toNum(src.p_sell_30d_recommended),
      },
      overrideValue: mode === 'override' ? ov : null,
      overrideExpectedProfit: mode === 'override' && check ? toNum(check.expected_profit_now) : null,
      reasonCode: mode === 'override' ? reasonCode : null,
      reasonText,
    };
    api<Row>('/api/decisions', { method: 'POST', body: JSON.stringify(body) })
      .then((r) => {
        setSaved(`Decision #${text(r.decision_id)} saved: ${label(r.decision)} — final discount ${money(r.final_discount)}. Synced to Unity Catalog via Lakehouse Sync.`);
        setOverrideValue(''); setReasonCode(''); setReasonText(''); setCheck(null); setMode('accept');
        load();
      })
      .catch((e: ApiError) => setSaveErr(e.message))
      .finally(() => setSaving(false));
  };

  const credit = v.image_author ? `Photo: ${text(v.image_author).slice(0, 60)} · ${text(v.image_licence)} · Wikimedia Commons (representative of model)` : undefined;
  const latest = detail.history[0];

  return (
    <div className="space-y-4">
      <Link to="/queue" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" /> Pricing queue
      </Link>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        {/* ---- vehicle facts ---- */}
        <Card>
          <CardHeader>
            <CardTitle className="text-xl">{text(v.model_year)} {text(v.make)} {text(v.model)} {text(v.trim)}</CardTitle>
            <CardDescription>
              {text(v.stock_number)} · {text(v.rooftop_name)} · {text(v.condition)} · {text(v.exterior_colour)} · {int(v.mileage)} mi · VIN {text(v.vin)}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <VehiclePhoto file={text(v.image_file)} alt={`${text(v.make)} ${text(v.model)}`} credit={credit} />
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              <Stat label="Days in stock" value={int(v.days_in_stock)} sub={`band ${text(v.aging_bucket)}`} />
              <Stat label="List price" value={money(price)} sub={toNum(v.total_discount) ? `already −${money(v.total_discount)}` : 'no cuts yet'} />
              <Stat label="Market price" value={money(v.market_price)} sub={ptmLabel(v.price_to_market)} />
              <Stat label="Holding cost" value={`${money(v.daily_holding_cost)}/day`} sub={`${money(v.carrying_cost_to_date)} carried so far`} />
              <Stat label="Front gross at list" value={money(v.front_gross_at_current_price)} sub={`unit cost ${money(v.unit_cost)}`} />
              <Stat label="Web demand, 4 weeks" value={`${int(v.vdp_views_4w)} views`} sub={`${int(v.leads_4w)} leads · ${int(v.test_drives_4w)} test drives`} />
            </div>
          </CardContent>
        </Card>

        {/* ---- live model ---- */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Model/DS value
              {isLive ? <Badge variant="secondary"><Zap className="mr-1 h-3 w-3" />live · {int(live?.latencyMs)} ms</Badge>
                : <Badge variant="outline">overnight batch</Badge>}
              <Badge variant="outline">model v{text(src.model_version ?? '?')}</Badge>
            </CardTitle>
            <CardDescription>
              Profit-optimal extra discount from the real-time endpoint <code>{live?.endpoint ?? 'piag-pricing-model'}</code>, after
              floor-plan, lot and depreciation cost and auction-exit risk, within pricing guardrails.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {liveErr && <Alert><AlertDescription>{liveErr}</AlertDescription></Alert>}
            {liveLoading && !live ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground"><Spinner /> Asking the model… (first call can take ~30 s while the endpoint wakes)</div>
            ) : null}
            <div className="flex flex-wrap items-end gap-6">
              <div>
                <div className="text-xs text-muted-foreground">Recommended</div>
                <div className="text-4xl font-semibold tabular-nums">{modelValue === 0 ? 'Hold price' : `−${money(modelValue)}`}</div>
                <div className="text-sm text-muted-foreground">new list {money(src.recommended_price ?? price)}</div>
              </div>
              <Stat label="Chance to sell in 30 days" value={pct(src.p_sell_30d_recommended, 0)} sub={`${pct(src.p_sell_30d_now, 0)} at today's price`} />
              <Stat label="Expected days to sell" value={days(src.expected_days_to_sell_recommended)} sub={`${days(src.expected_days_to_sell_now)} at today's price`} />
              <Stat label="Expected profit" value={money(src.expected_profit_recommended)}
                sub={`${signedMoney(src.uplift_vs_flat_rule)} vs flat rule (${toNum(src.flat_rule_discount) ? `−${money(src.flat_rule_discount)}` : 'no cut'})`} />
            </div>
            {src.guardrail_applied === true && (
              <p className="flex items-center gap-1 text-sm text-muted-foreground">
                <ShieldCheck className="h-4 w-4" /> Capped by pricing guardrail — unconstrained optimum would be −{money(src.unconstrained_discount)}.
              </p>
            )}
            {curveData.length > 0 && (
              <div>
                <div className="text-sm font-medium">Expected profit by discount (16-week horizon)</div>
                <LineChart data={curveData} xKey="discount" yKey="expected_profit" height={200} colorPalette="categorical"
                  ariaLabel="Expected profit for each candidate discount" valueFormatter={(x) => money(x)}
                  options={{ xAxis: { name: '' }, yAxis: { name: '' } }} />
              </div>
            )}
            <Button variant="outline" size="sm" onClick={askModel} disabled={liveLoading}>{liveLoading ? 'Asking…' : 'Ask the model again'}</Button>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* ---- decision ---- */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">Pricing decision {latest && <StatusBadge status={text(latest.decision)} />}</CardTitle>
            <CardDescription>Accept the Model/DS value, or override it with your value and a reason. Saved to Lakebase; the reason teaches the next model.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <RadioGroup value={mode} onValueChange={(x) => { setMode(x as 'accept' | 'override'); setCheck(null); }}>
              <div className="flex items-center gap-2">
                <RadioGroupItem value="accept" id="accept" />
                <Label htmlFor="accept">Accept Model/DS value ({modelValue === 0 ? 'hold price' : `−${money(modelValue)}`})</Label>
              </div>
              <div className="flex items-center gap-2">
                <RadioGroupItem value="override" id="override" />
                <Label htmlFor="override">Override</Label>
              </div>
            </RadioGroup>
            {mode === 'override' && (
              <div className="space-y-3 rounded-md border p-3">
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="space-y-1">
                    <Label htmlFor="ov">Override value (discount, USD)</Label>
                    <Input id="ov" type="number" min={0} step={50} value={overrideValue} placeholder="e.g. 750"
                      onChange={(e) => { setOverrideValue(e.target.value); setCheck(null); }} />
                    {ov !== null && !ovValid && (
                      <p className="text-xs text-destructive">
                        {ov === modelValue ? 'Same as the model value — choose Accept instead.' : `Enter 0 – ${money(0.15 * price)} (15% cap).`}
                      </p>
                    )}
                  </div>
                  <div className="space-y-1">
                    <Label>Reason</Label>
                    <Select value={reasonCode} onValueChange={setReasonCode}>
                      <SelectTrigger aria-label="Override reason"><SelectValue placeholder="Choose a reason" /></SelectTrigger>
                      <SelectContent>
                        {reasons.map((r) => <SelectItem key={text(r.reason_code)} value={text(r.reason_code)}>{text(r.label)}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="space-y-1">
                  <Label htmlFor="notes">Notes {reasonCode === 'other' ? '(required)' : '(optional)'}</Label>
                  <Textarea id="notes" rows={2} value={reasonText} onChange={(e) => setReasonText(e.target.value)} placeholder="What does the model not know?" />
                </div>
                <Button variant="outline" size="sm" onClick={checkOverride} disabled={!ovValid || checking}>
                  {checking ? 'Checking…' : 'Check my override with the model'}
                </Button>
                {check && (
                  <p className="text-sm">
                    At −{money(ov)} the model expects <b>{money(check.expected_profit_now)}</b> profit and a sale in ~{days(check.expected_days_to_sell_now)}
                    {' '}vs <b>{money(src.expected_profit_recommended)}</b> for the Model/DS value
                    {' '}(<span className={toNum(check.expected_profit_now) >= toNum(src.expected_profit_recommended) ? 'text-success' : 'text-warning'}>
                      {signedMoney(toNum(check.expected_profit_now) - toNum(src.expected_profit_recommended))}</span>).
                  </p>
                )}
              </div>
            )}
            {mode === 'accept' && (
              <div className="space-y-1">
                <Label htmlFor="notes2">Notes (optional)</Label>
                <Textarea id="notes2" rows={2} value={reasonText} onChange={(e) => setReasonText(e.target.value)} />
              </div>
            )}
            {saveErr && <Alert variant="destructive"><AlertDescription>{saveErr}</AlertDescription></Alert>}
            {saved && <Alert><AlertDescription>{saved}</AlertDescription></Alert>}
          </CardContent>
          <CardFooter>
            <Button onClick={submit} disabled={!canSubmit || saving}>{saving ? 'Saving…' : mode === 'accept' ? 'Accept Model/DS value' : 'Save override'}</Button>
          </CardFooter>
        </Card>

        {/* ---- GenAI rationale + targeting ---- */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Sparkles className="h-4 w-4" /> Why, and who to target</CardTitle>
            <CardDescription>AI-written from the overnight model facts (Claude Haiku via AI Functions); every number checked against the facts.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {detail.rationale ? (
              <>
                <p className="text-sm">{text(detail.rationale.rationale)}</p>
                <Separator />
                <div className="text-sm">
                  <div className="font-medium">{text(detail.rationale.promo_headline)}</div>
                  <p className="text-muted-foreground">{text(detail.rationale.promo_message)}</p>
                  <p className="mt-1 text-xs text-muted-foreground">Draft SMS for <b>{label(detail.rationale.top_segment)}</b> — review before sending.</p>
                </div>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">
                {detail.rationaleSuppressed ? 'AI rationale hidden: it failed the number check.' : 'No AI rationale (written for units 45+ days old).'}
              </p>
            )}
            <Separator />
            <div className="text-sm font-medium">Segments most likely to respond to a {label(v.body_class)} promotion</div>
            <Table>
              <TableHeader><TableRow><TableHead>Segment</TableHead><TableHead className="text-right">Leads / 1,000 sends</TableHead><TableHead className="text-right">Lift</TableHead></TableRow></TableHeader>
              <TableBody>
                {detail.segments.map((s) => (
                  <TableRow key={text(s.segment)}>
                    <TableCell>{label(s.segment)}</TableCell>
                    <TableCell className="text-right tabular-nums">{toNum(s.leads_per_1000_sends).toFixed(1)}</TableCell>
                    <TableCell className="text-right tabular-nums">{toNum(s.lift_vs_body_class_avg).toFixed(2)}×</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <p className="text-[11px] text-muted-foreground">Source: segment_targeting (campaign responses) · AI-generated text — verify before use.</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">Decision history for this unit</CardTitle></CardHeader>
        <CardContent>
          {detail.history.length === 0 ? <p className="text-sm text-muted-foreground">No decisions yet.</p> : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>When</TableHead><TableHead>Decision</TableHead><TableHead className="text-right">Model/DS value</TableHead>
                  <TableHead className="text-right">Override value</TableHead><TableHead>Reason</TableHead><TableHead>By</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {detail.history.map((h) => (
                  <TableRow key={text(h.decision_id)}>
                    <TableCell>{when(h.decided_at)}</TableCell>
                    <TableCell><StatusBadge status={text(h.decision)} /></TableCell>
                    <TableCell className="text-right tabular-nums">{money(h.model_value)} <span className="text-xs text-muted-foreground">v{text(h.model_version)}</span></TableCell>
                    <TableCell className="text-right tabular-nums">{h.override_value === null ? '—' : money(h.override_value)}</TableCell>
                    <TableCell>{h.reason_code ? label(h.reason_code) : '—'}{h.reason_text ? ` · ${text(h.reason_text)}` : ''}</TableCell>
                    <TableCell className="text-xs">{text(h.decided_by)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
