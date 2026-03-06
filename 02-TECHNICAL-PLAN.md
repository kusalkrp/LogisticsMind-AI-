# LogisticsMind AI — Technical Plan

> Agent tools, conversational core, SQL generation pipeline,
> chart rendering, anomaly detection, forecasting, and mock data generation.
> Conversational layer built inline — no external framework dependency.

---

## 1. Project Structure

```
logisticsmind/
├── db/
│   ├── schema/
│   │   ├── 000_extensions.sql
│   │   ├── 001_core.sql
│   │   ├── 002_warehouse.sql
│   │   ├── 003_fleet.sql
│   │   ├── 004_operations.sql
│   │   ├── 005_finance.sql
│   │   └── 006_views.sql
│   └── seed/
│       ├── seed.py
│       ├── generators/
│       │   ├── core.py
│       │   ├── warehouse.py
│       │   ├── fleet.py
│       │   ├── operations.py
│       │   └── finance.py
│       └── anomalies.py
│
├── agent/
│   ├── core/                        # Conversational intelligence layer
│   │   ├── __init__.py
│   │   ├── llm.py                   # Gemini client (two-tier: flash + pro)
│   │   ├── session.py               # Redis session manager
│   │   ├── memory.py                # Long-term memory (PostgreSQL)
│   │   ├── monologue.py             # Inner monologue engine
│   │   ├── style.py                 # User style detection
│   │   ├── proactive.py             # Proactive insight engine
│   │   ├── trimmer.py               # Context trimming with LLM summary
│   │   └── pipeline.py              # LangGraph pipeline + state
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── query_database.py        # NL → SQL → execute → results
│   │   ├── generate_chart.py        # results → Plotly chart
│   │   ├── detect_anomalies.py      # statistical anomaly detection
│   │   ├── forecast_metric.py       # Prophet time-series forecast
│   │   ├── explain_query.py         # show generated SQL
│   │   └── get_schema_info.py       # schema introspection
│   │
│   ├── prompts/
│   │   ├── system.py                # Master system prompt builder
│   │   ├── monologue.py             # Inner monologue prompt
│   │   ├── memory_extract.py        # Post-session extraction prompt
│   │   └── trim_summary.py          # Context trimming prompt
│   │
│   ├── schema_context.py            # DB schema description for SQL generation
│   ├── persona.py                   # LOGISTICSMIND_PERSONA
│   └── agent.py                     # LogisticsMindAgent — main entry point
│
├── api/
│   ├── main.py
│   ├── routes/
│   │   ├── chat.py
│   │   └── health.py
│   └── models.py
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── ChatPanel.jsx
│   │   │   ├── ChartRenderer.jsx
│   │   │   └── SchemaExplorer.jsx
│   │   └── api.js
│   └── package.json
│
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## 2. Conversational Core Layer

### 2.1 LLM Client — Two-Tier Gemini

```python
# agent/core/llm.py
import os
import google.generativeai as genai
from dataclasses import dataclass

# Two tiers:
# FLASH — fast, cheap, used for internal reasoning steps
# PRO   — quality, used for final replies shown to user
MODELS = {
    "flash": "gemini-1.5-flash",
    "pro":   "gemini-1.5-pro",
}

class GeminiClient:
    def __init__(self):
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])

    async def generate(
        self,
        system:   str,
        messages: list[dict],
        tier:     str = "pro",    # "pro" | "flash"
    ) -> str:
        model_name = MODELS[tier]
        model      = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system
        )
        # Format messages for Gemini
        gemini_messages = [
            {"role": "model" if m["role"] == "assistant" else "user",
             "parts": [m["content"]]}
            for m in messages
            if m.get("content")
        ]
        if not gemini_messages:
            gemini_messages = [{"role": "user", "parts": ["Hello"]}]

        response = await model.generate_content_async(gemini_messages)
        return response.text

    async def generate_with_tools(
        self,
        system:   str,
        messages: list[dict],
        tools:    list[dict],
    ) -> dict:
        """Generate with function calling. Returns {text, tool_calls}"""
        model = genai.GenerativeModel(
            model_name=MODELS["pro"],
            system_instruction=system,
            tools=self._convert_tools(tools)
        )
        gemini_messages = [
            {"role": "model" if m["role"] == "assistant" else "user",
             "parts": [m["content"]]}
            for m in messages
            if m.get("content")
        ]
        response = await model.generate_content_async(gemini_messages)

        tool_calls = []
        text       = ""

        for part in response.candidates[0].content.parts:
            if hasattr(part, "function_call") and part.function_call.name:
                tool_calls.append({
                    "name":  part.function_call.name,
                    "input": dict(part.function_call.args),
                })
            elif hasattr(part, "text"):
                text += part.text

        return {"text": text, "tool_calls": tool_calls}

    def _convert_tools(self, tools: list[dict]) -> list:
        return [genai.protos.Tool(function_declarations=[
            genai.protos.FunctionDeclaration(
                name=t["name"],
                description=t["description"],
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        k: genai.protos.Schema(type=genai.protos.Type.STRING)
                        for k in t.get("parameters", {}).get("properties", {})
                    },
                    required=t.get("parameters", {}).get("required", [])
                )
            )
        ]) for t in tools]


