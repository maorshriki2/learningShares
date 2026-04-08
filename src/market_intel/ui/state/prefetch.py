from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4
import threading

import streamlit as st

from market_intel.ui.clients.api_client import MarketIntelApiClient
from market_intel.ui.state.analysis_cache import set_cached
from market_intel.ui.state.session import resolve_symbol_for_api


@dataclass(frozen=True)
class PrefetchStep:
    id: str
    label: str
    run: callable


_SS_PREFETCH = "_mi_prefetch_state"
_SS_PREFETCH_JOB = "_mi_prefetch_job"

_PROGRESS_LOCK = threading.Lock()
_PROGRESS: dict[str, dict[str, Any]] = {}

# Keep job handles out of session_state so navigation/reruns cannot drop them.
_JOBS_LOCK = threading.Lock()
_JOBS: dict[str, Future] = {}


def _safe_call(fn, *, default: Any) -> Any:
    try:
        return fn()
    except Exception:
        return default


def _build_steps(client: MarketIntelApiClient, sym: str, config: dict[str, Any] | None) -> list[PrefetchStep]:
    # Stable order requested by user.
    cfg = config if isinstance(config, dict) else {}
    return [
        PrefetchStep(
            id="analysis_artifact",
            label="Analyze (Artifact v1)",
            run=lambda: _safe_call(
                lambda: client.analysis_artifact(
                    sym,
                    include_explain=True,
                    timeframe=str(cfg.get("timeframe") or "1d"),
                    limit=int(cfg.get("limit") or 320),
                    years=int(cfg.get("years") or 10),
                    gov_year=int(cfg.get("gov_year") or 2024),
                    gov_quarter=int(cfg.get("gov_quarter") or 4),
                    peers_extra=str(cfg.get("peers_extra") or ""),
                    mos_required=float(cfg.get("mos_required") or 0.15),
                    premium_threshold=float(cfg.get("premium_threshold") or 0.15),
                    wacc_span=float(cfg.get("wacc_span") or 0.02),
                    terminal_span=float(cfg.get("terminal_span") or 0.01),
                    grid_size=int(cfg.get("grid_size") or 5),
                ),
                default={},
            ),
        ),
    ]


@st.cache_resource(show_spinner=False)
def _prefetch_resources() -> dict[str, Any]:
    # One executor per Streamlit process. Keep small to avoid API overload.
    return {
        "executor": ThreadPoolExecutor(max_workers=2, thread_name_prefix="mi-prefetch"),
    }


def _register_job(job_id: str, future: Future) -> None:
    with _JOBS_LOCK:
        _JOBS[job_id] = future


def _get_job_future(job_id: str) -> Future | None:
    with _JOBS_LOCK:
        f = _JOBS.get(job_id)
        return f if isinstance(f, Future) else None


def _forget_job(job_id: str) -> None:
    with _JOBS_LOCK:
        _JOBS.pop(job_id, None)


def _set_progress(job_id: str, patch: dict[str, Any]) -> None:
    # Thread-safe, does not touch Streamlit APIs.
    with _PROGRESS_LOCK:
        prog = _PROGRESS.get(job_id) or {}
        prog.update(patch)
        _PROGRESS[job_id] = prog


def _get_progress(job_id: str) -> dict[str, Any]:
    with _PROGRESS_LOCK:
        prog = _PROGRESS.get(job_id)
        return dict(prog) if isinstance(prog, dict) else {}


def _store_step_result(job_id: str, step_id: str, result: Any) -> None:
    # Thread-safe, no Streamlit usage.
    with _PROGRESS_LOCK:
        prog = _PROGRESS.get(job_id) or {}
        res = prog.get("results")
        if not isinstance(res, dict):
            res = {}
            prog["results"] = res
        res[step_id] = result
        _PROGRESS[job_id] = prog


