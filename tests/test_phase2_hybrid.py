import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from core.execution_prep import prepare_execution_workspace
from runtime.router.intent_router import IntentRouter
from runtime.runtime_factory import build_runtime
from skills.registry_manager import SkillRegistry


class TestPhase2Hybrid(unittest.TestCase):
    def test_execution_prep_generates_workspace_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            session = root / "out" / "scheme_phase" / "sessions" / "s1"
            art = session / "artifacts"
            art.mkdir(parents=True, exist_ok=True)
            for name in ("research_plan.md", "derivation.md", "architecture_draft.md", "experiment_design.md"):
                (art / name).write_text(f"# {name}\n", encoding="utf-8")
            out = prepare_execution_workspace(scheme_session_dir=session, workspace_root=root)
            self.assertEqual(out["status"], "success")
            target = root / out["report"]["target_root"]
            self.assertTrue((target / "scheme" / "research_plan.md").is_file())
            self.assertTrue((target / "NEXT_STEPS.md").is_file())
            self.assertTrue((target / "run_log.json").is_file())

    def test_registry_install_and_route_custom_skill(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d) / "repo"
            (repo / "skills" / "core").mkdir(parents=True, exist_ok=True)
            (repo / "skills" / "installed").mkdir(parents=True, exist_ok=True)
            (repo / "skills" / "registry").mkdir(parents=True, exist_ok=True)
            (repo / "skills" / "registry" / "manifest.json").write_text('{"schema_version":"skill_registry_v1","skills":[]}', encoding="utf-8")
            pkg = Path(d) / "my_skill"
            pkg.mkdir(parents=True, exist_ok=True)
            (pkg / "skill_manifest.json").write_text(
                json.dumps(
                    {
                        "id": "hello_skill",
                        "version": "0.1.0",
                        "entry": "skills.installed.hello_skill.runtime:hello",
                        "capabilities": ["custom.hello"],
                        "tags": ["custom"],
                        "trust": "project",
                    }
                ),
                encoding="utf-8",
            )
            (pkg / "__init__.py").write_text("", encoding="utf-8")
            (pkg / "runtime.py").write_text(
                "def hello(runtime, **kwargs):\n"
                "    return {'status':'success','report':{'message':'hello','kwargs':kwargs}}\n",
                encoding="utf-8",
            )
            target_pkg = repo / "skills" / "installed" / "hello_skill"
            target_pkg.mkdir(parents=True, exist_ok=True)
            (target_pkg / "__init__.py").write_text("", encoding="utf-8")
            (target_pkg / "runtime.py").write_text(
                "def hello(runtime, **kwargs):\n"
                "    return {'status':'success','report':{'message':'hello','kwargs':kwargs}}\n",
                encoding="utf-8",
            )
            reg = SkillRegistry(repo)
            out = reg.install_from_path(pkg)
            self.assertEqual(out["status"], "success")
            fn, entry = reg.load_callable("hello_skill")
            invoked = fn(None, x=1)
            self.assertEqual(entry.id, "hello_skill")
            self.assertEqual(invoked["status"], "success")
            self.assertEqual(invoked["report"]["message"], "hello")

    def test_local_and_mcp_consistency(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d) / "repo"
            repo.mkdir(parents=True, exist_ok=True)
            workspace = repo / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)

            local = build_runtime(workspace_root=workspace, backend="local")
            mcp = build_runtime(workspace_root=workspace, backend="mcp")
            local_router = IntentRouter(repo_root=repo, runtime=local)
            mcp_router = IntentRouter(repo_root=repo, runtime=mcp)

            write_local = local_router.route(intent="workspace.write", arguments={"path": "a.txt", "content": "abc"})
            self.assertEqual(write_local["status"], "success")
            read_local = local_router.route(intent="workspace.read", arguments={"path": "a.txt"})
            read_mcp = mcp_router.route(intent="workspace.read", arguments={"path": "a.txt"})
            self.assertEqual(read_local["status"], "success")
            self.assertEqual(read_mcp["status"], "success")
            self.assertEqual(read_local["report"]["content"], read_mcp["report"]["content"])

    def test_three_end_to_end_examples(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d) / "repo"
            repo.mkdir(parents=True, exist_ok=True)
            ws = repo / "workspace"
            ws.mkdir(parents=True, exist_ok=True)
            router = IntentRouter(repo_root=repo, runtime=build_runtime(workspace_root=ws, backend="local"))

            ex1 = router.route(intent="workspace.write", arguments={"path": "notes/x.md", "content": "draft"})
            ex2 = router.route(intent="workspace.list", arguments={"path": "notes"})
            ex3 = router.route(intent="terminal.run", arguments={"command": "echo ok"})
            self.assertEqual(ex1["status"], "success")
            self.assertEqual(ex2["status"], "success")
            self.assertEqual(ex3["status"], "success")

    def test_manifest_policy_rejects_unknown_permissions(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d) / "repo"
            (repo / "skills" / "core").mkdir(parents=True, exist_ok=True)
            (repo / "skills" / "installed").mkdir(parents=True, exist_ok=True)
            (repo / "skills" / "registry").mkdir(parents=True, exist_ok=True)
            (repo / "skills" / "registry" / "manifest.json").write_text('{"schema_version":"skill_registry_v1","skills":[]}', encoding="utf-8")
            pkg = Path(d) / "bad_skill"
            pkg.mkdir(parents=True, exist_ok=True)
            (pkg / "skill_manifest.json").write_text(
                json.dumps(
                    {
                        "id": "bad_skill",
                        "version": "0.1.0",
                        "entry": "skills.installed.bad_skill.runtime:run",
                        "requirements": {"permissions": ["file", "shell_root"]},
                    }
                ),
                encoding="utf-8",
            )
            reg = SkillRegistry(repo)
            out = reg.install_from_path(pkg)
            self.assertEqual(out["status"], "rejected")
            self.assertEqual(out["errors"][0]["code"], "E_POLICY")

    def test_create_skill_template_script(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d) / "repo"
            repo.mkdir(parents=True, exist_ok=True)
            cmd = [
                "python",
                "scripts/create_skill_template.py",
                "demo_skill",
                "--output-dir",
                str(repo),
            ]
            cp = subprocess.run(cmd, cwd="/home/foo/test/inverst_agent", capture_output=True, text=True, check=True)
            payload = json.loads(cp.stdout.strip())
            self.assertEqual(payload["status"], "success")
            created = Path(payload["report"]["created"])
            self.assertTrue((created / "skill_manifest.json").is_file())
            self.assertTrue((created / "runtime.py").is_file())


if __name__ == "__main__":
    unittest.main()

