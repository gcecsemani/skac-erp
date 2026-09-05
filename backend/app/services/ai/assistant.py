"""AI Agriculture Retail Business Assistant.

Flow (secure, no raw SQL):
  1. Route the natural-language question to ONE vetted tool + validated args.
     - If an LLM provider is configured, it selects the tool by returning strict
       JSON constrained to the registered tool names/params.
     - Otherwise a deterministic keyword heuristic selects the tool.
  2. Execute the tool with parameterized, org/branch-scoped queries.
  3. Summarize the structured result into a concise recommendation (LLM if
     available, else a templated summary).

The model can ONLY pick from `tools.TOOLS`; it never sees or writes SQL.
"""
from __future__ import annotations

import json
import re

from app.services.ai import tools
from app.services.ai.provider import get_provider
from app.services.ai.tools import ToolContext


def _build_router_prompt(question: str) -> str:
    catalogue = {
        name: {"description": t.description, "parameters": t.parameters}
        for name, t in tools.TOOLS.items()
    }
    return (
        "You are a routing function for an agri-retail ERP assistant (SKAC). "
        "Given the user's question, choose exactly ONE tool from the catalogue "
        "and the arguments to call it with. Respond with STRICT JSON only, of the "
        'form {"tool": "<tool_name>", "arguments": { ... }}. Do not add prose.\n\n'
        "Routing hints:\n"
        "- Farmers/customers who owe credit AND have not visited / billed recently "
        "→ inactive_credit_customers (days from the question, default 30).\n"
        "- User asks to generate / download / export a named report "
        "(GST, inventory, daily sales, field visits, outstanding, etc.) "
        "→ run_business_report with the matching report_key.\n"
        "- What can you do / help → list_capabilities.\n"
        "- Period words: today, this_week, this_month, last_month, last_30_days, "
        "last_90_days, or last_N_days (e.g. last_45_days).\n\n"
        f"TOOL CATALOGUE:\n{json.dumps(catalogue, indent=2)}\n\n"
        f"USER QUESTION: {question}\n\nJSON:"
    )


def _period_from(text: str) -> str:
    if "today" in text:
        return "today"
    m = re.search(r"last\s+(\d+)\s+days?", text)
    if m:
        return f"last_{m.group(1)}_days"
    if "last 90" in text or "90 day" in text:
        return "last_90_days"
    if "last 30" in text or "30 day" in text:
        return "last_30_days"
    if "last month" in text:
        return "last_month"
    if "this week" in text or "week" in text:
        return "this_week"
    if "year" in text or "ytd" in text:
        return "ytd"
    return "this_month"


def _days_from(text: str, default: int = 30) -> int:
    m = re.search(r"(\d+)\s*day", text)
    return int(m.group(1)) if m else default


def _match_report_key(q: str) -> str | None:
    aliases = [
        ("farmer_loss", ("farmer loss", "farmers who lose")),
        ("farmer_profit", ("farmer profit",)),
        ("product_loss", ("product loss", "loss making product")),
        ("product_profit", ("product profit",)),
        ("field_visits", ("field visit",)),
        ("vendor_stock", ("vendor stock", "vendor-wise stock")),
        ("payment_collection", ("payment collection", "collections report")),
        ("supplier_outstanding", ("supplier outstanding", "vendor outstanding", "vendor due")),
        ("customer_outstanding", ("customer outstanding", "farmer outstanding", "khata outstanding")),
        ("low_stock", ("low stock", "below reorder")),
        ("expiry", ("expir", "near expiry")),
        ("stock_movement", ("stock movement",)),
        ("inventory", ("inventory report", "stock on hand", "stock report")),
        ("gst", ("gst",)),
        ("profit_loss", ("profit and loss", "p&l", "pnl")),
        ("category_sales", ("category sales",)),
        ("product_sales", ("product sales", "sales by product")),
        ("purchase", ("purchase report", "purchases report")),
        ("monthly_sales", ("monthly sales",)),
        ("daily_sales", ("daily sales", "sales by day")),
    ]
    for key, words in aliases:
        if any(w in q for w in words):
            return key
    return None


