# execution_report (this run)

**Run:** `<tag>` | **Session:** `<id>`

## 1. Data
- Schema / keys / dates / labels (brief).

## 2. Runs
- Commands (repo-relative paths). Inputs → outputs under `project/`.

## 3. Metrics
- Key numbers + artifact paths (`models/`, `data/`).

## 4. Baseline contract (supervised NN + GBDT; pretrain/gen/RL = row D)

| | ok/N/A | evidence |
|--|--------|----------|
| A Supervised NN default **1 epoch** | | |
| B GBDT fixed **~300** rounds | | |
| C `Path(__file__)` project root | | |
| D Pretrain/gen/RL: epochs + stop rule | | |
| E Deviations documented | | |

## 5. Next / blockers

## 6. Promote to `knowledge/`? (optional)
Lesson one-liner + sink (`ide_lessons.md` / skip). See `docs/templates/knowledge_promotion_checklist.md`.
