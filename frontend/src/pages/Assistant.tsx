import { useState } from "react";
import { Sparkles, Send, ShieldCheck } from "lucide-react";
import { api } from "../api";
import { Card, PageHeader } from "../components/ui";

const SUGGESTIONS = [
  "What are my top 10 selling products this month?",
  "Which products will run out of stock soon?",
  "What should I purchase this week?",
  "Which products have not sold for 90 days?",
  "Which products give me the highest profit margin?",
  "Which customers have the highest outstanding balance?",
  "How much did I sell today?",
  "Compare this month's sales with last month",
];

export default function Assistant() {
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [history, setHistory] = useState<any[]>([]);

  const ask = async (question: string) => {
    if (!question.trim()) return;
    setBusy(true);
    try {
      const r = await api.ask(question);
      setHistory((h) => [{ question, ...r }, ...h]); setQ("");
    } catch (e: any) {
      setHistory((h) => [{ question, answer: `Error: ${e.message}` }, ...h]);
    } finally { setBusy(false); }
  };

  return (
    <div>
      <PageHeader title="AI Business Assistant" subtitle="Ask about sales, stock, dues and profit in plain language" />
      <Card>
        <div className="ask-row">
          <input value={q} placeholder="Ask a question about your business…" onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && ask(q)} />
          <button className="btn btn-primary" disabled={busy} onClick={() => ask(q)}><Send size={16} /> {busy ? "…" : "Ask"}</button>
        </div>
        <div className="chips">
          {SUGGESTIONS.map((s) => <button key={s} className="chip" onClick={() => ask(s)}>{s}</button>)}
        </div>
        <div className="row mt-8 muted" style={{ fontSize: 12, gap: 6 }}>
          <ShieldCheck size={14} /> Answers use secure, vetted database tools — the AI never runs raw SQL.
        </div>
      </Card>

      {history.map((h, i) => (
        <Card key={i} className="qa">
          <div className="q"><Sparkles size={16} color="#16a34a" /> {h.question}</div>
          <div className="a">{h.answer}</div>
          {h.tool && <div className="muted mt-8" style={{ fontSize: 12 }}>tool: <code>{h.tool}</code></div>}
        </Card>
      ))}
    </div>
  );
}