def _heuristic_route(question: str) -> tuple[str, dict]:
    q = question.lower()

    if any(w in q for w in ("what can you", "what do you", "help me", "your capabilities", "what can i ask")):
        return "list_capabilities", {}

    creditish = any(w in q for w in ("credit", "khata", "outstanding", "owe", "due", "dues"))
    inactive = any(w in q for w in (
        "not coming", "not come", "haven't", "havent", "has not", "have not",
        "inactive", "no visit", "not visit", "didn't come", "did not come",
        "not been", "not shop", "not billed", "no bill", "last 30", "last 60", "last 90",
    ))
    if creditish and inactive:
        return "inactive_credit_customers", {"days": _days_from(q, 30), "limit": 2000}

    wants_report = any(w in q for w in ("report", "download", "export", "excel", "csv", "pdf", "generate"))
    report_key = _match_report_key(q)
    if wants_report and report_key:
        return "run_business_report", {"report_key": report_key, "period": _period_from(q)}
    if report_key in {"gst", "field_visits", "low_stock", "expiry"}:
        return "run_business_report", {"report_key": report_key, "period": _period_from(q)}

    category = None
    for c in ("fertilizer", "pesticide", "seed"):
        if c in q:
            category = c

    if "expense" in q or "spent" in q:
        return "expenses_summary", {"period": _period_from(q)}
    if "not sold" in q or "no sale" in q or "slow" in q or "dead stock" in q:
        return "products_not_sold_since", {"days": _days_from(q, 90)}
    if ("run out" in q or "stock out" in q or "stockout" in q or "run low" in q
            or "running out" in q or ("soon" in q and "stock" in q)):
        return "products_running_out", {"within_days": _days_from(q, 14)}
    if "purchase" in q or ("buy" in q and "week" in q) or "reorder" in q or "restock" in q:
        return "purchase_recommendations", {}
    if "margin" in q or ("profit" in q and ("product" in q or "highest" in q)):
        if "product" in q or "highest margin" in q:
            m = re.search(r"(\d+)\s*%", q)
            return "highest_margin_products", (
                {"min_margin_pct": float(m.group(1))} if m else {"limit": 10}
            )
    if creditish:
        args: dict = {"limit": 50 if wants_report else 10}
        m = re.search(r"[\$₹]?\s*([\d,]{3,})", q)
        if m:
            args["min_amount"] = float(m.group(1).replace(",", ""))
        return "customers_highest_outstanding", args
    if "compare" in q or ("vs" in q and "month" in q):
        return "compare_periods", {"period_a": "this_month", "period_b": "last_month"}
    if "top" in q and ("product" in q or "selling" in q or "sell" in q):
        m = re.search(r"top\s*(\d+)", q)
        return "top_selling_products", {
            "period": _period_from(q),
            "limit": int(m.group(1)) if m else 10,
            **({"category": category} if category else {}),
        }
    if "profit" in q:
        return "profit_summary", {"period": _period_from(q)}
    if "sell" in q or "sale" in q or "sold" in q or "revenue" in q:
        if category:
            return "top_selling_products", {"period": _period_from(q), "category": category}
        return "sales_summary", {"period": _period_from(q)}
    if wants_report:
        return "run_business_report", {"report_key": report_key or "daily_sales", "period": _period_from(q)}
    return "list_capabilities", {}


def _route(question: str) -> tuple[str, dict]:
    provider = get_provider()
    if provider.available():
        raw = provider.generate(_build_router_prompt(question))
        if raw:
            try:
                match = re.search(r"\{.*\}", raw, re.DOTALL)
                parsed = json.loads(match.group(0) if match else raw)
                name = parsed.get("tool")
                if name in tools.TOOLS:
                    return name, parsed.get("arguments", {}) or {}
            except (json.JSONDecodeError, AttributeError):
                pass
    return _heuristic_route(question)


