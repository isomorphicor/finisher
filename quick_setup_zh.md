# 极简启动说明

## 1. 安装依赖

```bash
pip install -r requirements.txt
```

## 2. 配置 DeepSeek

在仓库根目录创建 `.env`：

```dotenv
OPENAI_API_KEY=你的 DeepSeek Key
OPENAI_API_BASE=https://api.deepseek.com/v1
```

说明：代码已在启动时自动读取仓库根目录的 `.env`。

## 3. 配置模型与本地路径

编辑 `config/settings.yaml`：

```yaml
llm:
  provider: "openai"
  default_model: "openai/deepseek-chat"
  openai:
    api_base: "https://api.deepseek.com/v1"

paths:
  data_dir: "/home/foo/test/data"
  runs_dir: "/home/foo/test/projects_generated"
  workspace_root: "/home/foo/test/"
```

编辑 `config/agents.yaml`：

```yaml
ide_execution:
  coder_model: "openai/deepseek-chat"

supervisor:
  cio_model: "openai/deepseek-chat"

scheme_phase:
  default_agent_model: "openai/deepseek-chat"
```

## 4. 准备目录

至少确保以下目录可用：

- `/home/foo/test/`
- `/home/foo/test/data`

`/home/foo/test/projects_generated` 可在首次运行时由程序自动创建。

## 5. 启动命令

```bash
python scripts/run_research_session.py "设计一个新因子"
```

## 6. 输出位置

生成的工程默认在：

```text
/home/foo/test/projects_generated/
```

如果只想确认程序是否可启动，可先执行：

```bash
python scripts/run_research_session.py --help
```
