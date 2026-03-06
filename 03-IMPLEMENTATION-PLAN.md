# LogisticsMind AI — Implementation Plan

> 5-week build sequence for Claude Code CLI.
> Conversational layer built inline inside agent/core/.
> No external framework dependency.

---

## How to Use With Claude Code

Start every session:
```
Read 01-SYSTEM-DESIGN.md and 02-TECHNICAL-PLAN.md before starting.
We are building LogisticsMind AI. Current task: [X.X]
```

---

## Week 1 — Database + Mock Data

**Goal:** PostgreSQL running with all tables seeded,
analytical views ready. The database is the foundation.

---

### Task 1.1 — Project Scaffold + Schema

```
Create the full LogisticsMind AI project scaffold.

Directory structure from 02-TECHNICAL-PLAN.md Section 1.
Create all directories and empty __init__.py files.

Create .env.example:
  GEMINI_API_KEY=
  DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/ceylog
  REDIS_URL=redis://localhost:6379/0
  DEBUG=false

Create requirements.txt from 02-TECHNICAL-PLAN.md Section 9.

Create docker-compose.yml:
  services:
    postgres: postgres:16, db=ceylog, user=user, password=password
    redis:    redis:7-alpine

Create the full database schema:
- db/schema/000_extensions.sql  — uuid-ossp, pg_stat_statements
- db/schema/001_core.sql        — districts, companies, contacts, vendors, products
- db/schema/002_warehouse.sql   — facilities, inventory_items, stock_movements, staff
- db/schema/003_fleet.sql       — vehicles, drivers, routes, trips, gps_pings, maintenance_logs
- db/schema/004_operations.sql  — orders, order_items, shipments, tracking_events, incidents, sla_contracts
- db/schema/005_finance.sql     — invoices, payments, operational_costs, sla_breaches
- db/schema/006_views.sql       — CREATE SCHEMA analytics + all 4 views from original 02-TECHNICAL-PLAN.md Section 9
- db/schema/007_analyst_memory.sql — analyst_facts, analyst_sessions tables from 02-TECHNICAL-PLAN.md Section 2.4

Full schemas from 01-SYSTEM-DESIGN.md Section 3.
All FK constraints. Indexes on every FK column, status, created_at, trip_date.

Create db/migrate.py:
  Reads and executes all schema files in order.
  Run: python db/migrate.py

Verify: psql -c "\dt *.*" shows all tables across all schemas.
```

---

### Task 1.2 — Core + Warehouse Seed

```
Implement and run core and warehouse data generators.

db/seed/generators/core.py:
- Insert all 25 Sri Lankan districts (exact data from 01-SYSTEM-DESIGN.md Section 3 — names, provinces, lat/lng)
- Generate 500 companies with Sri Lankan names (Faker + "(Pvt) Ltd", "PLC", "& Co" suffixes)
- Generate 150 vendors across 4 types
- Generate 2,000 products across 5 categories with realistic Sri Lankan SKUs (SKU-FMCG-001 etc.)

db/seed/generators/warehouse.py:
- Create exactly 18 facilities with these codes:
  WH-COL-01, WH-COL-02, WH-KAN-01, WH-GAL-01, WH-JAF-01,
  WH-TRC-01, WH-BAT-01, WH-KUR-01, WH-PUT-01, WH-ANU-01,
  WH-POL-01, WH-BAD-01, WH-RAT-01, WH-HAM-01, WH-MAT-01,
  WH-NUW-01, WH-KEG-01, WH-MON-01
  Assign to matching districts with realistic lat/lng
- Generate 40,000 inventory_items (not all product/facility combos — realistic subset)
- Generate 150,000 stock_movements over 2 years (batch inserts of 1000 rows)
- Generate 300 warehouse staff

Use asyncpg executemany() for performance. Print row count every 10,000 rows.
```

---

### Task 1.3 — Fleet + Operations + Finance Seed