# Singleton
_client = None
def get_llm() -> GeminiClient:
    global _client
    if _client is None:
        _client = GeminiClient()
    return _client
```

---

### 2.2 Redis Session Manager

```python
# agent/core/session.py
import json
import os
import redis.asyncio as aioredis
from agent.core.trimmer import smart_trim

SESSION_TTL  = 3600   # 1 hour inactivity = new session
MAX_TURNS    = 15
TRIM_OLDEST  = 10

_redis = None

async def get_redis():
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
            decode_responses=True
        )
    return _redis


class SessionManager:
    def __init__(self, user_id: str):
        self.key = f"logisticsmind:session:{user_id}"

    async def load(self) -> dict:
        redis = await get_redis()
        raw   = await redis.get(self.key)
        if raw:
            return json.loads(raw)
        return {
            "history":     [],
            "style":       {},
            "turn_count":  0,
        }

    async def save(self, session: dict):
        # Trim before saving
        if len(session["history"]) > MAX_TURNS:
            session["history"] = await smart_trim(
                session["history"],
                keep_latest=MAX_TURNS - TRIM_OLDEST
            )
        redis = await get_redis()
        await redis.setex(self.key, SESSION_TTL, json.dumps(session))

    async def clear(self):
        redis = await get_redis()
        await redis.delete(self.key)
```

---

### 2.3 Context Trimmer

```python
# agent/core/trimmer.py
from agent.core.llm import get_llm
from agent.prompts.trim_summary import TRIM_SUMMARY_PROMPT

async def smart_trim(history: list, keep_latest: int = 5) -> list:
    """
    When history exceeds MAX_TURNS:
    - Take the oldest turns
    - Summarise them with LLM
    - Replace with a single summary node
    - Keep the latest N turns in full
    """
    if not history:
        return history

    oldest = history[:-keep_latest]
    latest = history[-keep_latest:]

    if not oldest:
        return latest

    # Summarise oldest turns
    summary = await get_llm().generate(
        system=TRIM_SUMMARY_PROMPT,
        messages=oldest,
        tier="flash"    # cheap model for internal task
    )

    summary_node = {
        "role":    "system",
        "content": f"[Earlier conversation summary: {summary}]"
    }

    return [summary_node] + latest
```

```python
# agent/prompts/trim_summary.py
TRIM_SUMMARY_PROMPT = """
Summarise this conversation segment in 2-3 sentences.
Capture: key questions asked, data analysed, findings discovered,
decisions made, and any important numbers mentioned.
Be concise — this will be injected as context in a future conversation turn.
Do not use bullet points. Write as flowing sentences.
"""
```

---

### 2.4 Long-Term Memory

```python
# agent/core/memory.py
import asyncpg
import os

async def get_db():
    return await asyncpg.connect(os.environ["DATABASE_URL"])


