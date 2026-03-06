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


async def node_route_and_execute_tools(state: AgentState) -> AgentState:
    from agent.core.llm import get_llm
    from agent.tools import TOOL_REGISTRY, TOOL_SCHEMAS

    llm = get_llm()
    system = _build_tool_system(state)
    messages = state["history"] + [{"role": "user", "content": state["message"]}]

    result = await llm.generate_with_tools(system, messages, TOOL_SCHEMAS)
    tool_calls = result.get("tool_calls", [])

    executed = []
    for call in tool_calls:
        fn = TOOL_REGISTRY.get(call["name"])
        if fn:
            try:
                output = await fn(**call["input"])
                executed.append({
                    "name": call["name"],
                    "input": call["input"],
                    "output": output,
                    "status": "success"
                })
            except Exception as e:
                executed.append({
                    "name": call["name"],
                    "input": call["input"],
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

    system = build_system_prompt(state)
    messages = list(state["history"])

    user_content = state["message"]
    if state.get("tool_context"):
        user_content += f"\n\n[Tool results available:\n{state['tool_context']}]"
    messages.append({"role": "user", "content": user_content})

    raw = await get_llm().generate(
        system=system,
        messages=messages,
        tier="pro"
    )

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
- Visual requests → generate_chart (after querying data)
- "unusual/anomaly/pattern" → detect_anomalies
- "forecast/predict/next" → forecast_metric
- "show SQL/explain" → explain_query
- "what tables/columns" → get_schema_info
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