```
Implement and run fleet, operations, and finance generators.

db/seed/generators/fleet.py:
- 200 vehicles with Sri Lankan plate format. Include plate VH-0031, VH-0089 explicitly.
- 180 drivers with Sri Lankan names. Include employee_id DRV-0042 explicitly.
- 80 routes. Include code RT-COL-JAF-003 explicitly (Colombo → Jaffna, cross_province type).
- 15,000 trips over 2 years:
  - More trips Oct-Jan (post-monsoon high season)
  - 90% status=completed, 5% cancelled, 5% breakdown
- 500,000 GPS pings: generate ~33 pings per completed trip at 5-minute intervals
  Use monthly partitioning: gps_pings_2024_01, gps_pings_2024_02 etc.
- 3,000 maintenance_logs

db/seed/generators/operations.py:
- 25,000 orders over 2 years
  November seasonal spike: orders in November are 60% higher than monthly average
- 28,000 shipments (some orders split into 2 shipments)
  On-time rate: 75% delivered on time, 20% mild delay (<8h), 5% major delay
- 180,000 tracking_events (6-7 events per shipment covering full lifecycle)
- 2,500 incidents distributed across types:
  delay 40%, damage 25%, breakdown 15%, weather 10%, other 10%

db/seed/generators/finance.py:
- 24,000 invoices matching orders
- 22,000 payments (most within credit terms, 10% late)
- 35,000 operational_costs
- 3,200 sla_breaches

Run db/seed/seed.py and verify row counts match 01-SYSTEM-DESIGN.md Section 4.
```

---

### Task 1.4 — Anomaly Injection + Verification

```
Inject the 5 anomaly patterns and verify they exist.

Implement db/seed/anomalies.py:

1. RT-COL-JAF-003 — 40% higher delay rate:
   UPDATE fleet.trips SET actual_arrive = scheduled_arrive + INTERVAL '8 hours'
   WHERE route_id = (SELECT id FROM fleet.routes WHERE code = 'RT-COL-JAF-003')
   AND status = 'completed' AND random() < 0.4

2. DRV-0042 — 2x fuel consumption:
   UPDATE fleet.trips SET fuel_used_l = fuel_used_l * 2.1
   WHERE driver_id = (SELECT id FROM fleet.drivers WHERE employee_id = 'DRV-0042')

3. VH-0031 — breakdown every ~8000km:
   INSERT maintenance records at 8000km intervals for this vehicle

4. COMP-0187 (187th company by created_at) — 15 days late payments:
   UPDATE finance.payments SET payment_date = due_date + 15
   WHERE invoice_id IN (invoices for this company)

5. SKU-PHARM-099 — 5x damage rate:
   INSERT 50 damage incidents for shipments containing this product

Create db/verify_anomalies.sql with 5 verification queries.
Run them and confirm each anomaly is statistically significant.
All 5 must show clear deviation from the baseline.
```

---

## Week 2 — Conversational Core Layer

**Goal:** The full agent/core/ layer working end-to-end.
A real multi-turn conversation with context memory before any tools exist.

---

### Task 2.1 — LLM Client + Session Manager

```
Implement the LLM client and Redis session manager.

agent/core/llm.py — from 02-TECHNICAL-PLAN.md Section 2.1:
- GeminiClient with generate() and generate_with_tools()
- Two model tiers: flash (gemini-1.5-flash) and pro (gemini-1.5-pro)
- get_llm() singleton

agent/core/session.py — from 02-TECHNICAL-PLAN.md Section 2.2:
- SessionManager with load(), save(), clear()
- Redis-backed with 1-hour TTL
- Calls smart_trim when history > 15 turns

agent/core/trimmer.py — from 02-TECHNICAL-PLAN.md Section 2.3:
- smart_trim(history, keep_latest) → summarises oldest turns via LLM (flash tier)

agent/prompts/trim_summary.py — the summarisation prompt

Test manually:
  from agent.core.session import SessionManager
  sm = SessionManager("test_user")
  await sm.save({"history": [{"role":"user","content":"hello"}], "style":{}, "turn_count":1})
  loaded = await sm.load()
  assert loaded["history"][0]["content"] == "hello"
```

---

### Task 2.2 — Memory System

```
Implement the long-term memory system.

agent/core/memory.py — from 02-TECHNICAL-PLAN.md Section 2.4 and 2.5:
- MemoryStore class: get_facts(), get_recent_sessions(), upsert_facts(), save_session_summary()
- extract_and_store() async function (fire-and-forget, never raises)

agent/prompts/memory_extract.py — from 02-TECHNICAL-PLAN.md Section 2.5

Run db/schema/007_analyst_memory.sql migration if not already run.

Test:
  store = MemoryStore("analyst_1")
  await store.upsert_facts(["Analyst focuses on route performance"])
  facts = await store.get_facts()
  assert "route performance" in facts[0]
```

---

### Task 2.3 — Inner Monologue + Style Detection