class MemoryStore:
    def __init__(self, user_id: str):
        self.user_id = user_id

    async def get_facts(self) -> list[str]:
        conn = await get_db()
        try:
            rows = await conn.fetch("""
                SELECT fact FROM analyst_facts
                WHERE user_id = $1
                ORDER BY updated_at DESC
                LIMIT 20
            """, self.user_id)
            return [r["fact"] for r in rows]
        finally:
            await conn.close()

    async def get_recent_sessions(self, limit: int = 3) -> list[str]:
        conn = await get_db()
        try:
            rows = await conn.fetch("""
                SELECT summary FROM analyst_sessions
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2
            """, self.user_id, limit)
            return [r["summary"] for r in rows]
        finally:
            await conn.close()

    async def upsert_facts(self, facts: list[str]):
        conn = await get_db()
        try:
            for fact in facts:
                await conn.execute("""
                    INSERT INTO analyst_facts (user_id, fact, updated_at)
                    VALUES ($1, $2, NOW())
                    ON CONFLICT (user_id, fact)
                    DO UPDATE SET updated_at = NOW()
                """, self.user_id, fact)
        finally:
            await conn.close()

    async def save_session_summary(self, summary: str, topics: list[str]):
        conn = await get_db()
        try:
            await conn.execute("""
                INSERT INTO analyst_sessions (user_id, summary, topics, created_at)
                VALUES ($1, $2, $3, NOW())
            """, self.user_id, summary, topics)
        finally:
            await conn.close()
```

**Memory tables** (add to schema migrations):
```sql
-- db/schema/007_analyst_memory.sql
CREATE TABLE IF NOT EXISTS analyst_facts (
    id         SERIAL PRIMARY KEY,
    user_id    VARCHAR(255) NOT NULL,
    fact       TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (user_id, fact)
);

