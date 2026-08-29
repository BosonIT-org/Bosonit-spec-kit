from __future__ import annotations

import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validate_github_workflow_governance.py"
SPEC = importlib.util.spec_from_file_location("workflow_governance", MODULE_PATH)
assert SPEC and SPEC.loader
WORKFLOW_GOVERNANCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WORKFLOW_GOVERNANCE)


class WorkflowGovernanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        shutil.copytree(ROOT / ".github", self.root / ".github")

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_repository_workflows_pass(self) -> None:
        self.assertEqual([], WORKFLOW_GOVERNANCE.validate(ROOT))

    def test_mutable_action_reference_fails(self) -> None:
        workflow = self.root / ".github" / "workflows" / "spec-gate.yml"
        workflow.write_text(
            workflow.read_text(encoding="utf-8").replace(
                "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
                "actions/checkout@v4",
            ),
            encoding="utf-8",
        )
        errors = WORKFLOW_GOVERNANCE.validate(self.root)
        self.assertTrue(any("not pinned" in error for error in errors), errors)

    def test_automatic_release_trigger_fails(self) -> None:
        workflow = self.root / ".github" / "workflows" / "release.yml"
        workflow.write_text(
            workflow.read_text(encoding="utf-8").replace(
                "on:\n", "on:\n  push:\n    branches: [main]\n", 1
            ),
            encoding="utf-8",
        )
        errors = WORKFLOW_GOVERNANCE.validate(self.root)
        self.assertTrue(any("manual-only" in error for error in errors), errors)

    def test_release_event_package_publish_fails(self) -> None:
        workflow = self.root / ".github" / "workflows" / "npm-publish.yml"
        workflow.write_text(
            workflow.read_text(encoding="utf-8").replace(
                "on:\n", "on:\n  release:\n    types: [published]\n", 1
            ),
            encoding="utf-8",
        )
        errors = WORKFLOW_GOVERNANCE.validate(self.root)
        self.assertTrue(any("manual-only" in error for error in errors), errors)

    def test_new_write_capable_push_workflow_fails(self) -> None:
        workflow = self.root / ".github" / "workflows" / "unsafe.yml"
        workflow.write_text(
            """name: Unsafe
on:
  push:
permissions:
  contents: write
jobs:
  unsafe:
    runs-on: ubuntu-latest
    steps:
      - run: true
""",
            encoding="utf-8",
        )
        errors = WORKFLOW_GOVERNANCE.validate(self.root)
        self.assertTrue(any("write-capable" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