```
Implement reasoning and style layers.

agent/core/monologue.py — from 02-TECHNICAL-PLAN.md Section 2.6:
- run_inner_monologue(system, history, message) → (monologue_text, clean_response)
- Strips <think>...</think> before returning
- Uses flash tier

agent/prompts/monologue.py — from 02-TECHNICAL-PLAN.md Section 2.6

agent/core/style.py — from 02-TECHNICAL-PLAN.md Section 2.7:
- detect_style(history, current_style) → style dict
- Only re-runs every 5 turns
- Uses flash tier

Test inner monologue:
  mono, response = await run_inner_monologue(
      system="You are a data analyst.",
      history=[],
      message="Which routes have delays?"
  )
  assert "<think>" not in response    # stripped correctly
  assert len(mono) > 0                # reasoning was generated
  assert "route" in mono.lower()      # reasoning is relevant
```

---

### Task 2.4 — LangGraph Pipeline + Agent Entry Point

```
Wire everything into the LangGraph pipeline and main agent class.

agent/core/pipeline.py — from 02-TECHNICAL-PLAN.md Section 2.8:
- Full AgentState TypedDict
- All 7 nodes: load_session, inject_memory, detect_style, inner_monologue,
  execute_tools, generate_reply, save_session
- build_pipeline() → compiled graph

agent/prompts/system.py — from 02-TECHNICAL-PLAN.md Section 2.9:
- build_system_prompt(state) with memory + style + proactive rules

agent/persona.py — from 02-TECHNICAL-PLAN.md Section 3

agent/agent.py — from 02-TECHNICAL-PLAN.md Section 2.10:
- LogisticsMindAgent with chat() and reset()
- AgentResponse dataclass

agent/tools/__init__.py — from 02-TECHNICAL-PLAN.md Section 2.11:
- TOOL_REGISTRY and TOOL_SCHEMAS defined
- Stub all tool functions as placeholders returning {"success": True, "rows": [], "message": "stub"}

Week 2 milestone test — must pass before moving to Week 3:

  agent = LogisticsMindAgent(debug=True)

  r1 = await agent.chat("analyst_1", "Hello, I am analysing CeyLog route performance")
  r2 = await agent.chat("analyst_1", "What was I just telling you about?")
  assert "route" in r2.message.lower()   # session memory works

  r3 = await agent.chat("analyst_1", "What is my name?")
  # Should say it doesn't know the name — not hallucinate

  print(r1.thinking)   # Should show inner monologue reasoning

All three assertions must pass. The agent remembers within a session
and doesn't hallucinate facts it wasn't given.
```

---

## Week 3 — Tools

**Goal:** All 6 tools implemented and working.
Natural language → SQL → results → charts working end-to-end.

---

### Task 3.1 — Schema Context + query_database Tool

```
Implement the schema context and the most important tool.

agent/schema_context.py:
Full SCHEMA_CONTEXT string from original 02-TECHNICAL-PLAN.md Section 3.
Must describe every table, every important column, and the key query patterns.
Also describe all 4 analytical views in analytics schema.

agent/tools/query_database.py — from 02-TECHNICAL-PLAN.md Section 4.1:
- SQL generation using SCHEMA_CONTEXT as system prompt (flash tier)
- Safety check: reject DELETE, UPDATE, DROP, INSERT, CREATE, ALTER, TRUNCATE
- Execute with asyncpg
- Retry once on error: send error back to LLM to fix the SQL
- Return: {success, sql, columns, rows, row_count}

Register in TOOL_REGISTRY — replace the stub.

Test these 5 queries — all must return correct data:
1. "How many shipments were delivered last month?"
   → should return a count > 0

2. "Which 5 warehouses have the highest utilisation?"
   → should return exactly 5 rows with facility codes

3. "What is the on-time delivery rate by route for the last 90 days?"
   → should return multiple routes with percentage values

4. "Show me all incidents in Colombo this year"
   → should return rows from operations.incidents joined to core.districts

5. "Which companies have overdue invoices over 1 million LKR?"
   → should join finance.invoices to core.companies

All 5 must succeed. Fix schema_context if any query fails.
```

---

### Task 3.2 — generate_chart Tool

