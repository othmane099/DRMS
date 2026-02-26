import json
import logging
import re
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph

from config import settings
from core.documents.schemas import DocumentSearchFilters

logger = logging.getLogger(__name__)

SCORE_THRESHOLD = 7

_FILTER_SYSTEM_PROMPT = (
    "You are a document search filter extractor.\n"
    "Convert the user's natural language query into a JSON object with these optional fields:\n"
    "{\n"
    '  "title_contains": "<string or null>",\n'
    '  "description_contains": "<string or null>",\n'
    '  "category": "<string or null>",\n'
    '  "subcategory": "<string or null>",\n'
    '  "stage": "<string or null>",\n'
    '  "assignee_name": "<string or null>",\n'
    '  "created_by_name": "<string or null>",\n'
    '  "tags": ["<string>", ...] or null,\n'
    '  "created_after": "<YYYY-MM-DD or null>",\n'
    '  "created_before": "<YYYY-MM-DD or null>",\n'
    '  "archived": <true/false/null>,\n'
    '  "limit": <integer 1-100, default 20>\n'
    "}\n\n"
    "Rules:\n"
    "- Output ONLY a valid JSON object, no explanation or markdown\n"
    "- Use null for fields not relevant to the query\n"
    "- For name/title searches, put the keyword in title_contains\n"
    "- For archived documents set archived to true; for active documents set to false; "
    "if not specified leave null\n"
    "- Keep limit at 20 unless the user specifies a different number"
)

_FILTER_REVIEWER_PROMPT = (
    "You are a search filter reviewer. Given a user's natural language query and extracted "
    "JSON filters, evaluate whether the filters correctly and completely capture the user's intent.\n\n"
    "Score 0-10 (7+ is acceptable).\n"
    'Respond with ONLY valid JSON: {"score": <number>, "feedback": "<one sentence>"}'
)


class FilterState(TypedDict):
    user_message: str
    extracted_filters_json: str
    filters: DocumentSearchFilters | None
    score: int
    feedback: str
    iterations: int


def _get_llm() -> ChatOllama:
    return ChatOllama(base_url=settings.OLLAMA_HOST, model=settings.OLLAMA_MODEL)


def _parse_review(content: str) -> tuple[int, str]:
    try:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            data = json.loads(match.group())
            return int(data.get("score", 0)), str(data.get("feedback", ""))
    except (json.JSONDecodeError, ValueError, KeyError):
        pass
    return 0, "Failed to parse review"


async def extractor_node(state: FilterState) -> dict[str, Any]:
    feedback_section = (
        f"\nPrevious filters: {state['extracted_filters_json']}\nFeedback: {state['feedback']}"
        if state["extracted_filters_json"]
        else ""
    )
    messages = [
        SystemMessage(content=_FILTER_SYSTEM_PROMPT),
        HumanMessage(content=f"{state['user_message']}{feedback_section}"),
    ]
    response = await _get_llm().ainvoke(messages)
    content = str(response.content).strip()
    logger.debug(
        "extractor_node iteration=%d raw: %s", state["iterations"] + 1, content
    )

    try:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            raise ValueError("No JSON object found in response")
        data = json.loads(match.group())
        filters = DocumentSearchFilters.model_validate(data)
        logger.debug("extractor_node parsed: %s", filters)
        return {
            "extracted_filters_json": json.dumps(data),
            "filters": filters,
            "iterations": state["iterations"] + 1,
        }
    except Exception as exc:
        logger.debug("extractor_node parse error: %s", exc)
        return {
            "extracted_filters_json": "",
            "filters": None,
            "feedback": f"Parse/validation error: {exc}",
            "iterations": state["iterations"] + 1,
        }


async def reviewer_node(state: FilterState) -> dict[str, Any]:
    if not state["extracted_filters_json"]:
        return {"score": 0}

    messages = [
        SystemMessage(content=_FILTER_REVIEWER_PROMPT),
        HumanMessage(
            content=(
                f"User query: {state['user_message']}\n\n"
                f"Extracted filters:\n{state['extracted_filters_json']}"
            )
        ),
    ]
    response = await _get_llm().ainvoke(messages)
    score, feedback = _parse_review(str(response.content))
    logger.debug("reviewer_node score=%d feedback=%s", score, feedback)
    return {"score": score, "feedback": feedback}


def _route(state: FilterState) -> str:
    if (
        state["score"] >= SCORE_THRESHOLD
        or state["iterations"] >= settings.OLLAMA_MAX_ITERATIONS
    ):
        return "done"
    return "extractor"


def _build_filter_graph() -> Any:
    graph: StateGraph = StateGraph(FilterState)
    graph.add_node("extractor", extractor_node)
    graph.add_node("reviewer", reviewer_node)

    graph.add_edge(START, "extractor")
    graph.add_edge("extractor", "reviewer")
    graph.add_conditional_edges(
        "reviewer",
        _route,
        {"done": END, "extractor": "extractor"},
    )

    return graph.compile()


async def extract_filters(message: str) -> DocumentSearchFilters:
    graph = _build_filter_graph()
    state: FilterState = {
        "user_message": message,
        "extracted_filters_json": "",
        "filters": None,
        "score": 0,
        "feedback": "",
        "iterations": 0,
    }
    final_state: FilterState = await graph.ainvoke(state)

    if final_state["filters"] is not None:
        logger.info(
            "Filters extracted (score=%d) in %d iteration(s)",
            final_state["score"],
            final_state["iterations"],
        )
        return final_state["filters"]

    logger.warning(
        "Filter extraction failed for message=%r, returning empty filters", message
    )
    return DocumentSearchFilters()


async def format_results(message: str, rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No documents found matching your request."

    rows_text = json.dumps(rows[:20], default=str, indent=2)
    messages = [
        SystemMessage(content=settings.OLLAMA_FORMATTER_SYSTEM_PROMPT),
        HumanMessage(
            content=f"User request: {message}\n\nResults ({len(rows)} rows):\n{rows_text}"
        ),
    ]
    response = await _get_llm().ainvoke(messages)
    return str(response.content).strip()
