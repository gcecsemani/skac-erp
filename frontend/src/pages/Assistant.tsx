import { useEffect, useRef, useState } from "react";
import { Sparkles, Send, FileSpreadsheet, FileText } from "lucide-react";
import { api } from "../api";
import { inr } from "../format";
import { exportExcel, exportPdf, type ExportColumn } from "../export";
import { Table } from "../components/ui";

type ChatReport = {
  title: string;
  columns: { key: string; label: string; money?: boolean; num?: boolean }[];
  rows: any[];
  row_count?: number;
};

type ChatMsg = {
  id: string;
  role: "user" | "assistant";
  text: string;
  report?: ChatReport | null;
  error?: boolean;
};

const SUGGESTIONS = [
  "How many farmers have credit and have not come to the shop in the last 30 days? Generate a report.",
  "What are my top 10 selling products this month?",
  "Which products will run out of stock soon?",
  "Which farmers have the highest outstanding balance?",
  "How much did I sell today?",
  "Generate the GST report for this month",
  "What should I purchase this week?",
];

function uid() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function inlineMd(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) =>
    p.startsWith("**") && p.endsWith("**") ? <strong key={i}>{p.slice(2, -2)}</strong> : p,
  );
}

function splitRow(line: string) {
  return line.replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
}

function ChatMarkdown({ text }: { text: string }) {
  const blocks = text.replace(/\r\n/g, "\n").trim().split(/\n{2,}/);
  return (
    <div className="chat-md">
      {blocks.map((block, bi) => {
        const lines = block.split("\n");
        if (/^#{1,3}\s/.test(lines[0])) {
          const rest = lines.slice(1).filter((l) => l.trim());
          const restList = rest.length > 0 && rest.every((l) => /^\s*[-*]\s+/.test(l));
          return (
            <div key={bi}>
              <h3>{inlineMd(lines[0].replace(/^#{1,3}\s+/, ""))}</h3>
              {restList ? (
                <ul>
                  {rest.map((l, li) => <li key={li}>{inlineMd(l.replace(/^\s*[-*]\s+/, ""))}</li>)}
                </ul>
              ) : rest.length ? (
                <p>{rest.map((l, li) => <span key={li}>{inlineMd(l)}{li < rest.length - 1 ? <br /> : null}</span>)}</p>
              ) : null}
            </div>
          );
        }
        const isTable = lines.length >= 2 && lines[0].includes("|") && /^\s*\|?\s*[-:| ]+\s*\|?\s*$/.test(lines[1]);
        if (isTable) {
          const header = splitRow(lines[0]);
          const body = lines.slice(2).filter((l) => l.includes("|"));
          return (
            <div key={bi} className="table-wrap chat-md-table">
              <table>
                <thead><tr>{header.map((h) => <th key={h}>{h}</th>)}</tr></thead>
                <tbody>
                  {body.map((row, ri) => (
                    <tr key={ri}>{splitRow(row).map((c, ci) => <td key={ci}>{inlineMd(c)}</td>)}</tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }
        const isList = lines.filter((l) => l.trim()).every((l) => /^\s*[-*]\s+/.test(l));
        if (isList) {
          return (
            <ul key={bi}>
              {lines.filter((l) => l.trim()).map((l, li) => (
                <li key={li}>{inlineMd(l.replace(/^\s*[-*]\s+/, ""))}</li>
              ))}
            </ul>
          );
        }
        const isNum = lines.filter((l) => l.trim()).every((l) => /^\s*\d+\.\s+/.test(l));
        if (isNum) {
          return (
            <ol key={bi}>
              {lines.filter((l) => l.trim()).map((l, li) => (
                <li key={li}>{inlineMd(l.replace(/^\s*\d+\.\s+/, ""))}</li>
              ))}
            </ol>
          );
        }
        return (
          <p key={bi}>
            {lines.map((l, li) => (
              <span key={li}>{inlineMd(l)}{li < lines.length - 1 ? <br /> : null}</span>
            ))}
          </p>
        );
      })}
    </div>
  );
}

function downloadReport(report: ChatReport, kind: "excel" | "pdf") {
  const cols: ExportColumn[] = report.columns.map((c) => ({
    key: c.key, label: c.label, money: !!c.money, num: !!c.num,
  }));
  if (kind === "excel") exportExcel(report.title, cols, report.rows);
  else exportPdf(report.title, `${report.row_count ?? report.rows.length} rows`, cols, report.rows);
}

function ReportCard({ report }: { report: ChatReport }) {
  const columns = report.columns.map((c) => ({
    key: c.key,
    label: c.label,
    num: !!c.num || !!c.money,
    render: c.money ? (r: any) => inr(r[c.key]) : undefined,
  }));
  return (
    <div className="chat-report">
      <div className="chat-report-head">
        <div>
          <div className="chat-report-title">{report.title}</div>
          <div className="muted" style={{ fontSize: 12 }}>{report.row_count ?? report.rows.length} rows</div>
        </div>
        <div className="row export-btns">
          <button className="btn btn-ghost btn-sm" onClick={() => downloadReport(report, "excel")}>
            <FileSpreadsheet size={14} /> Excel
          </button>
          <button className="btn btn-ghost btn-sm" onClick={() => downloadReport(report, "pdf")}>
            <FileText size={14} /> PDF
          </button>
        </div>
      </div>
      <Table columns={columns} rows={report.rows} empty="No rows" pageSize={25} />
    </div>
  );
}

export default function Assistant() {
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  const send = async (question: string) => {
    const text = question.trim();
    if (!text || busy) return;
    setQ("");
    setMessages((m) => [...m, { id: uid(), role: "user", text }]);
    setBusy(true);
    try {
      const r = await api.ask(text);
      setMessages((m) => [...m, {
        id: uid(),
        role: "assistant",
        text: r.answer || "I looked that up.",
        report: r.report && r.report.rows ? r.report : null,
      }]);
    } catch (e: any) {
      setMessages((m) => [...m, {
        id: uid(),
        role: "assistant",
        text: e.message || "Could not answer that.",
        error: true,
      }]);
    } finally {
      setBusy(false);
      inputRef.current?.focus();
    }
  };

  return (
    <div className="chat-shell">
      <div className="chat-thread">
        {messages.length === 0 && (
          <div className="chat-welcome">
            <div className="chat-welcome-icon"><Sparkles size={28} /></div>
            <h2>Ask SKAC anything about the shop</h2>
            <p>
              Sales, stock, farmer credit, expenses, GST — I’ll query live data and
              give you a readable answer plus a downloadable report when it helps.
            </p>
            <div className="chips">
              {SUGGESTIONS.map((s) => (
                <button key={s} className="chip" disabled={busy} onClick={() => send(s)}>{s}</button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`chat-msg ${msg.role}${msg.error ? " is-error" : ""}`}>
            {msg.role === "assistant" && (
              <div className="chat-avatar" aria-hidden><Sparkles size={16} /></div>
            )}
            <div className="chat-bubble">
              {msg.role === "assistant" ? <ChatMarkdown text={msg.text} /> : msg.text}
              {msg.report && msg.report.rows?.length > 0 && <ReportCard report={msg.report} />}
              {msg.report && !msg.report.rows?.length && msg.role === "assistant" && (
                <p className="muted" style={{ margin: "8px 0 0", fontSize: 12 }}>No rows to download for this answer.</p>
              )}
            </div>
          </div>
        ))}

        {busy && (
          <div className="chat-msg assistant">
            <div className="chat-avatar" aria-hidden><Sparkles size={16} /></div>
            <div className="chat-bubble chat-typing">
              <span /><span /><span />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form
        className="chat-composer"
        onSubmit={(e) => { e.preventDefault(); send(q); }}
      >
        <textarea
          ref={inputRef}
          value={q}
          rows={1}
          placeholder="Ask about sales, farmers, stock, or request a report…"
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send(q);
            }
          }}
        />
        <button className="btn btn-primary" type="submit" disabled={busy || !q.trim()}>
          {busy ? "…" : <><Send size={16} /> Send</>}
        </button>
      </form>
    </div>
  );
}
