"""Assistant: a dispatcher plus a router.
The router (rules now, a language model later) only CHOOSES a tool and its
arguments. Our code RUNS the tool. Nothing here executes model-written code."""
from __future__ import annotations

import analytics
import streamlit as st
from google import genai
from google.genai import types
from analytics import ToolResult

# The ONLY things the assistant may do. Add your own tools here.
TOOLS = {
    'get_total': {
        'fn': analytics.get_total,
        'params': {'value_col', 'filters'},
        'description': 'Sum a numeric column, optionally filtered.',
    },
    'group_total': {
        'fn': analytics.group_total,
        'params': {'value_col', 'group_col', 'filters'},
        'description': 'Sum a numeric column by group (store, channel, year, ...).',
    },
    'revenue_growth_by_channel': {
    'fn': analytics.revenue_growth_by_channel,
    'params': set(),
    'description': (
        'Compare percentage revenue growth across sales channels '
        'between the first and last available years.'
    ),
},
    'data_quality_report': {
        'fn': analytics.data_quality_report,
        'params': set(),
        'description': 'Report duplicates and missing values in the loaded data.',
    },
    'get_average_satisfaction': {
        'fn': analytics.get_average_satisfaction,
        'params': set(),
        'description': (
            'Calculate average customer satisfaction overall '
            'and by geographic region using survey data.'
        ),
    },
}

UNSUPPORTED = ('I can only answer questions that my approved analytical functions can '
               'calculate from the loaded data: ' + ', '.join(TOOLS) + '. '
               'I cannot answer that one.')

# For when you add a language model: keep these  in the system prompt.
SYSTEM_PROMPT = """You are an analytical assistant for E-Presso managers.

:
- Only state numbers that appear in a tool result. Never estimate or recall figures.
- Always call a tool before making a numerical claim.
- State the scope (which period and data) of every answer.
- Separate Findings (from tool results), Interpretation, and Next steps.
- Revenue is not profit. Association is not causation.
- If the data cannot support a conclusion, say so and name the missing information.
- Never ask for, run, or write code. Never modify data.

Tool selection:
- For questions about  revenue,  sales, or revenue by sales channel, use get_ or group_ as appropriate.
- For questions asking to compare revenue between sales channels, use group_ with StoreType as the group column.
- Use revenue_growth_by_channel ONLY when the question explicitly asks about revenue growth, percentage growth, or change over time by sales channel.
- Never use revenue_growth_by_channel to answer a question asking which channel generated the highest  revenue.
- For missing values, duplicate rows, or data quality, use data_quality_report.
- For questions about average customer satisfaction, satisfaction by region, or customer experience, use get_average_satisfaction. Never use data_quality_report for these questions.
- For revenue by year, use group_total with Year as the group column.
"""


def run_tool(name: str, args: dict, df, log: list, survey_df=None) -> ToolResult:
    """The dispatcher: validate the request, run the function, log the call."""
    if name not in TOOLS:
        result = analytics._error(name, f'Unknown tool: {name}')
    else:
        unexpected = set(args) - TOOLS[name]['params']
        if unexpected:
            result = analytics._error(name, f'Unexpected argument(s): {sorted(unexpected)}')
        else:
            data = survey_df if name == 'get_average_satisfaction' else df

            if data is None:
                result = analytics._error(
                    name,
                    'Survey data is not available.'
                )
            else:
                result = TOOLS[name]['fn'](data, **args)

    log.append({'tool': name, 'arguments': args, 'result': result.to_dict()})
    return result
    
def rules_router(question: str, df):
    """Choose an approved analytical tool based on the question."""
    q = question.lower()
    filters = {}
       
    if any(w in q for w in (
        'satisfaction', 'satisfied', 'customer experience'
    )):
        
        return 'get_average_satisfaction', {}
    words = [word.strip('.,?!') for word in q.split()]

    if 'Location' in df.columns:
        for location in df['Location'].dropna().unique():
            if str(location).lower() in words:
                filters['Location'] = location

    if 'Year' in df.columns:
        for year in df['Year'].dropna().unique():
            if str(int(year)) in words:
                filters['Year'] = int(year)

    if filters:
        return 'get_total', {
            'value_col': 'Revenue',
            'filters': filters
        }

    if any(w in q for w in ('growth', 'grew', 'increased', 'increase')) and any(
        w in q for w in ('channel', 'store type', 'storetype')
    ):
        return 'revenue_growth_by_channel', {}

    if any(w in q for w in ('missing', 'duplicate', 'quality', 'blank')):
        return 'data_quality_report', {}

    if any(w in q for w in ('by year', 'per year', 'annual', 'yearly')):
        return 'group_total', {
            'value_col': 'Revenue',
            'group_col': 'Year',
            'filters': {}
        }

    if any(w in q for w in (
        'store type', 'by store type', 'per store type',
        'sales channel', 'by channel', 'per channel', 'channel'
    )):
        return 'group_total', {
            'value_col': 'Revenue',
            'group_col': 'StoreType',
            'filters': {}
        }

    if any(w in q for w in ('category', 'categories', 'by product category')):
        return 'group_total', {
            'value_col': 'Revenue',
            'group_col': 'Category',
            'filters': {}
        }

    if any(w in q for w in ('revenue', 'sales', 'total', 'sum')):
        return 'get_total', {
            'value_col': 'Revenue',
            'filters': {}
        }

    return None