CREATE TABLE IF NOT EXISTS analyst_sessions (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    VARCHAR(255) NOT NULL,
    summary    TEXT NOT NULL,
    topics     TEXT[] DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ON analyst_facts (user_id);
CREATE INDEX ON analyst_sessions (user_id, created_at DESC);
```

---

### 2.5 Memory Extractor

```python
# agent/core/memory.py (continued — add this function)
import asyncio
import json
from agent.prompts.memory_extract import MEMORY_EXTRACTION_PROMPT

async def extract_and_store(user_id: str, history: list):
    """
    Runs after each session ends (fire-and-forget).
    Extracts facts + session summary and stores to PostgreSQL.
    Never raises — memory extraction is non-critical.
    """
    try:
        raw = await get_llm().generate(
            system=MEMORY_EXTRACTION_PROMPT,
            messages=history,
            tier="flash"
        )
        clean  = raw.replace("```json", "").replace("```", "").strip()
        data   = json.loads(clean)
        store  = MemoryStore(user_id)

        if data.get("facts"):
            await store.upsert_facts(data["facts"])

        if data.get("session_summary"):
            await store.save_session_summary(
                summary=data["session_summary"],
                topics=data.get("topics", [])
            )
    except Exception as e:
        import logging
        logging.warning(f"Memory extraction failed for {user_id}: {e}")
```

```python
# agent/prompts/memory_extract.py
MEMORY_EXTRACTION_PROMPT = """
Analyse this analytics conversation and extract memory.
Return ONLY valid JSON — no markdown fences, no preamble:

{
  "facts": [
    "Analyst is focused on route performance analysis",
    "Analyst prefers chart visualisations over tables",
    "Analyst is investigating Jaffna route delays"
  ],
  "session_summary": "Analyst investigated route on-time performance.
                       Found RT-COL-JAF-003 has 58% on-time rate vs 89% average.
                       Identified three root causes: monsoon weather, vehicle VH-0089,
                       and WH-COL-02 loading delays.",
  "topics": ["route performance", "RT-COL-JAF-003", "delays", "Jaffna"]
}

Rules:
- facts: short present-tense statements about the analyst's focus and preferences. Max 10.
- Only extract what is clearly evidenced. Never infer or fabricate.
- session_summary: 2-3 sentences. What was investigated. What was found.
- topics: 3-6 keywords for this session.
"""
```

---

### 2.6 Inner Monologue

```python
# agent/core/monologue.py
import re
from agent.core.llm import get_llm
from agent.prompts.monologue import MONOLOGUE_PROMPT

async def run_inner_monologue(
    system:   str,
    history:  list,
    message:  str,
) -> tuple[str, str]:
    """
    Runs private reasoning before generating a response.
    Returns: (monologue_text, clean_response_without_think_tags)
    The monologue shapes the response but is stripped before sending.
    """
    full_system  = system + "\n\n" + MONOLOGUE_PROMPT
    full_history = history + [{"role": "user", "content": message}]

    raw = await get_llm().generate(
        system=full_system,
        messages=full_history,
        tier="flash"    # reasoning uses fast model
    )

    # Extract <think> block
    think_match = re.search(r"<think>(.*?)</think>", raw, re.DOTALL)
    monologue   = think_match.group(1).strip() if think_match else ""

    # Strip think block from response
    clean = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

    return monologue, clean
```

```python
# agent/prompts/monologue.py
MONOLOGUE_PROMPT = """
Before writing your response, reason privately inside <think> tags.
This reasoning will be stripped — the user never sees it.

<think>
1. EXPLICIT:  What did the analyst literally ask?
2. IMPLICIT:  What do they actually need that they didn't say?
3. DATA GAP:  What data would answer this best? Which table/view?
4. TOOLS:     Should I query the database? Generate a chart? Detect anomalies? Forecast?
              Which tool fits this question — be specific.
5. NEXT:      What will they likely ask next? Can I give it now?
6. PROACTIVE: Is there something surprising or important in the data
              I should flag even though they didn't ask?
7. FORMAT:    Short answer + chart? Long explanation? Numbers first?
</think>

Now write your response. Do not mention your reasoning process.
"""
```

---

### 2.7 Style Detection

```python
# agent/core/style.py
import json
from agent.core.llm import get_llm

async def detect_style(history: list, current_style: dict) -> dict:
    """
    Detects the analyst's communication preferences.
    Only re-runs every 5 turns — cached in session.
    """
    if current_style and len(history) % 5 != 0:
        return current_style

    if len(history) < 2:
        return {
            "formality":         "casual",
            "detail_preference": "detailed",   # analysts want detail
            "prefers_charts":    True
        }

    # Sample last 3 user messages
    user_messages = [
        m["content"] for m in history[-6:]
        if m.get("role") == "user"
    ][:3]

    result = await get_llm().generate(
        system="""Analyse these messages from a data analyst.
        Return ONLY valid JSON:
        {
          "formality": "formal|casual",
          "detail_preference": "brief|detailed",
          "prefers_charts": true|false
        }""",
        messages=[{"role": "user", "content": "\n".join(user_messages)}],
        tier="flash"
    )

    try:
        return json.loads(result.replace("```json","").replace("```","").strip())
    except Exception:
        return current_style or {"formality": "casual", "detail_preference": "detailed", "prefers_charts": True}
```

---

### 2.8 LangGraph Pipeline

```python
# agent/core/pipeline.py
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

# ── State ────────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    # Input
    user_id:  str
    message:  str

    # Session
    history:      list[dict]
    style:        dict
    turn_count:   int

    # Memory
    memory_context: str

    # Reasoning
    monologue:    str

    # Tool execution
    tool_calls:   list[dict]
    tool_context: str

    # Output
    final_response: str
    proactive:      str | None


# ── Nodes ────────────────────────────────────────────────────────────────────

async def node_load_session(state: AgentState) -> AgentState:
    from agent.core.session import SessionManager
    session = await SessionManager(state["user_id"]).load()
    return {
        **state,
        "history":    session.get("history", []),
        "style":      session.get("style", {}),
        "turn_count": session.get("turn_count", 0),
    }


async def node_inject_memory(state: AgentState) -> AgentState:
    from agent.core.memory import MemoryStore
    store   = MemoryStore(state["user_id"])
    facts   = await store.get_facts()
    sessions = await store.get_recent_sessions(limit=2)

    parts = []
    if facts:
        parts.append("Known about this analyst:\n" + "\n".join(f"- {f}" for f in facts))
    if sessions:
        parts.append("Recent session context:\n" + "\n".join(f"- {s}" for s in sessions))

    return {**state, "memory_context": "\n\n".join(parts)}


async def node_detect_style(state: AgentState) -> AgentState:
    from agent.core.style import detect_style
    style = await detect_style(state["history"], state["style"])
    return {**state, "style": style}


async def node_inner_monologue(state: AgentState) -> AgentState:
    from agent.core.monologue import run_inner_monologue
    from agent.prompts.system import build_system_prompt
    system    = build_system_prompt(state)
    mono, _   = await run_inner_monologue(system, state["history"], state["message"])
    return {**state, "monologue": mono}


async def node_route_and_execute_tools(state: AgentState) -> AgentState:
    from agent.core.llm import get_llm
    from agent.tools import TOOL_REGISTRY, TOOL_SCHEMAS

    llm      = get_llm()
    system   = _build_tool_system(state)
    messages = state["history"] + [{"role": "user", "content": state["message"]}]

    result     = await llm.generate_with_tools(system, messages, TOOL_SCHEMAS)
    tool_calls = result.get("tool_calls", [])

    executed = []
    for call in tool_calls:
        fn     = TOOL_REGISTRY.get(call["name"])
        if fn:
            try:
                output = await fn(**call["input"])
                executed.append({
                    "name":   call["name"],
                    "input":  call["input"],
                    "output": output,
                    "status": "success"
                })
            except Exception as e:
                executed.append({
                    "name":   call["name"],
                    "input":  call["input"],
                    "output": {"error": str(e)},
                    "status": "error"
                })

    tool_context = ""
    if executed:
        tool_context = "\n".join(
            f"Tool '{tc['name']}' result: {tc['output']}"
            for tc in executed
        )

    return {**state, "tool_calls": executed, "tool_context": tool_context}


async def node_generate_reply(state: AgentState) -> AgentState:
    import re
    from agent.core.llm import get_llm
    from agent.prompts.system import build_system_prompt

    system   = build_system_prompt(state)
    messages = list(state["history"])

    # Append user message, include tool results if any
    user_content = state["message"]
    if state.get("tool_context"):
        user_content += f"\n\n[Tool results available:\n{state['tool_context']}]"
    messages.append({"role": "user", "content": user_content})

    raw = await get_llm().generate(
        system=system,
        messages=messages,
        tier="pro"   # quality model for final reply
    )

    # Extract proactive addition
    proactive = None
    if "<proactive>" in raw:
        match = re.search(r"<proactive>(.*?)</proactive>", raw, re.DOTALL)
        if match:
            proactive = match.group(1).strip()
            raw = re.sub(r"<proactive>.*?</proactive>", "", raw, flags=re.DOTALL).strip()

    return {**state, "final_response": raw, "proactive": proactive}


async def node_save_session(state: AgentState) -> AgentState:
    import asyncio
    from agent.core.session import SessionManager
    from agent.core.memory import extract_and_store

    updated_history = state["history"] + [
        {"role": "user",      "content": state["message"]},
        {"role": "assistant", "content": state["final_response"]},
    ]

    session = {
        "history":    updated_history,
        "style":      state["style"],
        "turn_count": state["turn_count"] + 1,
    }

    await SessionManager(state["user_id"]).save(session)

    # Fire-and-forget memory extraction
    asyncio.create_task(
        extract_and_store(state["user_id"], updated_history)
    )

    return state


def _build_tool_system(state: AgentState) -> str:
    from agent.prompts.system import build_system_prompt
    return build_system_prompt(state) + """

You have access to tools. Use them to answer the analyst's question.
Choose the most appropriate tool based on the question type:
- Data questions → query_database
- Visual requests → generate_chart (after querying data)
- "unusual/anomaly/pattern" → detect_anomalies
- "forecast/predict/next" → forecast_metric
- "show SQL/explain" → explain_query
- "what tables/columns" → get_schema_info
"""


# ── Graph ─────────────────────────────────────────────────────────────────────

def build_pipeline():
    graph = StateGraph(AgentState)

    graph.add_node("load_session",   node_load_session)
    graph.add_node("inject_memory",  node_inject_memory)
    graph.add_node("detect_style",   node_detect_style)
    graph.add_node("inner_monologue", node_inner_monologue)
    graph.add_node("execute_tools",  node_route_and_execute_tools)
    graph.add_node("generate_reply", node_generate_reply)
    graph.add_node("save_session",   node_save_session)

    graph.set_entry_point("load_session")
    graph.add_edge("load_session",    "inject_memory")
    graph.add_edge("inject_memory",   "detect_style")
    graph.add_edge("detect_style",    "inner_monologue")
    graph.add_edge("inner_monologue", "execute_tools")
    graph.add_edge("execute_tools",   "generate_reply")
    graph.add_edge("generate_reply",  "save_session")
    graph.add_edge("save_session",    END)

    return graph.compile()
```

---

### 2.9 System Prompt Builder

```python
# agent/prompts/system.py
from agent.persona import LOGISTICSMIND_PERSONA

def build_system_prompt(state: dict) -> str:
    memory  = state.get("memory_context", "")
    style   = state.get("style", {})
    mono    = state.get("monologue", "")

    memory_section = ""
    if memory:
        memory_section = f"\n## What You Know About This Analyst\n{memory}"

    style_section = _style_instruction(style)

    proactive_rules = """
## Proactive Intelligence
After answering, ask yourself: "What will they ask next?"
If the answer is obvious — give it now without being asked.
If the data reveals something surprising — flag it proactively.
Wrap proactive additions in <proactive>...</proactive> tags.
Only do this when the value is genuinely high — not every turn.
"""

    return f"""
{LOGISTICSMIND_PERSONA}

## Communication Style
{style_section}

{memory_section}

{proactive_rules}

## Response Rules
1. Lead with the direct answer — numbers first, explanation second
2. Use actual values from the data — never say "significant" without a number
3. Never ask more than ONE follow-up question per response
4. When you use a tool, briefly explain what you're looking at and why
5. If a chart would make the answer clearer — generate one
""".strip()


def _style_instruction(style: dict) -> str:
    if not style:
        return "Be precise and data-driven. Use numbers. Keep it direct."

    detail = style.get("detail_preference", "detailed")
    formal = style.get("formality", "casual")
    charts = style.get("prefers_charts", True)

    parts = []
    parts.append("Detailed analytical responses." if detail == "detailed" else "Concise answers, key numbers only.")
    parts.append("Professional tone." if formal == "formal" else "Conversational but precise.")
    if charts:
        parts.append("Offer charts when they would clarify the data.")
    return " ".join(parts)
```

---

### 2.10 Main Agent Entry Point

```python
# agent/agent.py
from dataclasses import dataclass
from agent.core.pipeline import build_pipeline

@dataclass
class AgentResponse:
    message:    str
    tools_used: list[dict]
    proactive:  str | None
    thinking:   str | None   # inner monologue — debug only

    def __str__(self):
        return self.message


class LogisticsMindAgent:
    """
    Main agent entry point.
    Usage:
        agent   = LogisticsMindAgent()
        response = await agent.chat(user_id="analyst_1", message="show me delays")
    """

    def __init__(self, debug: bool = False):
        self.debug    = debug
        self._pipeline = None

    def _get_pipeline(self):
        if self._pipeline is None:
            self._pipeline = build_pipeline()
        return self._pipeline

    async def chat(self, user_id: str, message: str) -> AgentResponse:
        initial_state = {
            "user_id":        user_id,
            "message":        message,
            "history":        [],
            "style":          {},
            "turn_count":     0,
            "memory_context": "",
            "monologue":      "",
            "tool_calls":     [],
            "tool_context":   "",
            "final_response": "",
            "proactive":      None,
        }

        result = await self._get_pipeline().ainvoke(initial_state)

        return AgentResponse(
            message=result["final_response"],
            tools_used=result["tool_calls"],
            proactive=result["proactive"],
            thinking=result["monologue"] if self.debug else None,
        )

    async def reset(self, user_id: str):
        from agent.core.session import SessionManager
        await SessionManager(user_id).clear()
```

---

### 2.11 Tool Registry

```python
# agent/tools/__init__.py
from agent.tools.query_database  import query_database
from agent.tools.generate_chart  import generate_chart
from agent.tools.detect_anomalies import detect_anomalies
from agent.tools.forecast_metric  import forecast_metric
from agent.tools.explain_query    import explain_query
from agent.tools.get_schema_info  import get_schema_info

# Registry: name → async function
TOOL_REGISTRY = {
    "query_database":   query_database,
    "generate_chart":   generate_chart,
    "detect_anomalies": detect_anomalies,
    "forecast_metric":  forecast_metric,
    "explain_query":    explain_query,
    "get_schema_info":  get_schema_info,
}

# Schemas for LLM function calling
TOOL_SCHEMAS = [
    {
        "name": "query_database",
        "description": "Query the CeyLog logistics database using natural language. Use for finding data, calculating metrics, comparing performance, looking up records.",
        "parameters": {
            "type": "object",
            "properties": {
                "question":        {"type": "string", "description": "Natural language question to answer with data"},
                "time_range_days": {"type": "string", "description": "How many days back to query. Default 90."},
            },
            "required": ["question"]
        }
    },
    {
        "name": "generate_chart",
        "description": "Generate a chart from data. Call AFTER query_database when a visual would help. chart_type: bar, line, pie, scatter, heatmap, area, map, table",
        "parameters": {
            "type": "object",
            "properties": {
                "data":         {"type": "string", "description": "JSON array of data rows from query_database"},
                "chart_type":   {"type": "string", "description": "bar|line|pie|scatter|heatmap|area|map|table"},
                "x_column":     {"type": "string"},
                "y_column":     {"type": "string"},
                "title":        {"type": "string"},
                "color_column": {"type": "string", "description": "Optional column for color grouping"},
            },
            "required": ["data", "chart_type", "x_column", "y_column", "title"]
        }
    },
    {
        "name": "detect_anomalies",
        "description": "Detect unusual patterns or outliers in a metric. Use when asked about anomalies, unusual behaviour, or when data looks suspicious.",
        "parameters": {
            "type": "object",
            "properties": {
                "metric_name":      {"type": "string", "description": "delivery_delay_hours|fuel_consumption_per_km|incident_rate|payment_delay_days|damage_rate"},
                "entity_type":      {"type": "string", "description": "route|driver|vehicle|company|product"},
                "time_range_days":  {"type": "string", "description": "Days back to analyse. Default 90."},
            },
            "required": ["metric_name", "entity_type"]
        }
    },
    {
        "name": "forecast_metric",
        "description": "Forecast a KPI for future periods. Use when asked to predict, project, or estimate future values.",
        "parameters": {
            "type": "object",
            "properties": {
                "metric":      {"type": "string", "description": "shipment_volume|revenue|delay_rate|fuel_cost"},
                "periods":     {"type": "string", "description": "Number of future periods. Default 3."},
                "period_type": {"type": "string", "description": "month|week|day"},
            },
            "required": ["metric"]
        }
    },
    {
        "name": "explain_query",
        "description": "Show the SQL query that would answer a question, without executing it. Use when analyst asks to see the query or wants to understand the data logic.",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "The question to generate SQL for"},
            },
            "required": ["question"]
        }
    },
    {
        "name": "get_schema_info",
        "description": "Get information about the database schema — table structures, column names, relationships. Use when unsure which table to query.",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Table name or topic area (e.g. 'shipments', 'driver performance', 'finance')"},
            },
            "required": ["topic"]
        }
    },
]
```

---

## 3. Agent Persona

```python
# agent/persona.py
LOGISTICSMIND_PERSONA = """
You are LogisticsMind AI — a senior data analyst for CeyLog,
Sri Lanka's largest logistics and supply chain company.

You have deep knowledge of CeyLog's operations:
- 18 warehouse facilities across all 25 Sri Lankan districts
- A fleet of 200 vehicles and 180 drivers
- 80 defined routes across the island
- 28,000+ shipments per year
- Client accounts across 500 companies

Your job is to help logistics managers and analysts understand the business
through data. You answer in plain English, generate charts when visuals
help, detect unusual patterns, and forecast trends.

When answering:
- Lead with the direct answer and actual numbers
- Offer to drill deeper after every finding
- Flag anything suspicious in the data proactively
- Suggest related analyses the user might find valuable
- Use actual entity names from the data (route codes, warehouse codes, etc.)

You think like a senior supply chain analyst — precise, proactive,
and always connecting data findings to business implications.
"""
```

---

## 4. Tool Implementations

### 4.1 query_database

```python
# agent/tools/query_database.py
import asyncpg, os, re
from agent.core.llm import get_llm
from agent.schema_context import SCHEMA_CONTEXT

