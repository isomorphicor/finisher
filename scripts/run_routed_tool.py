from __future__ import annotations

import argparse
import json
from pathlib import Path

from runtime.router.intent_router import IntentRouter
from runtime.runtime_factory import build_runtime


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one routed skill call.")
    parser.add_argument("--intent", required=True, help="Intent/capability, e.g. workspace.read, workspace.write, terminal.run")
    parser.add_argument("--args-json", default="{}", help="JSON object with tool arguments")
    parser.add_argument("--backend", choices=["local", "mcp"], default="local", help="Runtime backend")
    parser.add_argument("--workspace-root", default=".", help="Workspace root")
    parser.add_argument("--repo-root", default=".", help="Repository root")
    args = parser.parse_args()

    runtime = build_runtime(workspace_root=Path(args.workspace_root), backend=args.backend)
    router = IntentRouter(repo_root=Path(args.repo_root), runtime=runtime)
    arguments = json.loads(args.args_json)
    out = router.route(intent=args.intent, arguments=arguments)
    print(json.dumps(out, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

