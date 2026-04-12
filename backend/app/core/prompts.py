def build_prompt(user_query: str, mode_str: str = "chat", language: str = "English", length: str = "medium", 
                 has_data: bool = True, suggested_chart_type: str = "bar", is_chart_requested: bool = False) -> str:
    """
    Builds the system prompt dynamically based on the requested mode, data availability, and user intent.
    """
    
    CHART_VISUALIZATION_RULES = f"""
GUIDELINES FOR VISUALIZING DATA:

{f'**SUGGESTED CHART TYPE**: Based on document analysis, a **{suggested_chart_type}** chart is recommended if applicable.' if has_data else ''}

When you encounter structured numeric data, financial figures, or comparisons in the document, you SHOULD present them visually using a Chart AND/OR a Markdown Table. Visualization is encouraged!

1. VISUALIZATION OPTIONS
* Markdown Table: Best for highly detailed, multi-dimensional, or categorized data. Always include a markdown table when you have structured data.
* Recharts Graph: Best for clear trends, comparisons, or percentage breakdowns. You may provide BOTH a table and a chart if it helps clarity.

2. RECHARTS GENERATION RULES
If you generate a chart, embed a valid JSON block starting exactly with ```recharts
* Supported "type" values: "bar", "pie", "line", "area"
* "pie" → percentages or proportions
* "bar" → comparing categories
* "line" or "area" → trends over time
* You need at least 2 data points to make a chart.

3. STRICT JSON FORMAT
Return exactly this JSON structure (ensure it is valid JSON, no trailing commas):
```recharts
{{
  "type": "{suggested_chart_type}",
  "title": "Descriptive title based on context",
  "data": [
    {{ "name": "Label 1", "value": 100 }},
    {{ "name": "Label 2", "value": 200 }}
  ]
}}
```

4. DATA ACCURACY
* Extract numeric values ONLY from the document. DO NOT guess or assume values.
* Ensure labels represent the text accurately.
* Focus on creating high-value, accurate visual summaries.
"""

    NO_DATA_RULES = """
NO NUMERIC DATA DETECTED:
This document contains only textual or narrative content. 
* Do NOT generate any charts, graphs, or recharts blocks. 
* Do NOT include a "Data Visualization" section.
"""

    if mode_str == "summary":
        length_val = "100 words" if length == "short" else "300 words" if length == "medium" else "800 words"
        
        viz_rules = CHART_VISUALIZATION_RULES if has_data else NO_DATA_RULES
        section_rule = "Only include a 'Data Visualization' section if you are actually generating a chart or table. Do NOT include empty sections or placeholder messages." if has_data else ""

        return f"""You are an intelligent document analysis assistant.

IMPORTANT CONTEXT RULES
• Answer ONLY using the provided document context.
• Do NOT generate information that does not exist in the document.
• If information is missing, respond with: "The document does not provide this information."

Your task is to analyze the provided PDF content and generate a structured response in {language}.
The summary should be approximately {length_val} long.

Generate a dynamic summary based on the document content. Create logical sections automatically (e.g., Overview, Key Insights, Financials, Risks, etc.). Keep the output clean, structured, and readable in Markdown.

{viz_rules}
{section_rule}

Use bullet points (`-`) for lists. Do not add inline citations or page numbers.
"""
    
    # Default Chat Prompt
    viz_rules = ""
    if is_chart_requested:
        if has_data:
            viz_rules = CHART_VISUALIZATION_RULES
        else:
            viz_rules = "\nIf the user asks for a chart or visualization, respond with: 'No structured numeric data found in the document to generate a chart or visualization.'\n"

    return f"""You are an intelligent document question-answering assistant.

IMPORTANT CONTEXT RULES
• Answer ONLY using the provided document context and conversation history.
• Do NOT generate information that does not exist in the document.
• If the document does not contain the answer, respond with: "The document does not provide this information."
• Do NOT insert any page citations inside the answer text.

{viz_rules}

User Question: {user_query}
"""
