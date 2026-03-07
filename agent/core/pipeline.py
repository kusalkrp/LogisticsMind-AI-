"""LangGraph pipeline — the conversational state machine."""
from typing import TypedDict
from langgraph.graph import StateGraph, END


class AgentState(TypedDict):
    user_id: str
    message: str
    history: list[dict]
    style: dict
    turn_count: int
    memory_context: str
    monologue: str
    tool_calls: list[dict]
    tool_context: str
    final_response: str
    proactive: str | None


async def node_load_session(state: AgentState) -> AgentState:
    from agent.core.session import SessionManager
    session = await SessionManager(state["user_id"]).load()
    return {
        **state,
        "history": session.get("history", []),
        "style": session.get("style", {}),
        "turn_count": session.get("turn_count", 0),
    }


async def node_inject_memory(state: AgentState) -> AgentState:
    from agent.core.memory import MemoryStore
    store = MemoryStore(state["user_id"])
    facts = await store.get_facts()
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
    system = build_system_prompt(state)
    mono, _ = await run_inner_monologue(system, state["history"], state["message"])
    return {**state, "monologue": mono}


async def _execute_calls(calls: list, registry: dict) -> list:
    """Run a list of tool calls and return results."""
    import json
    executed = []
    for call in calls:
        fn = registry.get(call["name"])
        if fn:
            try:
                output = await fn(**call["input"])
                executed.append({"name": call["name"], "input": call["input"], "output": output, "status": "success"})
            except Exception as e:
                executed.append({"name": call["name"], "input": call["input"], "output": {"error": str(e)}, "status": "error"})
    return executed


async def node_route_and_execute_tools(state: AgentState) -> AgentState:
    import json
    from agent.core.llm import get_llm
    from agent.tools import TOOL_REGISTRY, TOOL_SCHEMAS

    llm = get_llm()
    system = _build_tool_system(state)
    messages = state["history"] + [{"role": "user", "content": state["message"]}]

    # Round 1: query/anomaly/forecast/schema tools
    result = await llm.generate_with_tools(system, messages, TOOL_SCHEMAS)
    executed = await _execute_calls(result.get("tool_calls", []), TOOL_REGISTRY)

    # Round 2: if query_database returned rows and no chart yet, offer a charting opportunity
    query_result = next(
        (tc for tc in executed if tc["name"] == "query_database" and tc.get("output", {}).get("success")),
        None
    )
    already_charted = any(tc["name"] == "generate_chart" for tc in executed)

    if query_result and not already_charted:
        rows = query_result["output"].get("rows", [])
        cols = query_result["output"].get("columns", [])
        if len(rows) >= 2 and len(cols) >= 2:
            # Give LLM the query results and ask it to chart if appropriate
            chart_context = (
                f"Query returned {len(rows)} rows with columns: {cols}.\n"
                f"Sample data (first 3 rows): {json.dumps(rows[:3])}\n\n"
                "If a chart would make this data clearer, call generate_chart now. "
                "Pass the full rows as the 'data' parameter (JSON array string). "
                "Choose x_column and y_column from the available columns. "
                "If no chart adds value, do not call any tool."
            )
            chart_messages = messages + [{"role": "user", "content": chart_context}]
            chart_result = await llm.generate_with_tools(system, chart_messages, TOOL_SCHEMAS)
            chart_calls = [c for c in chart_result.get("tool_calls", []) if c["name"] == "generate_chart"]
            if chart_calls:
                # Always override with the authoritative full rows from query_database
                # — never trust the LLM's data string (it may be truncated or malformed)
                for call in chart_calls:
                    call["input"]["data"] = json.dumps(rows)
                chart_executed = await _execute_calls(chart_calls, TOOL_REGISTRY)
                executed.extend(chart_executed)

    tool_context = "\n".join(
        f"Tool '{tc['name']}' result: {tc['output']}" for tc in executed
    ) if executed else ""

    return {**state, "tool_calls": executed, "tool_context": tool_context}