```
Implement the chart generation tool.

agent/tools/generate_chart.py — from original 02-TECHNICAL-PLAN.md Section 5:
- Accept data as JSON string (parse it inside the function)
- Support: bar, line, pie, scatter, heatmap, area, map, table
- CeyLog colours: primary #1B4F8C (navy), accent #E8B84B (gold)
- Return Plotly JSON via fig.to_json()

Special map type:
- Use px.scatter_mapbox centred on Sri Lanka (lat 7.87, lon 80.77, zoom 7)
- mapbox_style="carto-positron"
- x_column = district name, y_column = metric value
- Join with core.districts lat/lng for positioning

Register in TOOL_REGISTRY — replace the stub.

Test:
1. Query "top 5 routes by shipment count" → bar chart
   Verify chart_json is valid JSON with "data" and "layout" keys

2. Query "monthly shipment volume 2024" → line chart
   Verify x-axis has month labels

3. Query "warehouse utilisation by district" → map chart
   Verify mapbox layout in chart_json
```

---

### Task 3.3 — detect_anomalies Tool

```
Implement the anomaly detection tool.

agent/tools/detect_anomalies.py — from original 02-TECHNICAL-PLAN.md Section 6:
- Implement all 5 metric/entity combinations:
  * delivery_delay_hours by route
  * fuel_consumption_per_km by driver
  * incident_rate by vehicle
  * payment_delay_days by company
  * damage_rate by product
- Statistical detection: Z-score (|z| > 2.5) + IQR method
- LLM explanation per anomaly (flash tier, 1-2 sentences)
- Return top 10 anomalies sorted by z-score

Register in TOOL_REGISTRY — replace the stub.

Validation — all 5 injected anomalies must be detected:
  result = await detect_anomalies("delivery_delay_hours", "route", "365")
  route_codes = [a["entity"] for a in result["anomalies"]]
  assert "RT-COL-JAF-003" in route_codes    # must be top result

  result = await detect_anomalies("fuel_consumption_per_km", "driver", "365")
  driver_ids = [a["entity"] for a in result["anomalies"]]
  assert "DRV-0042" in driver_ids

Run all 5 validations. All must pass.
```

---

### Task 3.4 — forecast_metric + explain_query + get_schema_info Tools

```
Implement the remaining 3 tools.

agent/tools/forecast_metric.py — from original 02-TECHNICAL-PLAN.md Section 7:
- Prophet forecasting for: shipment_volume, revenue, delay_rate, fuel_cost
- yearly_seasonality=True
- Add Sri Lankan public holidays as custom seasonality:
  Sinhala New Year: April 13-14
  Vesak: May (full moon)
  Christmas: December 25
- Return forecast array with period, forecast, lower, upper
- Include trend direction and change_pct

Test: forecast shipment_volume for 3 months
- Verify if November is in forecast window: it shows higher than adjacent months
- Verify confidence intervals are < 40% of forecast value

agent/tools/explain_query.py:
- Generate SQL for a question (same as query_database) but DO NOT execute
- Additionally explain each major clause in plain English
- Return: {sql, explanation}

agent/tools/get_schema_info.py:
- Takes a topic string
- Returns relevant table(s), column list, sample query patterns
- References analytical views when relevant
- Pure LLM generation using SCHEMA_CONTEXT — no DB call needed

Register all 3 in TOOL_REGISTRY — replace stubs.
```

---

## Week 4 — API + Frontend + Full Integration

---

### Task 4.1 — FastAPI Backend

```
Build the FastAPI API.

api/main.py:
- FastAPI app with lifespan (init Redis + DB connections on startup)
- Include chat and health routers
- CORS: allow localhost:3000
- Request logging: user_id, message length, response time

api/routes/chat.py — from 02-TECHNICAL-PLAN.md Section 8:
- POST /chat → {user_id, message} → {message, tools_used, proactive, chart_json}
- Extract chart_json from tool_calls automatically
- 60 second timeout

api/routes/health.py:
- GET /health → {"status": "ok", "redis": bool, "postgres": bool}

api/models.py:
- ChatRequest, ChatResponse Pydantic models

Run: uvicorn api.main:app --reload --port 8000

Test with curl:
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "message": "How many shipments last week?"}'

Should return a real number from the database.
```

---

### Task 4.2 — Full Agent Integration Test

