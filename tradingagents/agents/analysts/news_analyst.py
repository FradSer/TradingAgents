from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_global_news,
    get_language_instruction,
    get_news,
)
from tradingagents.dataflows.config import get_config


def create_news_analyst(llm):
    def news_analyst_node(state):
        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        tools = [
            get_news,
            get_global_news,
        ]

        system_message = (
            "You are a news researcher tasked with analyzing recent news and trends over the past week. "
            "Please write a comprehensive report of the current state of the world that is relevant for trading and macroeconomics. "
            "Use the available tools: get_news(query, start_date, end_date) for company-specific or targeted news searches, "
            "and get_global_news(curr_date, look_back_days, limit) for broader macroeconomic news. "
            "Provide specific, actionable insights with supporting evidence to help traders make informed decisions.\n\n"
            "## Tool usage rules — read before calling tools\n"
            "1. `get_news` is backed by yfinance, which only exposes the latest ~20 articles for a ticker (roughly the last 7 days). "
            "It does NOT support historical lookups. Make ONE call with a window ending on the current date "
            "(e.g. `start_date = current_date - 7 days, end_date = current_date`). Do not fan out multiple parallel calls "
            "scanning earlier weeks — those windows will return `WINDOW_MISS` by construction.\n"
            "2. Tool returns are prefixed: a normal results block starts with `## <TICKER> News, ...`; "
            "failure modes are `NO_DATA: ...` (source returned nothing), `WINDOW_MISS: ...` (results exist but outside your window), "
            "`NO_DATES: ...` (results lack pub_date), or `ERROR: ...`.\n"
            "3. **Hallucination ban.** If every news tool call returns `NO_DATA`, `WINDOW_MISS`, `NO_DATES`, or `ERROR`, "
            "you MUST NOT invent article titles, publishers, links, dates, or specific events. The report must instead include "
            "a clearly marked section `**[News data unavailable]**` explaining which tools were called, what they returned, "
            "and what general macro context you can still provide from `get_global_news`. Speculation about company-specific "
            "events you have no tool evidence for is forbidden."
            + """ Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."""
            + get_language_instruction()
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. {instrument_context}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(instrument_context=instrument_context)

        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke(state["messages"])

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "news_report": report,
        }

    return news_analyst_node
