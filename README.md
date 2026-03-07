# LogisticsMind AI

**Conversational AI analytics platform for a fictional Sri Lankan logistics company.**
Natural language → SQL → charts → anomaly detection → forecasting. All in one chat.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791)
![Gemini](https://img.shields.io/badge/LLM-Gemini_1.5_Pro-4285F4)
![LangGraph](https://img.shields.io/badge/Pipeline-LangGraph-orange)
![Docker](https://img.shields.io/badge/Deploy-Docker-2496ED)

---

## What It Is

LogisticsMind AI is a senior data analyst you talk to in plain English.

It sits on top of a production-scale PostgreSQL database for **CeyLog** — a fictional Sri Lankan island-wide logistics company with warehouses, fleets, thousands of daily shipments, and 2 years of operational history.

You ask questions. It queries the database, generates charts, detects anomalies, and forecasts trends — using nothing but conversation.

```
Analyst: Which routes have the worst on-time delivery rate?

Agent: The 5 worst-performing routes are:
       1. RT-COL-JAF-003 — 58% on-time (network avg: 89%)
       2. RT-KAN-BAT-007 — 71% on-time
       ...
       RT-COL-JAF-003 stands out significantly. Want me to dig into what's driving it?

Analyst: Yes.

Agent: Three factors explain the JAF-003 delays:
       - 67% of delays cluster in June–October (monsoon season)
       - Vehicle VH-0089 handles 40% of trips on this route and has
         the highest breakdown rate in the fleet
       - Average loading time at WH-COL-02 is 2.3hr vs 1.1hr fleet avg
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        React Frontend                        │
│     Chat UI  ·  Plotly Charts  ·  Schema Explorer            │
└──────────────────────┬───────────────────────────────────────┘
                       │  /api/chat  (nginx proxy)
┌──────────────────────▼───────────────────────────────────────┐
│                       FastAPI  (api container)               │
└──────────────────────┬───────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────┐
│               LogisticsMind Agent (LangGraph)                │
│                                                              │
│  load_session → inject_memory → detect_style                 │
│       → inner_monologue → execute_tools                      │
│       → generate_reply  → save_session                       │
│                                                              │
│  Tools: query_database · generate_chart · detect_anomalies   │
│         forecast_metric · explain_query · get_schema_info    │
└──────┬───────────────────────────────────┬───────────────────┘
       │                                   │
┌──────▼──────┐                    ┌───────▼──────┐
│  PostgreSQL  │                   │    Redis      │
│  (18 tables) │                   │  (sessions)   │
│  ~1.1M rows  │                   └───────────────┘
└─────────────┘

All services run inside Docker — internal DNS, no localhost.
```

---

## Database — CeyLog Production Schema

**18 tables · 5 schemas · ~1.1 million rows · 2 years of history**

```
core/         — districts (25), companies (500), vendors (150), products (2,000)
warehouse/    — facilities (18), inventory_items (40k), stock_movements (150k)
fleet/        — vehicles (200), drivers (180), routes (80), trips (15k), gps_pings (500k)
operations/   — orders (25k), shipments (28k), tracking_events (180k), incidents (2.5k)
finance/      — invoices (24k), payments (22k), operational_costs (35k), sla_breaches (3.2k)
```

### Embedded Anomalies (for the AI to discover)

| Anomaly | Pattern |
|---------|---------|
| Route RT-COL-JAF-003 | 40% higher delay rate than comparable routes |
| Driver DRV-0042 | Fuel consumption 2× fleet average |
| Warehouse WH-GAL-01 | Utilisation always reported at exactly 87% |
| Company (187th) | Pays invoices consistently 15 days late |
| Product SKU-PHARM-099 | Damage rate 5× category average |
| November spike | Shipment volume +60% every November |
| Colombo → Jaffna | Delivery success drops 30% in monsoon months |
| Vehicle VH-0031 | Breakdown every ~8,000km exactly |

---

## Agent Capabilities

### 6 Tools

| Tool | What It Does |
|------|-------------|
| `query_database` | Converts NL to SQL, executes against CeyLog DB, returns results |
| `generate_chart` | Renders Plotly charts: bar, line, pie, scatter, heatmap, area, map |
| `detect_anomalies` | Z-score + IQR statistical outlier detection with LLM explanation |
| `forecast_metric` | Prophet time-series forecasting with Sri Lankan holidays |
| `explain_query` | Shows generated SQL without executing — builds analyst trust |
| `get_schema_info` | Schema introspection for the LLM to navigate 18 tables |

### Conversational Intelligence

The agent has a multi-layer architecture built in `agent/core/`:

- **Redis session memory** — maintains context across turns (1-hour TTL, 15-turn window)
- **PostgreSQL long-term memory** — facts and session summaries extracted by LLM, persisted across conversations
- **Inner monologue** — private reasoning (`<think>` tags) before every reply, using flash model
- **Style detection** — adapts formality and detail level to the analyst's communication style every 5 turns
- **Proactive insights** — flags surprising data patterns the analyst didn't ask about
- **Context trimming** — LLM-powered summarisation when history exceeds token budget

### Example Conversations

```
"Which routes have the worst on-time delivery rate?"
→ query_database + generate_chart (bar) → RT-COL-JAF-003 identified

"Are there anomalies in driver fuel consumption?"
→ detect_anomalies(fuel_consumption_per_km, driver) → DRV-0042 flagged at 2.1× avg

"Show warehouse utilisation across Sri Lanka on a map"
→ query_database + generate_chart (scatter_mapbox, centred Sri Lanka)

"Forecast our shipment volume for the next 3 months"
→ forecast_metric(shipment_volume, 3, month) → Prophet + Sri Lankan holidays

"Why is RT-COL-JAF-003 delayed? Show me the SQL you used"
→ explain_query → SQL shown + clause-by-clause explanation
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Database | PostgreSQL 16 |
| Mock data | Python + Faker + custom generators |
| Agent pipeline | LangGraph |
| LLM | Gemini 1.5 Pro (responses) + Gemini 1.5 Flash (reasoning, SQL, memory) |
| Session memory | Redis |
| Long-term memory | PostgreSQL (`analyst_facts`, `analyst_sessions`) |
| Charts | Plotly (interactive, dark theme) |
| Forecasting | Facebook Prophet with Sri Lankan holiday calendar |
| Anomaly detection | Z-score + IQR + LLM explanation |
| API | FastAPI |
| Frontend | React + Vite + react-plotly.js |
| Containers | Docker Compose (all-in) |

---

## Setup

**Prerequisites:** Docker, a Gemini API key.

```bash
git clone https://github.com/your-username/LogisticsMind-AI
cd LogisticsMind-AI
cp .env.example .env
# Edit .env — add your GEMINI_API_KEY
make setup
```

Open **http://localhost:3000**

That's it. `make setup` starts all containers, seeds the database with 1.1M rows, and launches the UI.

### Other commands

```bash
make dev      # start postgres + redis + api (without rebuilding frontend)
make logs     # tail api logs
make seed     # re-run the seeder
make reset    # wipe volumes and start fresh
make down     # stop everything
```

### Docker Services

| Service | Port | Notes |
|---------|------|-------|
| `postgres` | internal | Auto-migrates schema on first start |
| `redis` | internal | Session store, 1-hour TTL |
| `api` | 8000 | FastAPI, hot-reload in dev |
| `frontend` | 3000 | nginx + Vite React build |
| `seeder` | — | Profile: `seed` — runs once then exits |

All inter-service communication uses Docker service names (`postgres`, `redis`, `api`) — never localhost.

---

## Example Questions to Try

```
"Which routes have the worst on-time delivery rate?"
"Show warehouse utilisation across Sri Lanka on a map"
"Are there anomalies in driver fuel consumption?"
"Why does RT-COL-JAF-003 perform so poorly? Investigate it"
"Forecast our shipment volume for next quarter"
"Which companies have overdue invoices over 1 million LKR?"
"What caused the most incidents last month?"
"Show me monthly shipment volume for the last 2 years"
"Which products have the highest damage rates?"
"Are any vehicles breaking down more than expected?"
```

---

## Project Structure

```
logisticsmind/
├── docker-compose.yml          # All 5 services
├── Dockerfile                  # Python backend image
├── Makefile                    # Convenience commands
├── requirements.txt
│
├── db/
│   ├── schema/                 # 8 SQL files (auto-run by postgres on first start)
│   └── seed/                   # Mock data generators + anomaly injection
│       └── generators/         # core · warehouse · fleet · operations · finance
│
├── agent/
│   ├── agent.py                # LogisticsMindAgent (main entry point)
│   ├── persona.py              # CeyLog analyst persona
│   ├── schema_context.py       # Full schema description for SQL generation
│   ├── core/                   # llm · session · memory · monologue · style · pipeline
│   ├── tools/                  # 6 agent tools
│   └── prompts/                # System prompt · monologue · memory extraction
│
├── api/
│   ├── main.py                 # FastAPI app
│   └── routes/                 # /chat  ·  /health
│
└── frontend/
    ├── Dockerfile              # Node build → nginx
    ├── nginx.conf              # Proxies /api/ to api container
    └── src/
        ├── App.jsx
        └── components/         # ChatPanel · ChartRenderer · SchemaExplorer
```

---

## What Makes This Portfolio-Grade

1. **18 tables across 5 schemas** — complex real-world relational design with proper normalisation and indexing
2. **~1.1M mock rows** — production-scale volume, batch-inserted with performance in mind
3. **Embedded anomalies** — 8 deliberate patterns the AI can actually discover through conversation
4. **Geographic data** — all 25 Sri Lankan districts with lat/lng, choropleth maps
5. **Time-series history** — 2 years of operational data with seasonal patterns baked in
6. **Multi-layer conversational AI** — session memory + long-term memory + inner monologue + style adaptation
7. **Full analytics stack** — NL query + interactive charts + anomaly detection + forecasting
8. **Real business logic** — SLA breaches, credit limits, cold chain, monsoon seasonality
9. **One-command setup** — `make setup` → working demo, everything containerised