```
Run the 5 multi-turn test conversations before building the frontend.
Fix any issues found before proceeding.

Conversation 1 — Route analysis:
  Turn 1: "Which routes have the worst on-time delivery rate?"
          → Should call query_database + generate_chart
          → Should mention RT-COL-JAF-003 prominently
  Turn 2: "Why is RT-COL-JAF-003 so bad?"
          → Should call query_database for incidents on that route
          → Should give 2-3 specific root causes with numbers
  Turn 3: "Show me delay hours by month for that route as a line chart"
          → Should call query_database then generate_chart (line)
          → Should reference "that route" correctly from session memory

Conversation 2 — Anomaly discovery:
  Turn 1: "Are there any unusual patterns in driver fuel consumption?"
          → Should call detect_anomalies("fuel_consumption_per_km", "driver")
          → DRV-0042 must appear in response
  Turn 2: "Tell me more about that driver"
          → Should call query_database for DRV-0042 trip history
          → Should reference "that driver" correctly from memory

Conversation 3 — Forecasting:
  Turn 1: "Forecast our shipment volume for next 3 months"
          → Should call forecast_metric("shipment_volume", "3", "month")
          → Should return 3 future periods with numbers
  Turn 2: "What's driving the seasonal patterns?"
          → Should reference November spike from forecast results

Conversation 4 — Warehouse:
  Turn 1: "Which warehouses are near capacity?"
          → Should query warehouse utilisation
          → Should identify any over 85%
  Turn 2: "Show me a map of utilisation across Sri Lanka"
          → Should generate a map chart

Conversation 5 — Finance:
  Turn 1: "Which companies consistently pay late?"
          → Should call detect_anomalies("payment_delay_days", "company")
          → Should identify the anomalous company

All 5 conversations must complete with coherent multi-turn memory.
Fix tool routing, schema context, or prompts if any fail.
```

---

### Task 4.3 — React Frontend

```
Build the analytics chat UI.

Stack: React + Vite + Plotly.js
  npm create vite@latest frontend -- --template react
  cd frontend && npm install plotly.js-dist react-plotly.js axios

frontend/src/App.jsx — main layout:
  Left sidebar (280px): Schema Explorer + Suggested Questions
  Right main area: Chat Panel

frontend/src/components/ChatPanel.jsx:
  - Message thread with user/agent bubbles
  - Agent messages: white text on #1A2535, left border #1B4F8C
  - User messages: navy background
  - Render ChartRenderer inline below agent message if chart_json present
  - Tool badges below agent message: small tags showing which tools fired
    e.g. [🔍 query_database] [📊 generate_chart]
  - Typing indicator (3 animated dots) while waiting
  - Auto-scroll to latest message

frontend/src/components/ChartRenderer.jsx:
  - Accepts chart_json prop (Plotly JSON string)
  - Parses and renders with react-plotly.js
  - Dark theme: plot_bgcolor="#0F1923", paper_bgcolor="#1A2535", font color white
  - Responsive width (100% of chat panel)

frontend/src/components/SchemaExplorer.jsx:
  - Collapsible list of schemas → tables
  - Click a table → show column names in tooltip
  - Data: hardcode the schema structure (no API call needed)

frontend/src/components/SuggestedQuestions.jsx:
  - Shown when chat is empty
  - 6 clickable cards, clicking sends the question:
    * "Which routes have the worst on-time delivery rate?"
    * "Show warehouse utilisation across Sri Lanka on a map"
    * "Are there anomalies in driver fuel consumption?"
    * "Forecast shipment volume for next quarter"
    * "Which companies have overdue invoices?"
    * "What caused the most incidents last month?"

Design:
  Background:    #0F1923 (very dark navy)
  Panel bg:      #1A2535
  Primary:       #1B4F8C (CeyLog navy)
  Accent:        #E8B84B (gold)
  Text:          #E8EDF2
  Subtle border: #2A3A4F
```

---

## Week 5 — Polish + Portfolio

---

### Task 5.1 — Conversation Quality Tuning

```
Run all 5 test conversations from Task 4.2 again with the full UI.
Identify and fix quality issues.

Common issues to check:
□ Agent generating wrong SQL → add more examples to schema_context.py
□ Agent not generating charts when it should → strengthen persona prompt
□ Agent not being proactive → check PROACTIVE_RULES in system.py
□ "That route / that driver" not resolving from memory → check session trimmer
□ Anomaly descriptions too generic → improve explain_anomalies() LLM prompt
□ Forecast numbers unrealistic → check Prophet seasonality config
□ Response too long → add length guidance to persona

For every issue: identify root cause → fix the specific file → re-test.
Document fixes in agent/TUNING_NOTES.md.
```

---

### Task 5.2 — Anomaly Discovery Validation

