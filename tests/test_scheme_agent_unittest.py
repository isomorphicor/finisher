import json
import tempfile
import unittest
from pathlib import Path

from core.experiment_matrix import build_experiment_matrix_from_scheme_summary
from core.scheme_agent import _section_gate


class TestSchemeAgentGates(unittest.TestCase):
    def test_section_gate_detects_missing_sections(self):
        with tempfile.TemporaryDirectory() as d:
            run_root = Path(d)
            (run_root / "artifacts").mkdir(parents=True, exist_ok=True)
            (run_root / "artifacts" / "research_plan.md").write_text("# Problem\n\nx\n", encoding="utf-8")
            (run_root / "artifacts" / "derivation.md").write_text("# Notation\n\nx\n", encoding="utf-8")
            (run_root / "artifacts" / "architecture_draft.md").write_text("# Candidates\n\nx\n", encoding="utf-8")
            (run_root / "artifacts" / "experiment_design.md").write_text("# Hypotheses\n\nx\n", encoding="utf-8")
            out = _section_gate(run_root)
            self.assertFalse(out["ok"])
            self.assertIn("research_plan.md", out["missing_sections"])
            self.assertTrue(len(out["missing_sections"]["experiment_design.md"]) >= 1)


class TestExperimentMatrix(unittest.TestCase):
    def test_build_matrix_from_summary(self):
        summary = {
            "schema_version": "scheme_summary_v1",
            "task_summary": "test",
            "metrics": [{"name": "Sharpe", "definition": "x", "direction": "higher_better", "notes": ""}],
            "hypotheses": [{"id": "H1", "statement": "A improves B", "why_it_matters": "x"}],
            "variables": [{"name": "beta", "role": "hyperparam", "levels": ["0.1", "1.0"], "notes": ""}],
            "experiments": [
                {
                    "id": "Exp1",
                    "hypothesis_ids": ["H1"],
                    "setup": "x",
                    "vary": ["beta"],
                    "hold_fixed": [],
                    "factors": [{"name": "beta", "levels": ["0.1", "1.0"], "default": "0.1", "notes": ""}],
                    "baselines": ["base"],
                    "eval_metrics": ["Sharpe"],
                    "expected_outcome": "x",
                    "pass_conditions": [{"metric": "Sharpe", "operator": ">=", "value": 1.0, "notes": ""}],
                    "run_order_hint": "early",
                    "risks": [],
                }
            ],
            "data_protocol": {"data_requirements": [], "time_safety_split": "", "leakage_checks": []},
        }
        built = build_experiment_matrix_from_scheme_summary(summary)
        self.assertTrue(built.ok)
        self.assertEqual(built.matrix["schema_version"], "experiment_matrix_v1")
        self.assertEqual(built.matrix["matrix"][0]["id"], "Exp1")
        json.dumps(built.matrix, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()

