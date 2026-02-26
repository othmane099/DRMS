import json
import logging
import re
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph

from config import settings

logger = logging.getLogger(__name__)

SCORE_THRESHOLD = 7


class SearchState(TypedDict):
    user_message: str
    db_schema: str
    current_user_id: str | None  # None = search all, str = filter to this user
    generated_sql: str
    score: int
    feedback: str
    iterations: int
    rows: list[dict[str, Any]]
    message: str


def _get_llm() -> ChatOllama:
    return ChatOllama(base_url=settings.OLLAMA_HOST, model=settings.OLLAMA_MODEL)


def _extract_sql(content: str) -> str:
    match = re.search(r"```(?:sql)?\s*([\s\S]*?)```", content, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    select_match = re.search(r"(SELECT\b[\s\S]+)", content, re.IGNORECASE)
    if select_match:
        return select_match.group(1).strip()
    return content.strip()


def _parse_review(content: str) -> tuple[int, str]:
    try:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            data = json.loads(match.group())
            return int(data.get("score", 0)), str(data.get("feedback", ""))
    except (json.JSONDecodeError, ValueError, KeyError):
        pass
    return 0, "Failed to parse review"


async def sql_agent_node(state: SearchState) -> dict[str, Any]:
    feedback_section = (
        f"\nPrevious SQL: {state['generated_sql']}\nFeedback: {state['feedback']}"
        if state["generated_sql"]
        else ""
    )
    scope_section = (
        f"\nScope (MANDATORY): Only include documents where "
        f"d.assigned_to = '{state['current_user_id']}'::uuid "
        f"OR d.created_by = '{state['current_user_id']}'::uuid"
        if state["current_user_id"]
        else ""
    )
    system_prompt = (
        f"You are a PostgreSQL expert. Convert the user's request into a valid SELECT query.\n\n"
        f"{state['db_schema']}\n\n"
        f"Rules:\n{settings.OLLAMA_SQL_AGENT_RULES}{scope_section}"
    )
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(
            content=f"User request: {state['user_message']}{feedback_section}"
        ),
    ]
    response = await _get_llm().ainvoke(messages)
    sql = _extract_sql(str(response.content))
    logger.debug("sql_agent generated: %s", sql)
    return {"generated_sql": sql, "iterations": state["iterations"] + 1}


async def reviewer_node(state: SearchState) -> dict[str, Any]:
    messages = [
        SystemMessage(content=settings.OLLAMA_REVIEWER_SYSTEM_PROMPT),
        HumanMessage(
            content=f"User request: {state['user_message']}\n\nSQL:\n{state['generated_sql']}"
        ),
    ]
    response = await _get_llm().ainvoke(messages)
    score, feedback = _parse_review(str(response.content))
    logger.debug("reviewer score=%d feedback=%s", score, feedback)
    return {"score": score, "feedback": feedback}


async def formatter_node(state: SearchState) -> dict[str, Any]:
    rows = state["rows"]
    if not rows:
        return {"message": "No documents found matching your request."}

    rows_text = json.dumps(rows[:20], default=str, indent=2)
    messages = [
        SystemMessage(content=settings.OLLAMA_FORMATTER_SYSTEM_PROMPT),
        HumanMessage(
            content=f"User request: {state['user_message']}\n\nResults ({len(rows)} rows):\n{rows_text}"
        ),
    ]
    response = await _get_llm().ainvoke(messages)
    return {"message": str(response.content).strip()}


def _route(state: SearchState) -> str:
    if (
        state["score"] >= SCORE_THRESHOLD
        or state["iterations"] >= settings.OLLAMA_MAX_ITERATIONS
    ):
        return "done"
    return "sql_agent"


def _build_sql_graph() -> Any:
    graph: StateGraph = StateGraph(SearchState)
    graph.add_node("sql_agent", sql_agent_node)
    graph.add_node("reviewer", reviewer_node)

    graph.add_edge(START, "sql_agent")
    graph.add_edge("sql_agent", "reviewer")
    graph.add_conditional_edges(
        "reviewer",
        _route,
        {"done": END, "sql_agent": "sql_agent"},
    )

    return graph.compile()


async def generate_sql(
    message: str,
    db_schema: str,
    user_id: str | None = None,
) -> str:
    graph = _build_sql_graph()
    state: SearchState = {
        "user_message": message,
        "db_schema": db_schema,
        "current_user_id": user_id,
        "generated_sql": "",
        "score": 0,
        "feedback": "",
        "iterations": 0,
        "rows": [],
        "message": "",
    }
    final_state: SearchState = await graph.ainvoke(state)
    sql = final_state["generated_sql"].strip().rstrip(";")
    logger.info("SQL generated in %d iteration(s): %s", final_state["iterations"], sql)
    return sql


async def format_results(message: str, rows: list[dict[str, Any]]) -> str:
    state: SearchState = {
        "user_message": message,
        "db_schema": "",
        "current_user_id": None,
        "generated_sql": "",
        "score": 0,
        "feedback": "",
        "iterations": 0,
        "rows": rows,
        "message": "",
    }
    result = await formatter_node(state)
    return result["message"]
