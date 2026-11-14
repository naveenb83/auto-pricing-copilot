import {
  Alert, AlertDescription, AlertTitle, BarChart, Card, CardContent, CardDescription, CardHeader, CardTitle,
  LineChart, Skeleton, Table, TableBody, TableCell, TableHead, TableHeader, TableRow, useAnalyticsQuery,
} from '@databricks/appkit-ui/react';
import { Kpi } from '../components/Kpi';
import { int, money, pct, signedMoney, toNum, text } from '../lib/format';

const POLICY_LABEL: Record<string, string> = {
  flat_rule: 'Flat rule ($250 @45d / $500 @90d)',
  model_guardrails: 'Model + guardrails (this app)',
  model_unconstrained: 'Model, no guardrails',
};

export function OverviewPage() {
  const kpi = useAnalyticsQuery('kpi_overview');
  const rec = useAnalyticsQuery('model_vs_rule');
  const bt = useAnalyticsQuery('backtest_summary');
  const ag = useAnalyticsQuery('aging_by_rooftop');
  const top2 = [...(ag.data ?? [])].sort((a, b) => toNum(b['90+ days']) - toNum(a['90+ days'])).slice(0, 2);
  const k = kpi.data?.[0];
  const r = rec.data?.[0];
  const rule = bt.data?.find((x) => x.policy === 'flat_rule');
  const model = bt.data?.find((x) => x.policy === 'model_guardrails');
  const uplift120 = model && rule ? toNum(model.net_profit) - toNum(rule.net_profit) : null;
  const agedCut = model && rule && toNum(rule.aged90_day60) ? 1 - toNum(model.aged90_day60) / toNum(rule.aged90_day60) : null;

  if (kpi.error || rec.error) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Inventory KPIs unavailable</AlertTitle>
        <AlertDescription>{text(kpi.error ?? rec.error)} — the SQL warehouse may be starting; retry in a minute.</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-foreground">
          {k ? `${int(k.aged_90_plus)} units are 90+ days old and burn ${money(k.aged_holding_cost_per_day)} a day` : 'Aged inventory today'}
        </h2>
        <p className="text-sm text-muted-foreground">
          Business date 13 Nov 2026 · all six rooftops · governed KPIs from the Unity Catalog metric view <code>piag_pricing_kpis</code>
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi loading={kpi.loading} title="Units on hand" value={k ? int(k.units_on_hand) : '—'}
          sub={k ? `${int(k.aged_45_plus)} are 45+ days · avg ${Math.round(toNum(k.avg_days_in_stock))} days` : undefined}
          source="metric view · Units On Hand" />
        <Kpi loading={kpi.loading} tone="bad" title="Aged 90+ days" value={k ? pct(k.aged_90_share) : '—'}
          sub={k ? `${int(k.aged_90_plus)} units · target < 12%` : undefined} source="metric view · Aged 90+ Share" />
        <Kpi loading={kpi.loading} title="Holding cost per day" value={k ? money(k.holding_cost_per_day) : '—'}
          sub={k ? `${money(toNum(k.holding_cost_per_day) * 30)} / month · floor-plan + lot + depreciation` : undefined}
          source="metric view · Holding Cost Per Day" />
        <Kpi loading={rec.loading} tone="good" title="Expected profit vs flat rule" value={r ? signedMoney(r.expected_uplift_vs_rule) : '—'}
          sub={r ? `${int(r.recommend_cut)} cuts · ${int(r.recommend_hold)} holds · model v${text(r.model_version)}` : undefined}
          source="pricing_recommendations (batch score)" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>
            {uplift120 !== null && agedCut !== null
              ? `Replayed against today's lot, model pricing earns ${signedMoney(uplift120)} more in 120 days and cuts 90+ day stock ${pct(agedCut, 0)}`
              : 'Digital-twin backtest: model vs flat rule'}
          </CardTitle>
          <CardDescription>
            {"Today's lot replayed 120 days under the simulator's hidden buyer behaviour, 20 paired futures (same buyers in every arm)."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {bt.loading ? <Skeleton className="h-28 w-full" /> : bt.error ? (
            <Alert variant="destructive"><AlertDescription>Backtest results unavailable: {text(bt.error)}</AlertDescription></Alert>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Policy</TableHead><TableHead className="text-right">Net profit (120 d)</TableHead>
                  <TableHead className="text-right">Aged 90+ at day 60</TableHead><TableHead className="text-right">Carrying cost</TableHead>
                  <TableHead className="text-right">Auction exits</TableHead><TableHead className="text-right">Retail units</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(bt.data ?? []).map((p) => (
                  <TableRow key={p.policy} className={p.policy === 'model_guardrails' ? 'font-medium' : ''}>
                    <TableCell>{POLICY_LABEL[p.policy] ?? p.policy}</TableCell>
                    <TableCell className="text-right tabular-nums">{money(p.net_profit)}</TableCell>
                    <TableCell className="text-right tabular-nums">{int(p.aged90_day60)}</TableCell>
                    <TableCell className="text-right tabular-nums">{money(p.carrying_cost)}</TableCell>
                    <TableCell className="text-right tabular-nums">{int(p.wholesale_exits)}</TableCell>
                    <TableCell className="text-right tabular-nums">{int(p.retail_units)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
          <p className="mt-2 text-[11px] text-muted-foreground">Source: backtest_policy_results (ml/backtest.py). Synthetic data — validate on live inventory before quoting.</p>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>
              {top2.length === 2 ? `${top2[0].rooftop} and ${top2[1].rooftop} carry the most 90+ day stock` : 'Aged stock by rooftop'}
            </CardTitle>
            <CardDescription>On-hand units by days in stock, per rooftop</CardDescription>
          </CardHeader>
          <CardContent>
            {ag.loading ? <Skeleton className="h-[300px] w-full" /> : <BarChart data={ag.data ?? []} xKey="rooftop" yKey={['0-29 days', '30-44 days', '45-59 days', '60-89 days', '90+ days']}
              stacked colorPalette="sequential" height={300} ariaLabel="On-hand units by aging band per rooftop" />}
            <p className="text-[11px] text-muted-foreground">Source gold_inventory_current</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Share of stock aged 90+ days, last 26 weeks</CardTitle>
            <CardDescription>Group-wide, weekly (% of units on hand)</CardDescription>
          </CardHeader>
          <CardContent>
            <LineChart queryKey="aged_trend" xKey="week" yKey="% aged 90+" height={300} colorPalette="categorical"
              ariaLabel="Weekly share of inventory aged over 90 days" />
            <p className="text-[11px] text-muted-foreground">Source gold_rooftop_weekly_kpis</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
