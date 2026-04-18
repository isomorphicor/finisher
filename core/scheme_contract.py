from __future__ import annotations

from dataclasses import dataclass


REQUIRED_SCHEME_ARTIFACTS: tuple[str, ...] = (
    "research_plan.md",
    "derivation.md",
    "architecture_draft.md",
    "experiment_design.md",
)


@dataclass(frozen=True)
class SectionRequirement:
    canonical: str
    variants: tuple[str, ...]


RESEARCH_PLAN_SECTIONS: tuple[SectionRequirement, ...] = (
    SectionRequirement("Problem Statement", ("problem", "problem statement", "background", "motivation")),
    SectionRequirement("Success Criteria", ("success criteria", "success", "goals", "objectives")),
    SectionRequirement("Constraints", ("constraints", "assumptions", "scope")),
    SectionRequirement("Literature Synthesis", ("literature synthesis", "literature review", "related work")),
)

DERIVATION_SECTIONS: tuple[SectionRequirement, ...] = (
    SectionRequirement("Notation", ("notation", "symbols")),
    SectionRequirement("Assumptions", ("assumptions", "setting")),
    SectionRequirement("Objective", ("objective", "loss", "optimization problem")),
)

ARCHITECTURE_SECTIONS: tuple[SectionRequirement, ...] = (
    SectionRequirement("Candidates", ("candidate architectures", "candidates", "architecture candidates", "architectures")),
    SectionRequirement("Modules/Data Flow", ("modules", "data flow", "pipeline", "interfaces")),
)

EXPERIMENT_DESIGN_SECTIONS: tuple[SectionRequirement, ...] = (
    SectionRequirement("Hypotheses", ("hypotheses", "hypothesis")),
    SectionRequirement("Variables", ("variables", "factors")),
    SectionRequirement("Experiment Matrix", ("experiment matrix", "experiments", "ablation", "study design")),
    SectionRequirement("Metrics", ("metrics", "evaluation", "score")),
    SectionRequirement("Pass Conditions", ("pass conditions", "acceptance criteria", "stopping criteria")),
)


SCHEME_SUMMARY_SCHEMA_VERSION = "scheme_summary_v1"
EXPERIMENT_MATRIX_SCHEMA_VERSION = "experiment_matrix_v1"

