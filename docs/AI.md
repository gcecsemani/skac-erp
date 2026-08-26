# SKAC AI Features

Two capabilities, both designed for **free-tier LLM usage** and **safe DB access**.

## 1. Business Assistant (natural-language Q&A)

Endpoint: `POST /api/v1/ai/ask`  ·  `{ "question": "...", "branch_id": optional }`

### Security model — no raw SQL, ever
The LLM never sees the database and never writes SQL. Instead:

1. **Route** — the question is mapped to exactly ONE tool from a fixed registry
   (`app/services/ai/tools.py`). If an LLM provider is configured it returns
   strict JSON `{"tool", "arguments"}` constrained to the catalogue; otherwise a
   deterministic keyword router selects the tool. Unknown tools are rejected and
   arguments are whitelisted against each tool's schema.
2. **Execute** — the tool runs a **parameterized, ORM-built query** scoped to the
   caller's `organization_id` and branch access.
3. **Summarize** — the structured result is turned into a concise recommendation
   (LLM if available, else a deterministic template).

This is the standard "tools / function-calling over a vetted catalogue" pattern:
the model chooses *what* to ask, the server controls *how* it is asked.

### Available tools
`sales_summary`, `top_selling_products`, `profit_summary`,
`highest_margin_products`, `customers_highest_outstanding`,
`products_not_sold_since`, `products_running_out`, `purchase_recommendations`,
`compare_periods`. (Inspect live via `GET /api/v1/ai/tools`.)

### Example questions
- "What are my top 10 selling products this month?" → `top_selling_products`
- "Which products will run out of stock soon?" → `products_running_out`
- "What should I purchase this week?" → `purchase_recommendations`
- "Which products have not sold for 90 days?" → `products_not_sold_since`
- "Which customers owe more than 1000?" → `customers_highest_outstanding`
- "Compare this month's sales with last month" → `compare_periods`

## 2. Smart Inventory — demand forecasting

Module: `app/services/ai/forecasting.py` · Endpoint: `GET /api/v1/inventory/forecast`

For each product (optionally per branch) it computes from the movement ledger:
- average daily / weekly / monthly sales
- sales trend (last 30d vs prior 30d) and a rising/falling/stable label
- current stock, reorder point (lead-time + safety days)
- estimated stock-out date
- recommended purchase quantity (target coverage − current stock + reorder)

The frontend **AI Purchase Recommendations** screen lists items needing restock
and lets the user select rows to convert into a Purchase Order (PO creation is a
Phase-4 backend endpoint).

## Configuration (free tier friendly)

Set in `backend/.env`:

```
AI_PROVIDER=none        # none | gemini | groq
AI_API_KEY=             # your free-tier key
AI_MODEL=gemini-1.5-flash
```

- `none` (default): everything works using the deterministic router + templated
  summaries — zero external calls, zero cost. Good for offline/dev.
- `gemini`: Google Generative Language API free tier (`gemini-1.5-flash`).
- `groq`: Groq OpenAI-compatible free tier (`llama-3.1-8b-instant`).

Provider calls are best-effort: any failure falls back to the deterministic path,
so the assistant never hard-fails due to rate limits.
