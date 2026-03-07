"""Chat endpoint — main conversation API."""
from fastapi import APIRouter
from api.models import ChatRequest, ChatResponse
from agent.agent import LogisticsMindAgent

router = APIRouter()
agent = LogisticsMindAgent()


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    response = await agent.chat(req.user_id, req.message)

    chart_json = None
    for tc in response.tools_used:
        if tc["name"] == "generate_chart" and tc.get("output", {}).get("success"):
            chart_json = tc["output"].get("chart_json")

    return ChatResponse(
        message=response.message,
        tools_used=response.tools_used,
        proactive=response.proactive,
        chart_json=chart_json,
        cached=response.cached,
    )
