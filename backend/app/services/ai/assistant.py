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
        "You are a routing function for an agri-retail business assistant. "
        "Given the user's question, choose exactly ONE tool from the catalogue "
        "and the arguments to call it with. Respond with STRICT JSON only, of the "
        'form {"tool": "<tool_name>", "arguments": { ... }}. Do not add prose.\n\n'
        f"TOOL CATALOGUE:\n{json.dumps(catalogue, indent=2)}\n\n"
        f"USER QUESTION: {question}\n\nJSON:"
    )


def _heuristic_route(question: str) -> tuple[str, dict]:
    q = question.lower()

    def period_from(text: str) -> str:
        if "today" in text:
            return "today"
        if "last month" in text:
            return "last_month"
        if "this week" in text or "week" in text:
            return "this_week"
        if "year" in text or "ytd" in text:
            return "ytd"
        return "this_month"

    category = None
    for c in ("fertilizer", "pesticide", "seed"):
        if c in q:
            category = c

    if "not sold" in q or "no sale" in q or "slow" in q or "dead stock" in q:
        m = re.search(r"(\d+)\s*day", q)
        return "products_not_sold_since", {"days": int(m.group(1)) if m else 90}
    if ("run out" in q or "stock out" in q or "stockout" in q or "run low" in q
            or "running out" in q or "soon" in q and "stock" in q):
        return "products_running_out", {"within_days": 14}
    if "purchase" in q or ("buy" in q and "week" in q) or "reorder" in q or "restock" in q:
        return "purchase_recommendations", {}
    if "margin" in q or "profit" in q and ("product" in q or "highest" in q):
        if "product" in q or "highest margin" in q:
            m = re.search(r"(\d+)\s*%", q)
            return "highest_margin_products", (
                {"min_margin_pct": float(m.group(1))} if m else {"limit": 10}
            )
    if "outstanding" in q or "owe" in q or "due" in q or "credit" in q or "khata" in q:
        m = re.search(r"[\$₹]?\s*([\d,]{3,})", q)
        args: dict = {"limit": 10}
        if m:
            args["min_amount"] = float(m.group(1).replace(",", ""))
        return "customers_highest_outstanding", args
    if "compare" in q or ("vs" in q and "month" in q):
        return "compare_periods", {"period_a": "this_month", "period_b": "last_month"}
    if "top" in q and ("product" in q or "selling" in q or "sell" in q):
        m = re.search(r"top\s*(\d+)", q)
        return "top_selling_products", {
            "period": period_from(q),
            "limit": int(m.group(1)) if m else 10,
            **({"category": category} if category else {}),
        }
    if "profit" in q:
        return "profit_summary", {"period": period_from(q)}
    if "sell" in q or "sale" in q or "sold" in q or "revenue" in q:
        if category:
            return "top_selling_products", {"period": period_from(q), "category": category}
        return "sales_summary", {"period": period_from(q)}
    # Default
    return "sales_summary", {"period": "today"}


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
        prompt = (
            "You are a concise agri-retail business advisor. Given the user's "
            "question and the JSON data (already fetched securely from the "
            "business database), answer in 2-4 sentences with a clear, useful "
            "recommendation. Use figures from the data; do not invent numbers.\n\n"
            f"QUESTION: {question}\n\nDATA ({tool_name}):\n{json.dumps(result)}\n\nANSWER:"
        )
        text = provider.generate(prompt, temperature=0.3)
        if text:
            return text.strip()
    return _template_summary(tool_name, result)


def _template_summary(tool_name: str, result: dict) -> str:
    if tool_name == "sales_summary":
        return (
            f"Sales for {result.get('period')}: "
            f"{result.get('revenue', 0):,.2f} across "
            f"{result.get('invoice_count', 0)} invoices."
        )
    if tool_name == "profit_summary":
        return (
            f"For {result.get('period')}: revenue {result.get('revenue', 0):,.2f}, "
            f"cost {result.get('cost', 0):,.2f}, gross profit "
            f"{result.get('gross_profit', 0):,.2f} ({result.get('margin_pct', 0)}% margin)."
        )
    if tool_name == "top_selling_products":
        items = result.get("items", [])[:5]
        listing = ", ".join(f"{i['product']} ({i['revenue']:,.0f})" for i in items)
        return f"Top products ({result.get('period')}): {listing or 'no sales found'}."
    if tool_name == "products_running_out":
        ps = result.get("products", [])
        listing = ", ".join(
            f"{p['product_name']} (~{p['days_to_stockout']}d)" for p in ps[:8]
        )
        return f"Running out soon: {listing or 'nothing critical'}."
    if tool_name == "purchase_recommendations":
        recs = result.get("recommendations", [])
        listing = ", ".join(
            f"{r['product_name']}: buy {r['recommended_purchase_qty']:g}" for r in recs[:8]
        )
        return f"Recommended purchases: {listing or 'no restocking needed'}."
    if tool_name == "customers_highest_outstanding":
        cs = result.get("customers", [])
        listing = ", ".join(f"{c['name']} ({c['outstanding']:,.0f})" for c in cs[:8])
        return f"Highest outstanding: {listing or 'no dues'}."
    if tool_name == "products_not_sold_since":
        return (
            f"{result.get('count', 0)} products had no sales in the last "
            f"{result.get('days')} days."
        )
    if tool_name == "compare_periods":
        return (
            f"Change: {result.get('change', 0):,.2f} "
            f"({result.get('change_pct', 0)}%) between the two periods."
        )
    if tool_name == "highest_margin_products":
        items = result.get("items", [])[:5]
        listing = ", ".join(f"{i['product']} ({i['margin_pct']}%)" for i in items)
        return f"Highest-margin products: {listing or 'none'}."
    return json.dumps(result)


def ask(ctx: ToolContext, question: str) -> dict:
    """Answer a natural-language business question securely."""
    tool_name, arguments = _route(question)
    result = tools.run_tool(ctx, tool_name, arguments)
    answer = _summarize(question, tool_name, result)
    return {
        "question": question,
        "tool": tool_name,
        "arguments": arguments,
        "data": result,
        "answer": answer,
    }
