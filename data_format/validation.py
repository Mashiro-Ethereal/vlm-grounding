from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from .constants import (
    ACTION_FILENAME,
    FINAL_SCREENSHOT_FILENAME,
    METADATA_FILENAME,
    RESULT_FILENAME,
    SCREENSHOT_FILENAME,
    STEPS_DIRNAME,
    TASK_FILENAME,
    UI_TREE_FILENAME,
)


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    message: str
    severity: str  # "error" or "warning"


def _issue(path: Path, message: str, severity: str) -> ValidationIssue:
    return ValidationIssue(path=str(path), message=message, severity=severity)


def validate_trajectory_dir(
    trajectory_dir: Path,
    require_final_screenshot: bool = False,
    require_result: bool = False,
) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    task_path = trajectory_dir / TASK_FILENAME
    if not task_path.exists():
        issues.append(_issue(task_path, "Missing task.json", "error"))

    steps_dir = trajectory_dir / STEPS_DIRNAME
    if not steps_dir.exists():
        issues.append(_issue(steps_dir, "Missing steps directory", "error"))
        return issues

    step_dirs = [entry for entry in steps_dir.iterdir() if entry.is_dir()]
    if not step_dirs:
        issues.append(_issue(steps_dir, "No steps found", "warning"))

    numeric_steps = []
    for entry in step_dirs:
        try:
            numeric_steps.append(int(entry.name))
        except ValueError:
            issues.append(_issue(entry, "Step directory name is not numeric", "warning"))

    numeric_steps_sorted = sorted(numeric_steps)
    if numeric_steps_sorted:
        expected = list(range(numeric_steps_sorted[0], numeric_steps_sorted[-1] + 1))
        if numeric_steps_sorted != expected:
            issues.append(_issue(steps_dir, "Step indices are not contiguous", "warning"))

    for entry in step_dirs:
        action_path = entry / ACTION_FILENAME
        ui_tree_path = entry / UI_TREE_FILENAME
        screenshot_path = entry / SCREENSHOT_FILENAME
        if not action_path.exists():
            issues.append(_issue(action_path, "Missing action.json", "error"))
        if not ui_tree_path.exists():
            issues.append(_issue(ui_tree_path, "Missing ui_tree.json", "error"))
        if not screenshot_path.exists():
            issues.append(_issue(screenshot_path, "Missing screenshot.png", "error"))

    result_path = trajectory_dir / RESULT_FILENAME
    if require_result and not result_path.exists():
        issues.append(_issue(result_path, "Missing result.json", "error"))
    elif not result_path.exists():
        issues.append(_issue(result_path, "Missing result.json", "warning"))

    final_screenshot_path = trajectory_dir / FINAL_SCREENSHOT_FILENAME
    if require_final_screenshot and not final_screenshot_path.exists():
        issues.append(_issue(final_screenshot_path, "Missing final_screenshot.png", "error"))
    elif not final_screenshot_path.exists():
        issues.append(_issue(final_screenshot_path, "Missing final_screenshot.png", "warning"))

    return issues


def validate_dataset_dir(dataset_dir: Path) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    trajectories_dir = dataset_dir / "trajectories"
    if not trajectories_dir.exists():
        issues.append(_issue(trajectories_dir, "Missing trajectories directory", "error"))
        return issues

    index_path = dataset_dir / "index.json"
    if not index_path.exists():
        issues.append(_issue(index_path, "Missing index.json", "warning"))

    metadata_path = dataset_dir / METADATA_FILENAME
    if not metadata_path.exists():
        issues.append(_issue(metadata_path, "Missing metadata.json", "warning"))

    for trajectory_dir in trajectories_dir.iterdir():
        if not trajectory_dir.is_dir():
            continue
        issues.extend(validate_trajectory_dir(trajectory_dir))

    return issues
