/** POS bills kept in this browser so leaving the page, or serving another farmer, does not wipe the cart. */

const KEY = "skac.pos.session.v1";

export type PosDraft = {
  id: string;
  branchId: number;
  customer: any | null;
  lines: any[];
  tenders: Record<string, string>;
  billDiscount: string;
  discMode: "inr" | "pct";
  savedAt: number;
};

export type PosSession = {
  active: PosDraft | null;
  held: PosDraft[];
};

export const emptySession = (): PosSession => ({ active: null, held: [] });

export function loadPosSession(): PosSession {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return emptySession();
    const parsed = JSON.parse(raw);
    const held = Array.isArray(parsed?.held) ? parsed.held.filter((d: PosDraft) => d && d.id) : [];
    const active = parsed?.active && parsed.active.id ? parsed.active : null;
    return { active, held };
  } catch {
    return emptySession();
  }
}

export function savePosSession(session: PosSession) {
  const active = session.active && (session.active.lines?.length || session.active.customer) ? session.active : null;
  localStorage.setItem(KEY, JSON.stringify({ active, held: session.held || [] }));
}

export function newDraftId() {
  return crypto.randomUUID ? crypto.randomUUID() : `bill-${Date.now()}`;
}