def _run_prefetch_job(
    *,
    job_id: str,
    sym: str,
    api_base: str,
    order: list[str],
    config: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Background job runner (no Streamlit calls here).
    Returns all step results + any error string.
    """
    total = len(order)
    _set_progress(
        job_id,
        {
            "active": True,
            "done_n": 0,
            "total_n": total,
            "current_label": "Initializing",
            "error": None,
        },
    )

    results: dict[str, Any] = {}
    done: list[str] = []

    client = MarketIntelApiClient(api_base, normalize_symbol=False)
    try:
        steps = {s.id: s for s in _build_steps(client, sym, config)}
        for i, step_id in enumerate(order):
            step = steps.get(step_id)
            if step is None:
                done.append(step_id)
                _set_progress(job_id, {"done_n": len(done), "current_label": "Skipping"})
                continue
            _set_progress(job_id, {"current_label": step.label})
            try:
                result = step.run()
            except Exception as exc:
                # Keep going; cache will store defaults/empties for this step.
                result = {}
                _set_progress(job_id, {"error": f"{type(exc).__name__}: {exc}"})
            results[step_id] = result
            _store_step_result(job_id, step_id, result)
            done.append(step_id)
            _set_progress(job_id, {"done_n": len(done)})

        _set_progress(job_id, {"active": False, "current_label": "Done"})
        return {"ok": True, "results": results, "done": done, "error": _get_progress(job_id).get("error")}
    finally:
        try:
            client.close()
        except Exception:
            pass


def start_prefetch(
    *, symbol_display: str, api_base: str, start_tab: str | None, config: dict[str, Any] | None = None
) -> None:
    """
    Start a background prefetch job.
    Fetches all steps in the background and stores results into the in-memory analysis cache
    once the job completes (collected on the next normal rerun).
    """
    sym = resolve_symbol_for_api(symbol_display)
    # Build stable order list (primitive only) without leaving clients open.
    tmp = MarketIntelApiClient(api_base)
    try:
        order = [s.id for s in _build_steps(tmp, sym, config)]
    finally:
        try:
            tmp.close()
        except Exception:
            pass
    if start_tab and start_tab in set(order):
        order = [start_tab] + [x for x in order if x != start_tab]

    job_id = uuid4().hex[:12]
    r = _prefetch_resources()
    executor: ThreadPoolExecutor = r["executor"]
    future: Future = executor.submit(
        _run_prefetch_job, job_id=job_id, sym=sym, api_base=api_base, order=order, config=config
    )
    _register_job(job_id, future)
    st.session_state[_SS_PREFETCH_JOB] = {
        "active": True,
        "job_id": job_id,
        "symbol": sym,
        "api_base": api_base,
        "order": order,
        "config": config,
        "started_ts": datetime.now().isoformat(timespec="seconds"),
    }
    # Keep legacy state for any older code paths (should be unused now).
    st.session_state[_SS_PREFETCH] = {
        "active": True,
        "symbol": sym,
        "api_base": api_base,
        "order": order,
        "idx": 0,
        "done": [],
        "started_ts": datetime.now().isoformat(timespec="seconds"),
    }


def _cache_result(step_id: str, sym: str, api_base: str, result: Any) -> None:
    if step_id == "analysis_artifact" and isinstance(result, dict):
        # New unified cache key (v1)
        set_cached(sym, api_base, "analysis_artifact:v1", result or {})
        # Also cache individual inputs for pages that want a direct payload without
        # depending on the entire artifact shape.
        try:
            inputs = result.get("inputs") if isinstance(result.get("inputs"), dict) else {}
            mc = inputs.get("market_context_feed") if isinstance(inputs, dict) else None
            if isinstance(mc, dict) and mc:
                set_cached(sym, api_base, "market_context_feed:v1", mc)
        except Exception:
            pass
        return


def collect_prefetch_if_ready() -> None:
    """
    Collect any available background prefetch results and write them to analysis_cache.
    Must be called from the main Streamlit thread (safe).
    """
    job = st.session_state.get(_SS_PREFETCH_JOB)
    if not isinstance(job, dict) or not job.get("active"):
        return

    sym = str(job.get("symbol") or "").strip().upper()
    api_base = str(job.get("api_base") or "").strip()
    order = job.get("order") if isinstance(job.get("order"), list) else []
    job_id = str(job.get("job_id") or "")
    future = _get_job_future(job_id) if job_id else None
    if not isinstance(future, Future):
        # Job handle lost (e.g. process restart). Mark inactive but keep any collected cache.
        job["active"] = False
        st.session_state[_SS_PREFETCH_JOB] = job
        return

    # Collect incremental results (no waiting).
    prog = _get_progress(job_id) if job_id else {}
    prog_results = prog.get("results") if isinstance(prog, dict) else None
    if isinstance(prog_results, dict) and sym and api_base:
        collected = job.get("collected")
        if not isinstance(collected, list):
            collected = []
        collected_set = set(str(x) for x in collected)
        for step_id in order:
            if step_id in collected_set:
                continue
            if step_id in prog_results:
                _cache_result(step_id, sym, api_base, prog_results.get(step_id))
                collected_set.add(step_id)
        job["collected"] = list(collected_set)
        st.session_state[_SS_PREFETCH_JOB] = job

    if not future.done():
        return

    try:
        payload = future.result(timeout=0)
    except Exception as exc:
        job["active"] = False
        st.session_state[_SS_PREFETCH_JOB] = job
        _set_progress(str(job.get("job_id") or ""), {"active": False, "error": f"{type(exc).__name__}: {exc}"})
        _forget_job(job_id)
        return

    results = payload.get("results") if isinstance(payload, dict) else None
    if isinstance(results, dict) and sym and api_base:
        for step_id in order:
            if step_id in results:
                _cache_result(step_id, sym, api_base, results.get(step_id))

    job["active"] = False
    st.session_state[_SS_PREFETCH_JOB] = job
    _forget_job(job_id)
    st.session_state["_mi_last_analysis_sync"] = {
        "symbol": sym,
        "api_base": api_base,
        "ts": datetime.now().isoformat(timespec="seconds"),
    }


def get_prefetch_status() -> dict[str, Any] | None:
    job = st.session_state.get(_SS_PREFETCH_JOB)
    if not isinstance(job, dict):
        return None
    job_id = str(job.get("job_id") or "")
    prog = _get_progress(job_id) if job_id else {}
    order = job.get("order") if isinstance(job.get("order"), list) else []
    total_n = int(prog.get("total_n") or len(order) or 0)
    return {
        "active": bool(job.get("active")),
        "job_id": job_id,
        "symbol": job.get("symbol"),
        "api_base": job.get("api_base"),
        "done_n": int(prog.get("done_n") or 0),
        "total_n": total_n,
        "current_label": prog.get("current_label") or None,
        "error": prog.get("error") or None,
        "started_ts": job.get("started_ts"),
    }


def prefetch_tick() -> dict[str, Any] | None:
    """
    Execute a single prefetch step if a prefetch is active.
    Returns the current state (for UI), or None if inactive.
    """
    state = st.session_state.get(_SS_PREFETCH)
    if not isinstance(state, dict) or not state.get("active"):
        return None

    sym = str(state.get("symbol") or "").strip().upper()
    api_base = str(state.get("api_base") or "").strip()
    order = state.get("order")
    idx = int(state.get("idx") or 0)
    done = state.get("done") if isinstance(state.get("done"), list) else []

    if not sym or not api_base or not isinstance(order, list):
        st.session_state.pop(_SS_PREFETCH, None)
        return None

    if idx >= len(order):
        # Finish
        state["active"] = False
        st.session_state[_SS_PREFETCH] = state
        st.session_state["_mi_last_analysis_sync"] = {
            "symbol": sym,
            "api_base": api_base,
            "ts": datetime.now().isoformat(timespec="seconds"),
        }
        return state

    step_id = str(order[idx])
    client = MarketIntelApiClient(api_base)
    try:
        steps = {s.id: s for s in _build_steps(client, sym)}
        step = steps.get(step_id)
        if step is None:
            state["idx"] = idx + 1
            st.session_state[_SS_PREFETCH] = state
            return state
        state["current"] = {"id": step.id, "label": step.label}
        result = step.run()
        _cache_result(step_id, sym, api_base, result)
        done.append(step_id)
        state["done"] = done
        state["idx"] = idx + 1
        state["current"] = None
        st.session_state[_SS_PREFETCH] = state
        return state
    finally:
        try:
            client.close()
        except Exception:
            pass


def get_prefetch_state() -> dict[str, Any] | None:
    state = st.session_state.get(_SS_PREFETCH)
    return state if isinstance(state, dict) else None
