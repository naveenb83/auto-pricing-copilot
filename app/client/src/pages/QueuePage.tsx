import {
  Alert, AlertDescription, AlertTitle, Badge, Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Empty,
  EmptyDescription, EmptyHeader, EmptyTitle, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Skeleton,
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@databricks/appkit-ui/react';
import { ShieldCheck } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { VehiclePhoto } from '../components/VehiclePhoto';
import { api, type Row } from '../lib/api';
import { days, int, money, ptmLabel, signedMoney, toNum, text } from '../lib/format';

const PAGE = 25;
const ALL = '__all';

export function StatusBadge({ status }: { status: string }) {
  if (status === 'accepted') return <Badge variant="secondary">Accepted</Badge>;
  if (status === 'overridden') return <Badge variant="outline">Overridden</Badge>;
  if (status === 'held') return <Badge variant="outline">Held</Badge>;
  return <Badge>Needs decision</Badge>;
}

export function QueuePage() {
  const nav = useNavigate();
  const [rooftops, setRooftops] = useState<Row[]>([]);
  const [rooftop, setRooftop] = useState(ALL);
  const [bucket, setBucket] = useState(ALL);
  const [status, setStatus] = useState(ALL);
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<{ rows: Row[]; total: number; key: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<Row[]>('/api/rooftops').then(setRooftops).catch(() => setRooftops([]));
  }, []);

  const wantedKey = new URLSearchParams({
    rooftop: rooftop === ALL ? '' : rooftop, bucket: bucket === ALL ? '' : bucket, status: status === ALL ? '' : status,
    limit: `${PAGE}`, offset: `${offset}`,
  }).toString();

  useEffect(() => {
    let cancelled = false;
    api<{ rows: Row[]; total: number }>(`/api/queue?${wantedKey}`)
      .then((d) => { if (!cancelled) { setData({ ...d, key: wantedKey }); setError(null); } })
      .catch((e: Error) => { if (!cancelled) setError(e.message); });
    return () => { cancelled = true; };
  }, [wantedKey]);
  const loading = !error && data?.key !== wantedKey;

  const reset = (fn: (v: string) => void) => (v: string) => { setOffset(0); fn(v); };
  const total = data?.total ?? 0;

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-semibold text-foreground">Pricing queue</h2>
        <p className="text-sm text-muted-foreground">
          Units 45+ days in stock, biggest expected profit gain over the flat rule first. Open a unit to get a live Model/DS value and decide.
        </p>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Filters</CardTitle>
          <CardDescription>{loading ? 'Loading…' : `${int(total)} units match`}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <Select value={rooftop} onValueChange={reset(setRooftop)}>
            <SelectTrigger className="w-60" aria-label="Rooftop"><SelectValue placeholder="All rooftops" /></SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All rooftops</SelectItem>
              {rooftops.map((r) => <SelectItem key={text(r.rooftop_id)} value={text(r.rooftop_id)}>{text(r.rooftop_name)}</SelectItem>)}
            </SelectContent>
          </Select>
          <Select value={bucket} onValueChange={reset(setBucket)}>
            <SelectTrigger className="w-44" aria-label="Days in stock"><SelectValue placeholder="All ages" /></SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All ages (45+)</SelectItem>
              <SelectItem value="45-59">45–59 days</SelectItem>
              <SelectItem value="60-89">60–89 days</SelectItem>
              <SelectItem value="90+">90+ days</SelectItem>
            </SelectContent>
          </Select>
          <Select value={status} onValueChange={reset(setStatus)}>
            <SelectTrigger className="w-48" aria-label="Decision status"><SelectValue placeholder="Any status" /></SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>Any status</SelectItem>
              <SelectItem value="pending">Needs decision</SelectItem>
              <SelectItem value="accepted">Accepted</SelectItem>
              <SelectItem value="overridden">Overridden</SelectItem>
              <SelectItem value="held">Held</SelectItem>
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {error ? (
        <Alert variant="destructive"><AlertTitle>Queue unavailable</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>
      ) : loading && !data ? (
        <Skeleton className="h-96 w-full" />
      ) : (data?.rows.length ?? 0) === 0 ? (
        <Empty><EmptyHeader><EmptyTitle>No units match</EmptyTitle><EmptyDescription>Clear a filter to see more of the lot.</EmptyDescription></EmptyHeader></Empty>
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-28">Vehicle</TableHead><TableHead />
                  <TableHead className="text-right">Days</TableHead><TableHead className="text-right">List price</TableHead>
                  <TableHead className="text-right">Holding / day</TableHead><TableHead className="text-right">Model/DS value</TableHead>
                  <TableHead className="text-right">Flat rule adds</TableHead><TableHead className="text-right">Gain vs rule</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.rows.map((r) => (
                  <TableRow key={text(r.vin)} className="cursor-pointer" onClick={() => { void nav(`/vehicle/${text(r.vin)}`); }}>
                    <TableCell><VehiclePhoto file={text(r.image_file)} alt={`${text(r.make)} ${text(r.model)}`} className="w-24" /></TableCell>
                    <TableCell>
                      <div className="font-medium">{text(r.model_year)} {text(r.make)} {text(r.model)} {text(r.trim)}</div>
                      <div className="text-xs text-muted-foreground">
                        {text(r.stock_number)} · {text(r.rooftop_name)} · {text(r.condition)} · {ptmLabel(r.price_to_market)}
                      </div>
                    </TableCell>
                    <TableCell className={`text-right tabular-nums ${toNum(r.days_in_stock) >= 90 ? 'text-destructive font-medium' : ''}`}>{int(r.days_in_stock)}</TableCell>
                    <TableCell className="text-right tabular-nums">{money(r.current_price)}</TableCell>
                    <TableCell className="text-right tabular-nums">{money(r.daily_holding_cost)}</TableCell>
                    <TableCell className="text-right tabular-nums font-medium">
                      {toNum(r.recommended_discount) === 0 ? 'Hold' : `−${money(r.recommended_discount)}`}
                      {r.guardrail_applied === true && <ShieldCheck className="ml-1 inline h-3.5 w-3.5 text-muted-foreground" aria-label="capped by guardrail" />}
                      <div className="text-[11px] font-normal text-muted-foreground">sells in ~{days(r.expected_days_to_sell_recommended)}</div>
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-muted-foreground">{toNum(r.flat_rule_discount) === 0 ? '$0' : `−${money(r.flat_rule_discount)}`}</TableCell>
                    <TableCell className={`text-right tabular-nums ${toNum(r.uplift_vs_flat_rule) > 0 ? 'text-success' : ''}`}>{signedMoney(r.uplift_vs_flat_rule)}</TableCell>
                    <TableCell><StatusBadge status={text(r.decision_status)} /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          {total ? `${offset + 1}–${Math.min(offset + PAGE, total)} of ${int(total)}` : ''} · Model/DS value = overnight batch score;
          open a unit for a live call · <ShieldCheck className="inline h-3.5 w-3.5" /> = capped by pricing guardrail
        </span>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>Previous</Button>
          <Button variant="outline" size="sm" disabled={offset + PAGE >= total} onClick={() => setOffset(offset + PAGE)}>Next</Button>
        </div>
      </div>
    </div>
  );
}
