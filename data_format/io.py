from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .constants import (
    ACTION_FILENAME,
    FINAL_SCREENSHOT_FILENAME,
    RESULT_FILENAME,
    SCREENSHOT_FILENAME,
    STEPS_DIRNAME,
    TASK_FILENAME,
    UI_TREE_FILENAME,
)
from .models import Action, DatasetIndex, Result, Step, Task, Trajectory


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _dump_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2)


def load_task(path: Path) -> Task:
    return Task.from_dict(_load_json(path))


def load_action(path: Path) -> Action:
    return Action.from_dict(_load_json(path))


def load_result(path: Path) -> Result:
    return Result.from_dict(_load_json(path))


def load_step(step_dir: Path) -> Step:
    action = load_action(step_dir / ACTION_FILENAME)
    ui_tree = _load_json(step_dir / UI_TREE_FILENAME)
    screenshot_path = step_dir / SCREENSHOT_FILENAME
    return Step(
        index=action.step_index,
        ui_tree=ui_tree,
        action=action,
        screenshot_path=str(screenshot_path) if screenshot_path.exists() else None,
    )


def _list_step_dirs(steps_dir: Path) -> List[Path]:
    candidates = [entry for entry in steps_dir.iterdir() if entry.is_dir()]
    numeric_dirs = []
    for entry in candidates:
        try:
            numeric_dirs.append((int(entry.name), entry))
        except ValueError:
            continue
    return [entry for _, entry in sorted(numeric_dirs, key=lambda item: item[0])]


def load_trajectory(trajectory_dir: Path) -> Trajectory:
    task = load_task(trajectory_dir / TASK_FILENAME)
    steps_dir = trajectory_dir / STEPS_DIRNAME
    steps = [load_step(step_dir) for step_dir in _list_step_dirs(steps_dir)]
    result_path = trajectory_dir / RESULT_FILENAME
    result = load_result(result_path) if result_path.exists() else None
    final_screenshot = trajectory_dir / FINAL_SCREENSHOT_FILENAME
    trajectory_id = result.trajectory_id if result else trajectory_dir.name
    return Trajectory(
        trajectory_id=trajectory_id,
        task=task,
        steps=steps,
        result=result,
        final_screenshot_path=str(final_screenshot) if final_screenshot.exists() else None,
        root_dir=str(trajectory_dir),
    )


def save_trajectory(trajectory: Trajectory, trajectory_dir: Path) -> None:
    _dump_json(trajectory_dir / TASK_FILENAME, trajectory.task.to_dict())
    steps_dir = trajectory_dir / STEPS_DIRNAME
    steps_dir.mkdir(parents=True, exist_ok=True)
    for step in trajectory.steps:
        step_dir = steps_dir / f"{step.index:03d}"
        step_dir.mkdir(parents=True, exist_ok=True)
        _dump_json(step_dir / ACTION_FILENAME, step.action.to_dict())
        _dump_json(step_dir / UI_TREE_FILENAME, step.ui_tree)
    if trajectory.result is not None:
        _dump_json(trajectory_dir / RESULT_FILENAME, trajectory.result.to_dict())


def load_dataset_index(index_path: Path) -> DatasetIndex:
    return DatasetIndex.from_dict(_load_json(index_path))
