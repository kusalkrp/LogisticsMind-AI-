MEMORY_EXTRACTION_PROMPT = """
Analyse this analytics conversation and extract memory.
Return ONLY valid JSON — no markdown fences, no preamble:

{
  "facts": [
    "Analyst is focused on route performance analysis",
    "Analyst prefers chart visualisations over tables",
    "Analyst is investigating Jaffna route delays"
  ],
  "session_summary": "Analyst investigated route on-time performance. Found RT-COL-JAF-003 has 58% on-time rate vs 89% average. Identified three root causes: monsoon weather, vehicle VH-0089, and WH-COL-02 loading delays.",
  "topics": ["route performance", "RT-COL-JAF-003", "delays", "Jaffna"]
}

Rules:
- facts: short present-tense statements about the analyst's focus and preferences. Max 10.
- Only extract what is clearly evidenced. Never infer or fabricate.
- session_summary: 2-3 sentences. What was investigated. What was found.
- topics: 3-6 keywords for this session.
"""
