from __future__ import annotations

from dataclasses import dataclass


@dataclass
class QuantGateResult:
    ok: bool
    missing: list[str]
    must_fix: list[str]


def _has_any(text: str, needles: list[str]) -> bool:
    t = (text or "").lower()
    return any(n.lower() in t for n in needles if n)
def run_quant_soul_gate(*, scheme_text: str) -> QuantGateResult:
    missing: list[str] = []
    must_fix: list[str] = []

    time_safety_ok = _has_any(
        scheme_text,
        [
            "time-safety",
            "time safety",
            "cpcv",
            "purge",
            "embargo",
            "next open",
            "next-open",
            "execution price",
            "trade is executed",
            "信号",
            "执行价",
            "成交价",
            "下一开盘",
            "走前",
            "走前测试",
            "滚动",
            "不允许偷看",
            "未来信息",
        ],
    )
    if not time_safety_ok:
        missing.append("time_safety")
        must_fix.append("Add explicit time-safety: data availability timestamp, signal time, and execution price assumption (no look-ahead).")

    leakage_bias_ok = _has_any(
        scheme_text,
        [
            "leakage",
            "look-ahead",
            "survivorship",
            "delisting",
            "corporate action",
            "point-in-time",
            "revision",
            "偏差",
            "泄露",
            "幸存者",
            "退市",
            "复权",
            "回填",
            "修订",
            "点时可得",
        ],
    )
    if not leakage_bias_ok:
        missing.append("leakage_bias")
        must_fix.append("Add a bias/leakage checklist: survivorship, corporate actions, point-in-time fundamentals, missing data handling.")

    backtest_protocol_ok = _has_any(
        scheme_text,
        [
            "cpcv",
            "combinatorial purged",
            "purged",
            "embargo",
            "model validation",
            "model selection",
            "final backtest",
            "回测",
            "cpcv",
            "组合净化",
            "purged",
            "embargo",
            "模型验证",
            "模型选择",
            "最终回测",
        ],
    )
    if not backtest_protocol_ok:
        missing.append("backtest_protocol")
        must_fix.append("Specify supervised validation protocol with CPCV (purge+embargo) for model acceptance, and keep final portfolio backtest as a separate downstream step.")

    target_alignment_ok = _has_any(
        scheme_text,
        [
            "prediction target",
            "target alignment",
            "objective-aligned",
            "strategy objective",
            "weights",
            "signal to weight",
            "pnl objective",
            "预测目标",
            "目标一致",
            "策略目标",
            "权重映射",
            "信号到权重",
        ],
    )
    if not target_alignment_ok:
        missing.append("target_objective_alignment")
        must_fix.append("Make prediction target explicitly aligned with strategy objective, and specify deterministic mapping from model output to tradable weights/signals.")

    overfit_reject_ok = _has_any(
        scheme_text,
        [
            "pbo",
            "probability of backtest overfitting",
            "overfitting probability",
            "reject",
            "discard",
            "stop tuning",
            "kill",
            "过拟合概率",
            "直接丢弃",
            "拒绝",
            "停止优化",
        ],
    )
    if not overfit_reject_ok:
        missing.append("overfit_fail_fast")
        must_fix.append("Add fail-fast rule: if overfitting-risk diagnostics (e.g., PBO) exceed threshold, reject/discard the candidate and stop further tuning on that line.")

    costs_constraints_ok = _has_any(
        scheme_text,
        [
            "transaction cost",
            "slippage",
            "impact",
            "turnover",
            "leverage",
            "position limit",
            "capacity",
            "cost model",
            "交易成本",
            "滑点",
            "冲击",
            "换手",
            "杠杆",
            "仓位限制",
            "容量",
            "参与率",
        ],
    )
    if not costs_constraints_ok:
        missing.append("costs_constraints")
        must_fix.append("Add costs/constraints: transaction cost + slippage/impact, leverage/position/turnover limits, and a capacity proxy.")

    metrics_ok = _has_any(
        scheme_text,
        [
            "sharpe",
            "sortino",
            "drawdown",
            "cvar",
            "var",
            "turnover",
            "pass condition",
            "acceptance",
            "夏普",
            "最大回撤",
            "回撤",
            "cvar",
            "var",
            "换手",
            "通过条件",
            "验收",
        ],
    )
    if not metrics_ok:
        missing.append("metrics_acceptance")
        must_fix.append(
            "Name portfolio-level metrics (e.g. Sharpe, drawdown, turnover, cost-adjusted) and define pass/fail vs explicit baselines and mandate. "
            "Do not invent numeric cutoffs in the scheme phase—mark thresholds provisional/TBD and tie them to data calibration or investor constraints (quant_soul: no universal turnover/DD/Sharpe bounds)."
        )

    failure_modes_ok = _has_any(
        scheme_text,
        [
            "failure mode",
            "monitor",
            "regime shift",
            "non-stationary",
            "tail risk",
            "overfitting",
            "drift",
            "失效",
            "故障",
            "监控",
            "漂移",
            "非平稳",
            "尾部风险",
            "过拟合",
            "回滚",
            "停机",
        ],
    )
    if not failure_modes_ok:
        missing.append("failure_modes")
        must_fix.append("Add failure modes + monitoring/mitigation: drift/regime shift, tail risk, overfitting, liquidity/capacity, data issues.")

    ok = not missing
    return QuantGateResult(ok=ok, missing=missing, must_fix=must_fix)
