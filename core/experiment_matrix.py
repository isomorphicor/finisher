from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.scheme_contract import EXPERIMENT_MATRIX_SCHEMA_VERSION


@dataclass(frozen=True)
class MatrixBuildResult:
    ok: bool
    matrix: dict[str, Any]
    errors: list[dict[str, Any]]


def _as_list(x: Any) -> list:
    return x if isinstance(x, list) else []


def _as_str(x: Any) -> str:
    return str(x).strip() if x is not None else ""


def _as_float(x: Any) -> float | None:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def build_experiment_matrix_from_scheme_summary(summary: dict[str, Any]) -> MatrixBuildResult:
    errors: list[dict[str, Any]] = []
    experiments_in = _as_list(summary.get("experiments"))
    metrics_in = _as_list(summary.get("metrics"))
    hypotheses_in = _as_list(summary.get("hypotheses"))
    variables_in = _as_list(summary.get("variables"))

    metrics_by_name: dict[str, dict[str, Any]] = {}
    for m in metrics_in:
        if isinstance(m, dict):
            name = _as_str(m.get("name"))
            if name:
                metrics_by_name[name] = m

    hyp_by_id: dict[str, dict[str, Any]] = {}
    for h in hypotheses_in:
        if isinstance(h, dict):
            hid = _as_str(h.get("id"))
            if hid:
                hyp_by_id[hid] = h

    variables_by_name: dict[str, dict[str, Any]] = {}
    for v in variables_in:
        if isinstance(v, dict):
            name = _as_str(v.get("name"))
            if name:
                variables_by_name[name] = v

    matrix_rows: list[dict[str, Any]] = []
    for e in experiments_in:
        if not isinstance(e, dict):
            continue
        exp_id = _as_str(e.get("id"))
        if not exp_id:
            errors.append({"code": "E_EXP_ID", "message": "experiment missing id", "details": {"experiment": e}})
            continue

        hyp_ids = [_as_str(x) for x in _as_list(e.get("hypothesis_ids")) if _as_str(x)]
        hyp_statements = []
        for hid in hyp_ids:
            h = hyp_by_id.get(hid)
            if h:
                hyp_statements.append(_as_str(h.get("statement")) or hid)

        factors = []
        for f in _as_list(e.get("factors")):
            if not isinstance(f, dict):
                continue
            fname = _as_str(f.get("name"))
            if not fname:
                continue
            levels = [_as_str(x) for x in _as_list(f.get("levels")) if _as_str(x)]
            default = _as_str(f.get("default"))
            factors.append(
                {
                    "name": fname,
                    "levels": levels,
                    "default": default,
                    "notes": _as_str(f.get("notes")),
                    "variable_role": _as_str(variables_by_name.get(fname, {}).get("role")),
                }
            )

        pass_conditions = []
        for pc in _as_list(e.get("pass_conditions")):
            if isinstance(pc, dict):
                metric = _as_str(pc.get("metric"))
                op = _as_str(pc.get("operator"))
                val = _as_float(pc.get("value"))
                if not metric or not op or val is None:
                    continue
                pass_conditions.append({"metric": metric, "operator": op, "value": val, "notes": _as_str(pc.get("notes"))})
            else:
                s = _as_str(pc)
                if s:
                    pass_conditions.append({"metric": "", "operator": "", "value": 0.0, "notes": s})

        eval_metrics = [_as_str(x) for x in _as_list(e.get("eval_metrics")) if _as_str(x)]
        eval_metrics_meta = [metrics_by_name.get(n, {"name": n}) for n in eval_metrics]

        matrix_rows.append(
            {
                "id": exp_id,
                "hypothesis_ids": hyp_ids,
                "hypotheses": hyp_statements,
                "setup": _as_str(e.get("setup")),
                "vary": [_as_str(x) for x in _as_list(e.get("vary")) if _as_str(x)],
                "hold_fixed": [_as_str(x) for x in _as_list(e.get("hold_fixed")) if _as_str(x)],
                "factors": factors,
                "baselines": [_as_str(x) for x in _as_list(e.get("baselines")) if _as_str(x)],
                "eval_metrics": eval_metrics,
                "eval_metrics_meta": eval_metrics_meta,
                "expected_outcome": _as_str(e.get("expected_outcome")),
                "pass_conditions": pass_conditions,
                "run_order_hint": _as_str(e.get("run_order_hint")),
                "risks": [_as_str(x) for x in _as_list(e.get("risks")) if _as_str(x)],
            }
        )

    out = {
        "schema_version": EXPERIMENT_MATRIX_SCHEMA_VERSION,
        "task_summary": _as_str(summary.get("task_summary")),
        "data_protocol": summary.get("data_protocol") if isinstance(summary.get("data_protocol"), dict) else {},
        "matrix": matrix_rows,
    }
    return MatrixBuildResult(ok=(len(errors) == 0 and len(matrix_rows) > 0), matrix=out, errors=errors)

