#!/usr/bin/env python3
"""Fail closed on automatic release effects and mutable GitHub Action refs."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


EFFECT_WORKFLOWS = {
    "manual-release.yml",
    "npm-publish.yml",
    "pages.yml",
    "release.yml",
}
SHA_PATTERN = re.compile(r"^[0-9a-fA-F]{40}$")
USES_PATTERN = re.compile(r"^\s*(?:-\s*)?uses:\s*([^\s#]+)")
WRITE_PERMISSION_PATTERN = re.compile(
    r"^\s+[A-Za-z][A-Za-z0-9_-]*:\s*write\s*(?:#.*)?$", re.MULTILINE
)


def workflow_triggers(text: str) -> set[str]:
    """Return top-level workflow event names from the ``on`` block."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = re.match(r"^(?:on|['\"]on['\"]):\s*(.*?)\s*$", line)
        if not match:
            continue

        inline = match.group(1)
        if inline:
            if inline.startswith("[") and inline.endswith("]"):
                return {
                    item.strip().strip("'\"")
                    for item in inline[1:-1].split(",")
                    if item.strip()
                }
            return {inline.strip().strip("'\"")}

        events: set[str] = set()
        for candidate in lines[index + 1 :]:
            if candidate and not candidate[0].isspace() and not candidate.lstrip().startswith("#"):
                break
            event = re.match(r"^  ([A-Za-z_][A-Za-z0-9_-]*):(?:\s|$)", candidate)
            if event:
                events.add(event.group(1))
        return events
    return set()


def validate(root: Path) -> list[str]:
    workflow_dir = root / ".github" / "workflows"
    errors: list[str] = []
    workflows = sorted(
        [*workflow_dir.glob("*.yml"), *workflow_dir.glob("*.yaml")]
    )

    if not workflows:
        return ["no GitHub workflows found"]

    for workflow in workflows:
        text = workflow.read_text(encoding="utf-8")
        relative = workflow.relative_to(root)
        triggers = workflow_triggers(text)

        if workflow.name in EFFECT_WORKFLOWS and triggers != {"workflow_dispatch"}:
            errors.append(
                f"{relative}: effect workflow must be manual-only; found {sorted(triggers)}"
            )

        if WRITE_PERMISSION_PATTERN.search(text) and triggers != {"workflow_dispatch"}:
            errors.append(
                f"{relative}: write-capable workflow must be manual-only; found {sorted(triggers)}"
            )

        for line_number, line in enumerate(text.splitlines(), start=1):
            uses = USES_PATTERN.match(line)
            if not uses:
                continue
            target = uses.group(1)
            if target.startswith("./"):
                continue
            if target.startswith("docker://"):
                if "@sha256:" not in target:
                    errors.append(
                        f"{relative}:{line_number}: Docker action is not digest-pinned: {target}"
                    )
                continue
            action, separator, reference = target.rpartition("@")
            if not separator or not action or not SHA_PATTERN.fullmatch(reference):
                errors.append(
                    f"{relative}:{line_number}: external action is not pinned to a 40-character SHA: {target}"
                )

    spec_gate = (workflow_dir / "spec-gate.yml").read_text(encoding="utf-8")
    if "validate_github_workflow_governance.py" not in spec_gate:
        errors.append(".github/workflows/spec-gate.yml: governance validator is not invoked")
    if "test_workflow_governance.py" not in spec_gate:
        errors.append(".github/workflows/spec-gate.yml: governance mutation tests are not invoked")
    if "contents: read" not in spec_gate:
        errors.append(".github/workflows/spec-gate.yml: explicit read-only permissions are missing")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors = validate(args.root.resolve())
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("GitHub workflow governance validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
