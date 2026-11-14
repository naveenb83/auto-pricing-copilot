import { Card, CardContent, CardDescription, CardHeader, CardTitle, Skeleton } from '@databricks/appkit-ui/react';
import type { ReactNode } from 'react';

/** KPI tile: value + unit/period + comparison + source (composed from Card primitives). */
export function Kpi({ title, value, sub, source, tone, loading }: {
  title: string; value: ReactNode; sub?: ReactNode; source: string; tone?: 'good' | 'bad' | 'neutral'; loading?: boolean;
}) {
  const toneClass = tone === 'good' ? 'text-success' : tone === 'bad' ? 'text-destructive' : 'text-foreground';
  return (
    <Card className="gap-2">
      <CardHeader className="pb-0">
        <CardDescription>{title}</CardDescription>
        <CardTitle className={`text-2xl tabular-nums ${toneClass}`}>{loading ? <Skeleton className="h-8 w-24" /> : value}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-1">
        {sub && <div className="text-sm text-muted-foreground">{sub}</div>}
        <div className="text-[11px] text-muted-foreground">Source: {source}</div>
      </CardContent>
    </Card>
  );
}