async def node_generate_reply(state: AgentState) -> AgentState:
    import re
    from agent.core.llm import get_llm
    from agent.prompts.system import build_system_prompt

    system = build_system_prompt(state)
    messages = list(state["history"])

    user_content = state["message"]
    if state.get("tool_context"):
        user_content += (
            f"\n\n[Tools have already been executed. Results:\n{state['tool_context']}]\n\n"
            "Write your response based on these results. Do NOT call any tools or output code blocks — "
            "the tools have already run. Just present the findings clearly."
        )
    messages.append({"role": "user", "content": user_content})

    raw = await get_llm().generate(
        system=system,
        messages=messages,
        tier="flash"
    )

    # Strip any tool call code blocks or image placeholders the model may emit
    raw = re.sub(r"<tool_code>.*?</tool_code>", "", raw, flags=re.DOTALL)
    raw = re.sub(r"```tool_code.*?```", "", raw, flags=re.DOTALL)
    raw = re.sub(r"```python.*?```", "", raw, flags=re.DOTALL)
    raw = re.sub(r"\[?<image:?[^>]*>\]?", "", raw)              # Gemini image placeholders
    raw = re.sub(r"<img\b[^>]*>", "", raw)                      # stray HTML img tags
    raw = re.sub(r"<figure\b[^>]*>.*?</figure>", "", raw, flags=re.DOTALL)  # figure blocks
    raw = re.sub(r"<figcaption\b[^>]*>.*?</figcaption>", "", raw, flags=re.DOTALL)
    # Strip stray print(generate_chart(...)) or similar calls in text
    raw = re.sub(
        r"\bprint\s*\(\s*(generate_chart|query_database|detect_anomalies|forecast_metric)\s*\(.*?\)\s*\)",
        "", raw, flags=re.DOTALL
    )

    proactive = None
    if "<proactive>" in raw:
        match = re.search(r"<proactive>(.*?)</proactive>", raw, re.DOTALL)
        if match:
            proactive = match.group(1).strip()
            raw = re.sub(r"<proactive>.*?</proactive>", "", raw, flags=re.DOTALL).strip()

    return {**state, "final_response": raw.strip(), "proactive": proactive}


async def node_save_session(state: AgentState) -> AgentState:
    import asyncio
    from agent.core.session import SessionManager
    from agent.core.memory import extract_and_store

    updated_history = state["history"] + [
        {"role": "user", "content": state["message"]},
        {"role": "assistant", "content": state["final_response"]},
    ]

    session = {
        "history": updated_history,
        "style": state["style"],
        "turn_count": state["turn_count"] + 1,
    }

    await SessionManager(state["user_id"]).save(session)

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
- Visual requests → ALWAYS use generate_chart tool (NEVER write Mermaid or ASCII diagrams)
- Route/driver/warehouse comparisons → query_database THEN generate_chart (bar chart)
- Time-series data → query_database THEN generate_chart (line chart)
- "unusual/anomaly/pattern" → detect_anomalies
- "forecast/predict/next" → forecast_metric
- "show SQL/explain" → explain_query
- "what tables/columns" → get_schema_info

IMPORTANT: Never output diagram markup (Mermaid, ASCII art). All visualisations go through generate_chart.
"""


def build_pipeline():
    graph = StateGraph(AgentState)

    graph.add_node("load_session", node_load_session)
    graph.add_node("inject_memory", node_inject_memory)
    graph.add_node("detect_style", node_detect_style)
    graph.add_node("inner_monologue", node_inner_monologue)
    graph.add_node("execute_tools", node_route_and_execute_tools)
    graph.add_node("generate_reply", node_generate_reply)
    graph.add_node("save_session", node_save_session)

    graph.set_entry_point("load_session")
    graph.add_edge("load_session", "inject_memory")
    graph.add_edge("inject_memory", "detect_style")
    graph.add_edge("detect_style", "inner_monologue")
    graph.add_edge("inner_monologue", "execute_tools")
    graph.add_edge("execute_tools", "generate_reply")
    graph.add_edge("generate_reply", "save_session")
    graph.add_edge("save_session", END)

    return graph.compile()
