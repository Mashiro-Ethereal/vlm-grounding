from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from . import paths


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
    task_file = paths.task_path(trajectory_dir)
    if not task_file.exists():
        issues.append(_issue(task_file, "Missing task.json", "error"))

    traj_steps_dir = paths.steps_dir(trajectory_dir)
    if not traj_steps_dir.exists():
        issues.append(_issue(traj_steps_dir, "Missing steps directory", "error"))
        return issues

    step_dirs = [entry for entry in traj_steps_dir.iterdir() if entry.is_dir()]
    if not step_dirs:
        issues.append(_issue(traj_steps_dir, "No steps found", "warning"))

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
            issues.append(_issue(traj_steps_dir, "Step indices are not contiguous", "warning"))

    for entry in step_dirs:
        action_file = paths.action_path(entry)
        ui_tree_file = paths.ui_tree_path(entry)
        screenshot_file = paths.screenshot_path(entry)
        if not action_file.exists():
            issues.append(_issue(action_file, "Missing action.json", "error"))
        if not ui_tree_file.exists():
            issues.append(_issue(ui_tree_file, "Missing ui_tree.json", "error"))
        if not screenshot_file.exists():
            issues.append(_issue(screenshot_file, "Missing screenshot.png", "error"))

    result_file = paths.result_path(trajectory_dir)
    if require_result and not result_file.exists():
        issues.append(_issue(result_file, "Missing result.json", "error"))
    elif not result_file.exists():
        issues.append(_issue(result_file, "Missing result.json", "warning"))

    final_screenshot_file = paths.final_screenshot_path(trajectory_dir)
    if require_final_screenshot and not final_screenshot_file.exists():
        issues.append(_issue(final_screenshot_file, "Missing final_screenshot.png", "error"))
    elif not final_screenshot_file.exists():
        issues.append(_issue(final_screenshot_file, "Missing final_screenshot.png", "warning"))

    return issues


def validate_dataset_dir(dataset_dir: Path) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    traj_dir = paths.trajectories_dir(dataset_dir)
    if not traj_dir.exists():
        issues.append(_issue(traj_dir, "Missing trajectories directory", "error"))
        return issues

    index_file = paths.dataset_index_path(dataset_dir)
    if not index_file.exists():
        issues.append(_issue(index_file, "Missing index.json", "warning"))

    metadata_file = paths.dataset_metadata_path(dataset_dir)
    if not metadata_file.exists():
        issues.append(_issue(metadata_file, "Missing metadata.json", "warning"))

    for trajectory_dir in traj_dir.iterdir():
        if not trajectory_dir.is_dir():
            continue
        issues.extend(validate_trajectory_dir(trajectory_dir))

    return issues
