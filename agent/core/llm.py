"""Gemini LLM client with two-tier model support."""
import os
import google.generativeai as genai

MODEL = "gemini-2.5-flash"


class GeminiClient:
    def __init__(self):
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])

    async def generate(
        self,
        system: str,
        messages: list[dict],
        tier: str = "flash",  # noqa: ARG002 — kept for API compatibility
    ) -> str:
        model_name = MODEL
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system
        )
        gemini_messages = [
            {"role": "model" if m["role"] == "assistant" else "user",
             "parts": [m["content"]]}
            for m in messages
            if m.get("content")
        ]
        if not gemini_messages:
            gemini_messages = [{"role": "user", "parts": ["Hello"]}]

        response = await model.generate_content_async(gemini_messages)
        try:
            return response.text
        except Exception:
            # Response blocked or empty (finish_reason != STOP)
            return ""

    async def generate_with_tools(
        self,
        system: str,
        messages: list[dict],
        tools: list[dict],
    ) -> dict:
        """Generate with function calling. Returns {text, tool_calls}."""
        model = genai.GenerativeModel(
            model_name=MODEL,
            system_instruction=system,
            tools=self._convert_tools(tools)
        )
        gemini_messages = [
            {"role": "model" if m["role"] == "assistant" else "user",
             "parts": [m["content"]]}
            for m in messages
            if m.get("content")
        ]
        if not gemini_messages:
            gemini_messages = [{"role": "user", "parts": ["Hello"]}]

        response = await model.generate_content_async(gemini_messages)

        tool_calls = []
        text = ""

        for part in response.candidates[0].content.parts:
            if hasattr(part, "function_call") and part.function_call.name:
                tool_calls.append({
                    "name": part.function_call.name,
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


_client = None


def get_llm() -> GeminiClient:
    global _client
    if _client is None:
        _client = GeminiClient()
    return _client
