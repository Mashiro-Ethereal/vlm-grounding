#!/usr/bin/env python3
"""
Split OSWorld task definitions into setup.json and verify.json.

Source: references/OSWorld/evaluation_examples/examples/{app}/{task_id}.json
Target: tasks/{app}/{task_id}/
        ├── task.json      # Original complete task (for reference)
        ├── setup.json     # config + instruction + related metadata
        └── verify.json    # evaluator section
"""

import json
import shutil
from pathlib import Path


def split_task(task_data: dict) -> tuple[dict, dict]:
    """Split a task into setup and verify components."""
    setup = {
        "id": task_data["id"],
        "instruction": task_data["instruction"],
        "config": task_data.get("config", []),
        "snapshot": task_data.get("snapshot"),
        "related_apps": task_data.get("related_apps", []),
    }

    # Optional fields for setup
    if "source" in task_data:
        setup["source"] = task_data["source"]
    if "proxy" in task_data:
        setup["proxy"] = task_data["proxy"]
    if "fixed_ip" in task_data:
        setup["fixed_ip"] = task_data["fixed_ip"]

    verify = {
        "id": task_data["id"],
        "evaluator": task_data.get("evaluator", {}),
    }

    # Include possibility_of_env_change in verify (affects evaluation)
    if "possibility_of_env_change" in task_data:
        verify["possibility_of_env_change"] = task_data["possibility_of_env_change"]

    return setup, verify


def process_app_tasks(source_dir: Path, target_dir: Path, app: str) -> int:
    """Process all tasks for a specific app."""
    app_source = source_dir / app
    app_target = target_dir / app

    if not app_source.exists():
        print(f"Source directory not found: {app_source}")
        return 0

    count = 0
    for task_file in sorted(app_source.glob("*.json")):
        task_id = task_file.stem
        task_target = app_target / task_id
        task_target.mkdir(parents=True, exist_ok=True)

        # Load original task
        with open(task_file) as f:
            task_data = json.load(f)

        # Split into setup and verify
        setup, verify = split_task(task_data)

        # Write files
        with open(task_target / "task.json", "w") as f:
            json.dump(task_data, f, indent=2)

        with open(task_target / "setup.json", "w") as f:
            json.dump(setup, f, indent=2)

        with open(task_target / "verify.json", "w") as f:
            json.dump(verify, f, indent=2)

        count += 1
        print(f"  {task_id}")

    return count


def main():
    project_root = Path(__file__).parent.parent
    source_dir = project_root / "references" / "OSWorld" / "evaluation_examples" / "examples"
    target_dir = project_root / "tasks"

    # For now, only process chrome
    apps = ["chrome"]

    print(f"Source: {source_dir}")
    print(f"Target: {target_dir}")
    print()

    total = 0
    for app in apps:
        print(f"Processing {app}...")
        count = process_app_tasks(source_dir, target_dir, app)
        print(f"  -> {count} tasks\n")
        total += count

    print(f"Total: {total} tasks processed")


if __name__ == "__main__":
    main()