```
Confirm all 8 patterns from 01-SYSTEM-DESIGN.md Section 5 are discoverable.

Run the agent on these prompts and verify correct findings:

1. "Find routes with unusually high delay rates"
   → Expected: RT-COL-JAF-003 appears as top anomaly

2. "Which drivers have abnormal fuel consumption?"
   → Expected: DRV-0042 is flagged with ~2x average

3. "Are any vehicles breaking down more than expected?"
   → Expected: VH-0031 shows pattern

4. "Which companies consistently pay late?"
   → Expected: anomalous company (187th) flagged with ~15 day average delay

5. "Which products have the highest damage rates?"
   → Expected: SKU-PHARM-099 flagged at 5x category average

6. "Show me monthly shipment volumes — any seasonal patterns?"
   → Expected: November spike clearly visible in chart

7. "How does the Colombo-Jaffna route perform in rainy months vs dry months?"
   → Expected: June-October noticeably worse

8. "Which vehicle needs the most frequent maintenance?"
   → Expected: VH-0031 flagged

All 8 must be discoverable through natural language conversation.
```

---

### Task 5.3 — Docker + One-Command Setup

```
Make the full project start with one command.

Update docker-compose.yml:
services:
  postgres:
    image: postgres:16
    environment: POSTGRES_DB=ceylog, POSTGRES_USER=user, POSTGRES_PASSWORD=password
    volumes: postgres_data + ./db/schema:/docker-entrypoint-initdb.d
    (Docker auto-runs .sql files in initdb.d on first start)

  redis:
    image: redis:7-alpine

  seeder:
    build: .
    command: python db/seed/seed.py
    depends_on: [postgres]
    profiles: ["seed"]   # only runs with: docker-compose --profile seed up seeder

  api:
    build: .
    command: uvicorn api.main:app --host 0.0.0.0 --port 8000
    ports: ["8000:8000"]
    depends_on: [postgres, redis]
    env_file: .env

  frontend:
    build: ./frontend
    ports: ["3000:80"]
    depends_on: [api]

Create Makefile:
  setup:
    docker-compose up -d postgres redis
    sleep 3
    docker-compose --profile seed run seeder
    docker-compose up -d api frontend

  dev:
    docker-compose up postgres redis api
    cd frontend && npm run dev

  reset:
    docker-compose down -v
    make setup

README setup section:
  git clone ...
  cp .env.example .env
  # Add GEMINI_API_KEY to .env
  make setup
  # Open http://localhost:3000
```

---

### Task 5.4 — Portfolio README

```
Write the complete README.md.

Structure:
1. Header with project name, one-liner, badges (Python, PostgreSQL, Gemini, LangGraph)
2. Screenshot: the chat UI with a chart visible (use a real screenshot from testing)
3. Overview: what it is, the fictional CeyLog company, what the agent can do
4. Architecture diagram (ASCII — matches 01-SYSTEM-DESIGN.md)
5. Database section: 18 tables, 5 schemas, 1.1M rows, embedded anomalies list
6. Agent capabilities with real example conversation (paste actual output from testing)
7. Tech stack table
8. Setup: make setup → open localhost:3000 (3 commands)
9. Example questions (10 natural language questions it can answer)
10. Conversational intelligence section:
    "The agent uses a multi-layer conversational architecture:
     Redis-backed session memory, PostgreSQL long-term memory,
     inner monologue reasoning, style adaptation, and proactive insights.
     This layer (agent/core/) is designed to be extracted into a
     standalone framework in future work."

The README should demonstrate to any reader:
- Complex database design skills (18 tables, proper normalisation)
- Production AI engineering (not a toy — 1.1M rows, real SQL generation)
- Conversational AI depth (not just a chatbot — memory, reasoning, proactive)
- Sri Lankan context (local company, island-wide operations)
```

---

## Milestone Summary

| Week | Deliverable | Milestone Test |
|------|-------------|----------------|
| 1 | PostgreSQL + 1.1M rows + anomalies seeded | Row counts match, all 5 anomalies verified |
| 2 | Conversational core working (no tools yet) | Session memory test passes |
| 3 | All 6 tools working | 5 test queries pass, 5 anomalies detected |
| 4 | Full agent + API + React UI | 5 multi-turn conversations work end-to-end |
| 5 | Portfolio-ready, one-command setup | `make setup` → working demo |

---

## Key Architecture Reminder

The agent/core/ layer IS the conversational intelligence —
it's the same architecture you designed for Conversify, just
built inline for this project.

When you're ready to build Conversify as a standalone package later:
- agent/core/ becomes the conversify/ package
- LogisticsMindAgent becomes ConversifyAgent (generic)
- Tool registration pattern stays identical
- The hard work is already done and validated

The transition will be straightforward because the architecture
was designed with extraction in mind.
```
