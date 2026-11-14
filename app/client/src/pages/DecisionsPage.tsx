import {
  Alert, AlertDescription, AlertTitle, Card, CardContent, CardDescription, CardHeader, CardTitle, Empty, EmptyDescription,
  EmptyHeader, EmptyTitle, Skeleton, Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@databricks/appkit-ui/react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router';
import { Kpi } from '../components/Kpi';
import { api, type Row } from '../lib/api';
import { int, money, pct, signedMoney, toNum, when, text } from '../lib/format';
import { StatusBadge } from './QueuePage';

type Data = { rows: Row[]; summary: Row; reasons: Row[] };

export function DecisionsPage() {
  const [data, setData] = useState<Data | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { api<Data>('/api/decisions').then(setData).catch((e: Error) => setErr(e.message)); }, []);

  if (err) return <Alert variant="destructive"><AlertTitle>Decision log unavailable</AlertTitle><AlertDescription>{err}</AlertDescription></Alert>;
  if (!data) return <Skeleton className="h-96 w-full" />;
  const s = data.summary;
  const n = toNum(s.decisions);
  const overrideRate = n ? toNum(s.overridden) / n : 0;

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-semibold text-foreground">
          {n ? `${pct(overrideRate, 0)} of ${int(n)} pricing decisions overrode the model` : 'Pricing decisions'}
        </h2>
        <p className="text-sm text-muted-foreground">
          Every decision is written to Lakebase (<code>pricing_ops.pricing_decisions</code>) and streamed by Lakehouse Sync into Unity Catalog
          (<code>lb_pricing_decisions_history</code>) — ask Genie about it, or use it to retrain the model.
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi title="Decisions" value={int(n)} sub={`${int(s.accepted)} accepted · ${int(s.overridden)} overridden`} source="pricing_ops.pricing_decisions" />
        <Kpi title="Override rate" value={pct(overrideRate, 0)} sub="share of decisions where the manager disagreed" source="pricing_ops.pricing_decisions" />
        <Kpi title="Discount committed" value={money(s.total_discount_committed)} sub={`${signedMoney(s.override_delta_total)} vs Model/DS values`} source="final_discount" />
        <Kpi title="Expected profit of overrides vs model" value={signedMoney(s.override_expected_profit_gap)}
          tone={toNum(s.override_expected_profit_gap) >= 0 ? 'good' : 'bad'} sub="model's own view of each checked override" source="override_expected_profit" />
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">Why managers override</CardTitle><CardDescription>Overrides by reason and average gap to the Model/DS value</CardDescription></CardHeader>
        <CardContent>
          {data.reasons.length === 0 ? <p className="text-sm text-muted-foreground">No overrides yet.</p> : (
            <Table>
              <TableHeader><TableRow><TableHead>Reason</TableHead><TableHead className="text-right">Overrides</TableHead><TableHead className="text-right">Avg override − model</TableHead></TableRow></TableHeader>
              <TableBody>
                {data.reasons.map((r) => (
                  <TableRow key={text(r.reason)}><TableCell>{text(r.reason)}</TableCell><TableCell className="text-right">{int(r.n)}</TableCell>
                    <TableCell className="text-right tabular-nums">{signedMoney(r.avg_delta)}</TableCell></TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-base">Latest decisions</CardTitle></CardHeader>
        <CardContent>
          {data.rows.length === 0 ? (
            <Empty><EmptyHeader><EmptyTitle>No decisions yet</EmptyTitle>
              <EmptyDescription>Open a unit in the <Link className="underline" to="/queue">pricing queue</Link> and accept or override the Model/DS value.</EmptyDescription></EmptyHeader></Empty>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>When</TableHead><TableHead>Unit</TableHead><TableHead>Decision</TableHead><TableHead className="text-right">Model/DS value</TableHead>
                  <TableHead className="text-right">Override value</TableHead><TableHead>Reason</TableHead><TableHead>By</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.rows.map((r) => (
                  <TableRow key={text(r.decision_id)}>
                    <TableCell className="text-xs">{when(r.decided_at)}</TableCell>
                    <TableCell><Link className="underline" to={`/vehicle/${text(r.vin)}`}>{text(r.stock_number)}</Link>
                      <div className="text-xs text-muted-foreground">{int(r.days_in_stock)} days · {money(r.list_price_before)}</div></TableCell>
                    <TableCell><StatusBadge status={text(r.decision)} /></TableCell>
                    <TableCell className="text-right tabular-nums">{money(r.model_value)}</TableCell>
                    <TableCell className="text-right tabular-nums">{r.override_value === null ? '—' : money(r.override_value)}</TableCell>
                    <TableCell className="text-sm">{r.reason_label ? text(r.reason_label) : '—'}{r.reason_text ? <div className="text-xs text-muted-foreground">{text(r.reason_text)}</div> : null}</TableCell>
                    <TableCell className="text-xs">{text(r.decided_by)}</TableCell>
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