def llm_router(question: str, df):
    """Ask  to select one approved analytical tool."""
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        client = genai.Client(api_key=api_key)

        numeric_columns = df.select_dtypes(include="number").columns.tolist()
        all_columns = df.columns.tolist()

        declarations = [
            types.FunctionDeclaration(
                name="get_total",
                description="Calculate the sum of a numeric column.",
                parameters_json_schema={
                    "type": "object",
                    "properties": {
                        "value_col": {
                            "type": "string",
                            "enum": numeric_columns,
                        }
                    },
                    "required": ["value_col"],
                },
            ),
            types.FunctionDeclaration(
                name="group_total",
                description="Calculate a numeric total grouped by another column.",
                parameters_json_schema={
                    "type": "object",
                    "properties": {
                        "value_col": {
                            "type": "string",
                            "enum": numeric_columns,
                        },
                        "group_col": {
                            "type": "string",
                            "enum": all_columns,
                        },
                    },
                    "required": ["value_col", "group_col"],
                },
            ),
            types.FunctionDeclaration(
                name="revenue_growth_by_channel",
                description="Compare revenue growth across sales channels.",
                parameters_json_schema={"type": "object"},
            ),
            types.FunctionDeclaration(
                name="data_quality_report",
                description="Report missing values and duplicate rows.",
                parameters_json_schema={"type": "object"},
            ),
        ]

        tool = types.Tool(function_declarations=declarations)

        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=question,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=[tool],
                tool_config=types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode="ANY"
                    )
                ),
            ),
        )

        if not response.function_calls:
            return None

        call = response.function_calls[0]

        if call.name not in TOOLS:
            return None

        return call.name, dict(call.args or {})

    except Exception as e:
        st.session_state["gemini_error"] = str(e)
        return None



def format_findings(result: ToolResult) -> str:
    if result.error:
        return f'The request could not be completed: {result.error}'

    if result.tool == 'revenue_growth_by_channel':
        value = result.value
        lines = [
            f"Revenue growth by sales channel "
            f"({value['first_year']}–{value['last_year']}):"
        ]

        for channel, data in value['channels'].items():
            growth = data['growth_percentage']

            if growth is None:
                growth_text = "could not be calculated"
            else:
                growth_text = f"{growth:+.2f}%"

            lines.append(
                f"{channel}: "
                f"${data['starting_revenue']:,.0f} to "
                f"${data['ending_revenue']:,.0f} "
                f"({growth_text})"
            )

        return "\n".join(lines) + f"\nRows used: {result.rows_used}"

    return (
        f'{result.definition}: {result.value} '
        f'(rows used: {result.rows_used})'
    )



def answer_question(question: str, df, mode: str = 'rules', survey_df=None) -> dict:
    log: list = []
    if mode == 'rules':
        routed = rules_router(question, df)
    else:
        routed = llm_router(question, df)
    if routed is None:
        return {'scope': 'n/a', 'findings': UNSUPPORTED, 'interpretation': '',
                'next_steps': '', 'tool_log': log}
    name, args = routed
    result = run_tool(name, args, df, log, survey_df)
    interpretation = ' '.join(result.caveats)

    if result.tool == 'revenue_growth_by_channel' and not result.error:
        channels = result.value['channels']

        valid_channels = {
            channel: data['growth_percentage']
            for channel, data in channels.items()
            if data['growth_percentage'] is not None
        }

        if valid_channels:
            best_channel = max(
                valid_channels,
                key=valid_channels.get
            )

            interpretation = (
                f"{best_channel} experienced the greatest percentage "
                f"revenue growth. This comparison uses the first and "
                f"last available years ({result.value['first_year']} "
                f"and {result.value['last_year']}) and the full loaded "
                f"dataset. It does not establish why revenue changed. "
                f"The calculation also does not verify whether both "
                f"years cover equally complete periods. "
                f"{interpretation}"
            )
    return {
        'scope': (
            f"Full loaded dataset (independent of dashboard filters). "
            f"{result.scope}"
        ),
        'findings': format_findings(result),
        'interpretation': interpretation,
        'next_steps': '',
        'tool_log': log,
    }
