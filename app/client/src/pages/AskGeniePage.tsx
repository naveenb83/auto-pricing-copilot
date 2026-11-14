import {
  Alert, AlertDescription, Badge, Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Empty, EmptyDescription,
  EmptyHeader, EmptyTitle, GenieChatInput, GenieChatMessageList, useGenieChat,
} from '@databricks/appkit-ui/react';
import { ShieldCheck } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { api } from '../lib/api';

const SUGGESTIONS = [
  'How many units are aged 90+ days at each rooftop and what do they cost us per day?',
  'Which aged units does the model recommend cutting by $1,500 or more?',
  'Which customer segments respond best to pickup promotions?',
  'How often are pricing managers overriding the model, and why?',
];

export function AskGeniePage() {
  const { messages, status, error, sendMessage, reset } = useGenieChat({ alias: 'default' });
  const [me, setMe] = useState<{ email?: string } | null>(null);
  useEffect(() => { api<{ email?: string }>('/api/whoami').then(setMe).catch(() => setMe(null)); }, []);

  const lastSql = useMemo(() => {
    for (const m of [...messages].reverse()) for (const a of m.attachments ?? []) if (a.query?.query) return a.query;
    return null;
  }, [messages]);

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-2xl font-semibold text-foreground">Ask the data</h2>
          <Badge variant="secondary">{me?.email ?? 'Signed in'}</Badge>
          <Badge variant="outline"><ShieldCheck className="mr-1 h-3 w-3" />runs with your permissions</Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          Genie Agent over the governed pricing tables and KPI metric view. Questions run on-behalf-of you, so Unity Catalog row filters and
          masks apply — rooftop staff only see their rooftop, and cost/gross show as hidden without margin access.
        </p>
        <Card className="flex h-[min(620px,70vh)] flex-col overflow-hidden">
          {messages.length === 0 && status === 'idle' ? (
            <div className="flex-1 p-6">
              <Empty>
                <EmptyHeader>
                  <EmptyTitle>Ask anything about aged stock, pricing, overrides or segments</EmptyTitle>
                  <EmptyDescription>Try one of these:</EmptyDescription>
                </EmptyHeader>
                <div className="flex flex-col gap-2">
                  {SUGGESTIONS.map((q) => <Button key={q} variant="outline" className="h-auto whitespace-normal text-left" onClick={() => sendMessage(q)}>{q}</Button>)}
                </div>
              </Empty>
            </div>
          ) : (
            <GenieChatMessageList messages={messages} status={status} className="flex-1" />
          )}
          {status === 'streaming' && <p className="px-4 text-sm text-muted-foreground">Genie is writing and running SQL…</p>}
          {status === 'error' && <Alert variant="destructive" className="mx-4"><AlertDescription>{error ?? 'Genie failed — rephrase or retry.'}</AlertDescription></Alert>}
          <div className="border-t p-3">
            <GenieChatInput onSend={sendMessage} disabled={status === 'streaming'} placeholder="e.g. Which make has the most 90+ day units?" />
            <div className="mt-2 flex items-center justify-between">
              <p className="text-xs text-muted-foreground">AI-generated from your data via Genie — check the generated SQL before relying on a number.</p>
              <Button variant="ghost" size="sm" onClick={reset}>New conversation</Button>
            </div>
          </div>
        </Card>
      </div>
      <Card className="h-fit">
        <CardHeader>
          <CardTitle className="text-base">Generated SQL</CardTitle>
          <CardDescription>{lastSql?.description ?? lastSql?.title ?? 'How the latest answer was computed appears here.'}</CardDescription>
        </CardHeader>
        <CardContent>
          {lastSql ? <pre className="max-h-[480px] overflow-auto whitespace-pre-wrap break-all rounded-md bg-muted p-3 text-xs">{lastSql.query}</pre>
            : <p className="text-sm text-muted-foreground">No query yet.</p>}
          <p className="mt-2 text-[11px] text-muted-foreground">Executed on the SQL warehouse as the signed-in user (on-behalf-of, <code>dashboards.genie</code> scope).</p>
        </CardContent>
      </Card>
    </div>
  );
}