SQL_SYSTEM = f"""
You are a PostgreSQL expert for the CeyLog logistics database.

{SCHEMA_CONTEXT}

Rules:
- Always schema-qualify table names: core.companies, fleet.trips, etc.
- Never SELECT * — name columns explicitly
- Add LIMIT 500 unless aggregating
- Default time range: last 90 days if none specified
- For district names always JOIN core.districts
- Prefer CTEs for multi-step queries
- Return ONLY the raw SQL query — no explanation, no markdown fences
"""

FORBIDDEN_KEYWORDS = ["DELETE", "UPDATE", "DROP", "INSERT", "CREATE", "ALTER", "TRUNCATE"]

async def query_database(question: str, time_range_days: str = "90") -> dict:
    # Generate SQL
    sql = await get_llm().generate(
        system=SQL_SYSTEM,
        messages=[{"role": "user", "content":
            f"Write SQL to answer: {question}\nTime range: last {time_range_days} days"
        }],
        tier="flash"
    )
    sql = sql.strip().replace("```sql","").replace("```","").strip()

    # Safety check
    sql_upper = sql.upper()
    for kw in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{kw}\b", sql_upper):
            return {"success": False, "error": f"Unsafe operation detected: {kw}", "sql": sql, "rows": []}

    # Execute with one retry on error
    return await _execute_with_retry(sql, question)