def _summarize(question: str, tool_name: str, result: dict) -> str:
    provider = get_provider()
    if provider.available():
        try:
            payload = json.dumps(_summarize_payload(result), default=str)
        except (TypeError, ValueError):
            payload = json.dumps({"title": result.get("title"), "row_count": result.get("row_count")}, default=str)
        prompt = (
            "You are SKAC's agri-retail assistant chatting with the shop owner. "
            "Write a clear answer in Markdown: short paragraphs, **bold** for key "
            "numbers, and a bullet list when there are several items. "
            "Do NOT write markdown tables — the UI already shows a real downloadable table. "
            "Do not dump raw JSON. Use only figures from the data; do not invent numbers.\n\n"
            f"QUESTION: {question}\n\nDATA ({tool_name}):\n{payload}\n\nANSWER:"
        )
        text = provider.generate(prompt, temperature=0.3)
        if text:
            return text.strip()
    return _template_summary(tool_name, result)


def _inr(n) -> str:
    try:
        return f"₹{float(n):,.2f}"
    except (TypeError, ValueError):
        return "₹0.00"


def _summarize_payload(result: dict) -> dict:
    """Keep the LLM prompt small: drop huge row arrays after a preview."""
    rows = result.get("rows")
    if isinstance(rows, list) and len(rows) > 12:
        slim = {k: v for k, v in result.items() if k != "rows"}
        slim["row_preview"] = rows[:12]
        slim["row_count"] = result.get("row_count", len(rows))
        return slim
    return {k: v for k, v in result.items() if k not in {"recommendations", "products"} or not isinstance(v, list) or len(v) <= 12}


