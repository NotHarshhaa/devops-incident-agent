"""Agent orchestration graph.

Wires the investigation steps together:

    plan -> memory -> collect -> reason -> [low confidence? -> collect -> reason] -> report

Uses **LangGraph** when it is installed, and transparently falls back to a
dependency-free sequential runner otherwise. Both paths execute the exact
same node functions and produce an identical :class:`Report`.
"""

from __future__ import annotations

from datetime import timezone

from ..collectors import build_collectors
from ..config import Settings, get_settings
from ..llm import build_llm
from ..models import Evidence, Incident, Report
from ..store import get_store
from .memory import find_similar_incidents
from .planner import make_plan
from .reasoning import reason_root_cause
from .state import AgentState

#: Below this confidence, the graph re-runs collection once before
#: finalizing, hoping additional evidence sharpens the conclusion.
LOW_CONFIDENCE_THRESHOLD = 0.5

#: Safety cap — never re-collect more than once per investigation.
MAX_RECOLLECTIONS = 1


def _fmt_ts(dt) -> str:
    return dt.astimezone(timezone.utc).strftime("%H:%M:%S")


# --------------------------------------------------------------------- #
# Node functions (shared by both runners)
# --------------------------------------------------------------------- #
def plan_node(state: AgentState, settings: Settings) -> AgentState:
    incident: Incident = state["incident"]
    plan = make_plan(incident, settings)
    timeline = state.get("timeline", [])
    timeline.append(f"{_fmt_ts(incident.created_at)} 🚨 Alert received: {incident.title}")
    return {**state, "plan": plan, "timeline": timeline}


def memory_node(state: AgentState, settings: Settings) -> AgentState:
    incident: Incident = state["incident"]
    timeline = state.get("timeline", [])
    try:
        similar = find_similar_incidents(incident, get_store())
    except Exception:  # noqa: BLE001 - memory lookup never blocks an investigation
        similar = []
    if similar:
        top = similar[0]
        timeline.append(
            f"→ memory: found {len(similar)} similar past incident(s); "
            f"closest match {round(top.similarity * 100)}% — \"{top.incident_title}\""
        )
    else:
        timeline.append("→ memory: no similar past incidents found")
    return {**state, "similar_incidents": similar, "timeline": timeline}


def collect_node(state: AgentState, settings: Settings) -> AgentState:
    incident: Incident = state["incident"]
    evidence: list[Evidence] = list(state.get("evidence", []))
    timeline = state.get("timeline", [])
    recollecting = bool(evidence)
    for collector in build_collectors(settings):
        items = collector.collect(incident)
        evidence.extend(items)
        anomalies = sum(1 for e in items if e.anomalous)
        prefix = "→ (re-collect) " if recollecting else "→ "
        timeline.append(
            f"{prefix}{collector.name}: {len(items)} findings, {anomalies} anomalous"
        )
    return {**state, "evidence": evidence, "timeline": timeline}


def reason_node(state: AgentState, settings: Settings) -> AgentState:
    incident: Incident = state["incident"]
    evidence = state.get("evidence", [])
    llm = build_llm(settings)
    root_cause = reason_root_cause(incident, evidence, llm=llm, settings=settings)
    timeline = state.get("timeline", [])
    timeline.append(
        f"→ reasoning ({llm.name}): {root_cause.summary} "
        f"[{round(root_cause.confidence * 100)}% confidence]"
    )
    timeline.append(
        f"→ recommendation: {root_cause.recommended_action.value}"
    )
    return {**state, "root_cause": root_cause, "provider": llm.name, "timeline": timeline}


def _needs_recollection(state: AgentState) -> bool:
    root_cause = state.get("root_cause")
    if root_cause is None:
        return False
    already_recollected = state.get("recollect_count", 0) >= MAX_RECOLLECTIONS
    return root_cause.confidence < LOW_CONFIDENCE_THRESHOLD and not already_recollected


def recollect_node(state: AgentState, settings: Settings) -> AgentState:
    """Bump the retry counter and note why we're gathering more evidence."""
    timeline = state.get("timeline", [])
    root_cause = state["root_cause"]
    timeline.append(
        f"→ confidence {round(root_cause.confidence * 100)}% below "
        f"{round(LOW_CONFIDENCE_THRESHOLD * 100)}% threshold — re-collecting evidence"
    )
    return {**state, "recollect_count": state.get("recollect_count", 0) + 1, "timeline": timeline}


# --------------------------------------------------------------------- #
# Runners
# --------------------------------------------------------------------- #
def _run_with_langgraph(initial: AgentState, settings: Settings) -> AgentState:
    from langgraph.graph import END, START, StateGraph

    graph = StateGraph(AgentState)
    graph.add_node("plan", lambda s: plan_node(s, settings))
    graph.add_node("memory", lambda s: memory_node(s, settings))
    graph.add_node("collect", lambda s: collect_node(s, settings))
    graph.add_node("reason", lambda s: reason_node(s, settings))
    graph.add_node("recollect", lambda s: recollect_node(s, settings))

    graph.add_edge(START, "plan")
    graph.add_edge("plan", "memory")
    graph.add_edge("memory", "collect")
    graph.add_edge("collect", "reason")
    graph.add_conditional_edges(
        "reason",
        lambda s: "recollect" if _needs_recollection(s) else "done",
        {"recollect": "recollect", "done": END},
    )
    graph.add_edge("recollect", "collect")

    compiled = graph.compile()
    return compiled.invoke(initial)


def _run_sequential(initial: AgentState, settings: Settings) -> AgentState:
    state = plan_node(initial, settings)
    state = memory_node(state, settings)
    state = collect_node(state, settings)
    state = reason_node(state, settings)
    if _needs_recollection(state):
        state = recollect_node(state, settings)
        state = collect_node(state, settings)
        state = reason_node(state, settings)
    return state


def run_investigation(
    incident: Incident,
    settings: Settings | None = None,
    use_langgraph: bool = True,
) -> Report:
    """Run the full investigation pipeline and return a :class:`Report`."""
    settings = settings or get_settings()
    initial: AgentState = {"incident": incident, "timeline": []}

    ran_with = "sequential"
    if use_langgraph:
        try:
            state = _run_with_langgraph(initial, settings)
            ran_with = "langgraph"
        except Exception:  # noqa: BLE001 - fall back if langgraph unavailable
            state = _run_sequential(initial, settings)
    else:
        state = _run_sequential(initial, settings)

    timeline = state.get("timeline", [])
    timeline.append(f"(orchestrator: {ran_with})")

    return Report(
        incident=incident,
        evidence=state.get("evidence", []),
        root_cause=state["root_cause"],
        similar_incidents=state.get("similar_incidents", []),
        timeline=timeline,
        provider=state.get("provider", "mock"),
    )