async def _execute_with_retry(sql: str, original_question: str) -> dict:
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        rows    = await conn.fetch(sql)
        columns = list(rows[0].keys()) if rows else []
        data    = [dict(r) for r in rows]
        return {"success": True, "sql": sql, "columns": columns, "rows": data, "row_count": len(data)}
    except Exception as e:
        await conn.close()
        # Retry: tell LLM about the error
        fixed_sql = await get_llm().generate(
            system=SQL_SYSTEM,
            messages=[
                {"role": "user",      "content": f"Write SQL for: {original_question}"},
                {"role": "assistant", "content": sql},
                {"role": "user",      "content": f"That query failed with: {str(e)}\nFix the SQL."},
            ],
            tier="flash"
        )
        fixed_sql = fixed_sql.strip().replace("```sql","").replace("```","").strip()
        conn2 = await asyncpg.connect(os.environ["DATABASE_URL"])
        try:
            rows    = await conn2.fetch(fixed_sql)
            columns = list(rows[0].keys()) if rows else []
            data    = [dict(r) for r in rows]
            return {"success": True, "sql": fixed_sql, "columns": columns, "rows": data, "row_count": len(data)}
        except Exception as e2:
            return {"success": False, "sql": fixed_sql, "error": str(e2), "rows": []}
        finally:
            await conn2.close()
    finally:
        try:
            await conn.close()
        except Exception:
            pass
