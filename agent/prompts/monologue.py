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