def _template_summary(tool_name: str, result: dict) -> str:
    if result.get("error"):
        return f"{result['error']}\n\nPick a report from the table below, or ask in plain language."
    if tool_name == "sales_summary":
        return (
            f"Sales for **{result.get('period')}**: **{_inr(result.get('revenue', 0))}** "
            f"across **{result.get('invoice_count', 0)}** bills."
        )
    if tool_name == "profit_summary":
        return (
            f"For **{result.get('period')}**: revenue **{_inr(result.get('revenue', 0))}**, "
            f"cost **{_inr(result.get('cost', 0))}**, gross profit "
            f"**{_inr(result.get('gross_profit', 0))}** ({result.get('margin_pct', 0)}% margin)."
        )
    if tool_name == "top_selling_products":
        items = result.get("items") or result.get("rows") or []
        if not items:
            return f"No sales found for **{result.get('period')}**."
        lines = "\n".join(
            f"- **{i.get('product')}** — {_inr(i.get('revenue', 0))} ({i.get('quantity', 0):g} qty)"
            for i in items[:8]
        )
        extra = f"\n\n…and {len(items) - 8} more in the table." if len(items) > 8 else ""
        return f"Top products (**{result.get('period')}**):\n\n{lines}{extra}"
    if tool_name == "products_running_out":
        rows = result.get("rows") or []
        if not rows:
            return "Nothing is forecast to run out in that window."
        lines = "\n".join(
            f"- **{p.get('product')}** — about **{p.get('days_to_stockout')}** days left"
            for p in rows[:8]
        )
        return f"**{len(rows)}** products may stock out soon:\n\n{lines}"
    if tool_name == "purchase_recommendations":
        rows = result.get("rows") or []
        if not rows:
            return "No restocking needed right now."
        lines = "\n".join(
            f"- **{r.get('product')}**: buy **{r.get('recommended_qty')}**"
            for r in rows[:8]
        )
        return f"Recommended purchases (**{len(rows)}** items):\n\n{lines}"
    if tool_name == "customers_highest_outstanding":
        rows = result.get("rows") or result.get("customers") or []
        if not rows:
            return "No farmers currently have outstanding credit."
        total = sum(float(c.get("outstanding") or 0) for c in rows)
        lines = "\n".join(
            f"- **{c.get('name')}** — {_inr(c.get('outstanding', 0))}"
            for c in rows[:8]
        )
        return (
            f"**{len(rows)}** farmers on the list, totalling **{_inr(total)}** outstanding:\n\n"
            f"{lines}"
        )
    if tool_name == "inactive_credit_customers":
        n = result.get("count", 0)
        days = result.get("days", 30)
        total = result.get("total_outstanding", 0)
        shown = result.get("row_count", 0)
        if not n:
            return (
                f"No farmers with unpaid credit have been away for **{days}** days. "
                "Everyone who owes you has billed more recently."
            )
        extra = ""
        if result.get("truncated"):
            extra = f" The table lists the top **{shown}** by outstanding — download Excel or PDF to follow up."
        else:
            extra = " The full list is in the table — download Excel or PDF if you want to follow up."
        return (
            f"**{n} farmers** have unpaid credit and have not billed in the last **{days} days**.\n\n"
            f"Together they owe **{_inr(total)}**.\n\n"
            f"{extra}"
        )
    if tool_name == "products_not_sold_since":
        return (
            f"**{result.get('count', 0)}** products had no sales in the last "
            f"**{result.get('days')}** days. See the table for the list."
        )
    if tool_name == "compare_periods":
        return (
            f"Change: **{_inr(result.get('change', 0))}** "
            f"({result.get('change_pct', 0)}%) between the two periods."
        )
    if tool_name == "highest_margin_products":
        items = result.get("items") or result.get("rows") or []
        if not items:
            return "No products with a computable margin."
        lines = "\n".join(
            f"- **{i.get('product')}** — {i.get('margin_pct')}%"
            for i in items[:8]
        )
        return f"Highest-margin products:\n\n{lines}"
    if tool_name == "expenses_summary":
        return (
            f"Expenses for **{result.get('period')}**: **{_inr(result.get('total', 0))}**. "
            "Breakdown is in the table."
        )
    if tool_name == "run_business_report":
        n = result.get("row_count", 0)
        title = result.get("title") or "Report"
        span = ""
        if result.get("start") and result.get("end"):
            span = f" ({result['start']} to {result['end']})"
        return (
            f"**{title}**{span} — **{n}** row{'s' if n != 1 else ''}.\n\n"
            "Download Excel or PDF from the buttons on the table."
        )
    if tool_name == "list_capabilities":
        return (
            "I can look up live SKAC data — sales, stock, profit, farmer credit, "
            "expenses, and any report from the Reports screen — then give you a "
            "downloadable table.\n\n"
            "Try asking in plain language, for example:\n"
            "- How many farmers have credit and have not come in 30 days? Generate a report.\n"
            "- What did we sell today?\n"
            "- Which products will run out this week?"
        )
    n = result.get("row_count")
    if n:
        return f"Here are **{n}** rows for your question. Download Excel or PDF from the table."
    return "I looked that up. See the details below."


def _report_from_result(tool_name: str, result: dict) -> dict | None:
    if not isinstance(result, dict):
        return None
    columns = result.get("columns")
    rows = result.get("rows")
    if not isinstance(columns, list) or not isinstance(rows, list) or not columns:
        return None
    return {
        "title": result.get("title") or tool_name.replace("_", " ").title(),
        "columns": columns,
        "rows": rows,
        "row_count": int(result.get("row_count") or len(rows)),
    }


def ask(ctx: ToolContext, question: str) -> dict:
    """Answer a natural-language business question securely."""
    tool_name, arguments = _route(question)
    result = tools.run_tool(ctx, tool_name, arguments)
    answer = _summarize(question, tool_name, result)
    report = _report_from_result(tool_name, result)
    slim = {
        k: v for k, v in result.items()
        if k not in {"recommendations", "products", "items", "customers"}
    }
    return {
        "question": question,
        "tool": tool_name,
        "arguments": arguments,
        "data": slim,
        "answer": answer,
        "report": report,
    }