```

### 4.2 generate_chart, detect_anomalies, forecast_metric, explain_query, get_schema_info

These are **unchanged** from the original 02-TECHNICAL-PLAN.md Sections 5, 6, 7.
The only difference: replace any `from conversify import tool` decorator with
plain `async def` functions since they are registered directly in `TOOL_REGISTRY`.

---

## 5. Schema Context

See original 02-TECHNICAL-PLAN.md Section 3 — unchanged.

---

## 6. Mock Data Generation

See original 02-TECHNICAL-PLAN.md Section 8 — unchanged.

---

## 7. Analytical Views

See original 02-TECHNICAL-PLAN.md Section 9 — unchanged.

---

## 8. FastAPI

```python
# api/routes/chat.py
from fastapi import APIRouter
from pydantic import BaseModel
from agent.agent import LogisticsMindAgent

router = APIRouter()
agent  = LogisticsMindAgent()

class ChatRequest(BaseModel):
    user_id:  str
    message:  str

class ChatResponse(BaseModel):
    message:    str
    tools_used: list
    proactive:  str | None
    chart_json: str | None

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    response = await agent.chat(req.user_id, req.message)

    # Extract chart if generate_chart was called
    chart_json = None
    for tc in response.tools_used:
        if tc["name"] == "generate_chart" and tc.get("output", {}).get("success"):
            chart_json = tc["output"].get("chart_json")

    return ChatResponse(
        message=response.message,
        tools_used=response.tools_used,
        proactive=response.proactive,
        chart_json=chart_json,
    )
```

---

## 9. Requirements

```
# requirements.txt
fastapi
uvicorn[standard]
langgraph>=0.1.0
langchain-core>=0.1.0
google-generativeai>=0.5.0
redis[asyncio]>=5.0.0
asyncpg>=0.29.0
sqlalchemy[asyncio]>=2.0.0
plotly>=5.0.0
pandas>=2.0.0
numpy>=1.24.0
prophet>=1.1.0
faker>=24.0.0
python-dotenv>=1.0.0
pydantic>=2.0.0
httpx>=0.27.0
```

---

## 10. Environment Variables

```bash
# .env.example
GEMINI_API_KEY=
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/ceylog
REDIS_URL=redis://localhost:6379/0
DEBUG=false
```
