# Inverst Agent（研究优先的量化技术栈）

[English README](README.md)
[Quick load README](quick_setup_zh.md)

**设计目标：** 构建能够在**知识前沿替代人工完成研究工作**的 Agent——能够自由探索并产出高质量研究结论。它们是 **Cursor、Trae、Aider、MCP** 等开源工具的高级使用者，而不是重复造轮子的重构者；同时它们被设计为支持**深度思考**：提出问题、辩论路径、判断证据。当前可运行的重点是 scheme phase，详见 [scheme phase blueprint](docs/experiments/scheme_phase/blueprint.md)。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

## 什么是 Inverst Agent？

Inverst Agent 采用 **CIO 主导**的方式（见 `docs/policies/cio.md`）：由一条统一的编排线程把用户意图逐步转化为研究蓝图与验收证据——这与**单操作者**量化工作模式相匹配（全栈协同，而不是伪造“部门墙”）。**实现层**通过注册在 `docs/skills/manifest.json` 中的 **Markdown policy skills** 路由（例如 data-scientist、quant-researcher、quant-dev、quant-soul），它们是**阶段性合同**，而不是独立的“部门 Agent”。策略方法由 policies、`docs/reference/quant_tech_stack.md` 与 `knowledge/` 提供；`docs/agent/AGENTS.md` 中可选的 **Layer 1 / Layer 2 / Reviewer** 只是简写标签。执行阶段依赖**开源工具与外部 Agent**（例如 Cursor / Trae）。核心循环为：**mandate → evidence → gates → sign-off**。

## 关键特性

* **文献检索：** 搜索 Arxiv 以支持或反驳研究假设。
* **确定性实验：** 在显式假设下运行可复现实验。
* **证据门禁：** 将时效性与验证要求作为验收标准强制执行。
* **Skill-First 扩展：** 同时支持确定性的 `BaseSkill` 工具与定义在 [`docs/skills/manifest.json`](docs/skills/manifest.json) 中的 **Markdown policy skills**（CIO、quant-soul、data-scientist、quant-researcher、quant-dev）——它们是**阶段合同**，而不是不同“部门”的 Agent。

## 快速开始

### 1. 安装
```bash
git clone https://github.com/your-org/inverst_agent.git
cd inverst_agent
pip install -r requirements.txt
```

### 2. 配置（可选）
- `config/settings.yaml` —— API Key / 后端偏好设置。
- `config/agents.yaml` —— scheme phase 的 `scheme_phase.default_agent_model`（主工具循环 LLM）、`reviewers`、`translator`。可在运行时通过 `python scripts/run_scheme_agent.py --model ...` 或环境变量 `INVERST_SCHEME_AGENT_MODEL` 覆盖。

### 3. 命令示例

会话目录结构：`<runs_root>/<project>/<session>/`——例如 `~/Project/projects_generated/algo_alpha/main`。仓库内默认路径为 `out/<project>/<session>/`。制品存放在 `artifacts/`，代码位于 `project/src/`，运行输出在 `project/outputs/`。**`--project`** 和 **`--session`** 对应这两段路径（默认 session 名称为 `main`，除非设置了 `INVERST_DEFAULT_SCHEME_SESSION` 或使用 `timestamp`）。更多示例见 [`docs/guides/command_examples.md`](docs/guides/command_examples.md)。

**一条命令完成——scheme、execution prep 与 IDE coding 在同一进程内串联执行（推荐）：**

```bash
python scripts/run_research_session.py --project algo_alpha --ide-max-rounds 200 \
  "Your research task for the scheme phase"
```

其历史等价命令为：`python scripts/run_scheme_then_ide.py`（通过 `core/research_session_pipeline.py` 走同一管线）。可选参数包括：`--ide-task "…"`（只给 IDE 阶段的额外指令）、`--skip-execution-prep`、`--abort-ide-on-scheme-partial`。详情请查看这两个脚本的 `--help`。

**已废弃：** `scripts/run_autonomy_loop.py` —— 请改用 `run_research_session.py` 或 `run_scheme_then_ide.py`；详见 [`docs/skills/ARCHITECTURE.md`](docs/skills/ARCHITECTURE.md)。

Skill 分层（policy / ops / runtime）：[`docs/skills/ARCHITECTURE.md`](docs/skills/ARCHITECTURE.md)。

**冒烟测试（单次运行完成计划与编码）：** [`docs/experiments/smoke_plan_and_code.md`](docs/experiments/smoke_plan_and_code.md) —— `./scripts/smoke_research_session.sh`（需要可用的 LLM 后端）。

如果 scheme phase 在写完四个 `artifacts/*.md` 之前停止，组合运行会返回一个包含 `scheme_artifacts_missing` 字段的 JSON 结果——此时应提高 `--scheme-max-rounds`，或在同一 session 上重新运行 `run_scheme_agent`。

**分步执行——同一管线拆成三条命令：**

```bash
python scripts/run_scheme_agent.py --project algo_alpha "Your research task"
python scripts/run_execution_prep.py --project algo_alpha --resume-latest --workspace-root .
python scripts/run_ide_execution_agent.py "out/algo_alpha/$(cat out/algo_alpha/LATEST)" \
  --workspace-root . --max-rounds 200
```

（请使用英文直引号；`--max-rounds` 与 `200` 之间要有空格。）

**工具类命令（skills / tools）：**

- `python scripts/run_routed_tool.py --intent workspace.write --args-json '{"path":"demo.txt","content":"hello"}'`
- `python scripts/install_skill.py <path_to_skill_package>`
- `python scripts/list_skills.py --capability workspace.write`
- `python scripts/create_skill_template.py my_skill --output-dir /tmp`

建议的 skill 开发流程：`create_skill_template` → 编辑 `runtime.py` → `install_skill` → `run_routed_tool`。

## 文档

* [**文档索引**](docs/README.md)：合同与标准的起始页。
* [**项目状态**](docs/project_status.md)：当前路线图与活跃任务。
* [**工作日志**](docs/worklog.md)：仅记录关键行为变化的简明变更日志。
* [**Skill 目录**](docs/guides/skill_catalog.md)：可用 Python 工具（Skills）列表。
* [**编码规范**](docs/guides/coding_conventions.md)：代码贡献指南。
* [**模块合同**](docs/contracts/module_contracts.md)：模块边界、输入输出与证据产物说明。
* [**研究标准**](docs/contracts/research_standards.md)：验收门禁与证据标准。

历史说明：

## 路线图
* [x] Execution scaffolding MVP：消费 scheme 产物并生成 IDE 清单 / 工作区
* [x] Skill registry + intent router：支持安装、发现与按需调用
* [x] Runtime abstraction：提供 Local / MCP 兼容后端接口

## 许可证
MIT
