from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .models import Action, DatasetIndex, Result, Step, Task, Trajectory
from . import paths


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
    action = load_action(paths.action_path(step_dir))
    ui_tree = _load_json(paths.ui_tree_path(step_dir))
    screenshot = paths.screenshot_path(step_dir)
    return Step(
        index=action.step_index,
        ui_tree=ui_tree,
        action=action,
        screenshot_path=str(screenshot) if screenshot.exists() else None,
    )


def _list_step_dirs(traj_steps_dir: Path) -> List[Path]:
    candidates = [entry for entry in traj_steps_dir.iterdir() if entry.is_dir()]
    numeric_dirs = []
    for entry in candidates:
        try:
            numeric_dirs.append((int(entry.name), entry))
        except ValueError:
            continue
    return [entry for _, entry in sorted(numeric_dirs, key=lambda item: item[0])]


def load_trajectory(trajectory_dir: Path) -> Trajectory:
    task = load_task(paths.task_path(trajectory_dir))
    traj_steps_dir = paths.steps_dir(trajectory_dir)
    steps = [load_step(step_dir) for step_dir in _list_step_dirs(traj_steps_dir)]
    result_file = paths.result_path(trajectory_dir)
    result = load_result(result_file) if result_file.exists() else None
    final_screenshot = paths.final_screenshot_path(trajectory_dir)
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
    _dump_json(paths.task_path(trajectory_dir), trajectory.task.to_dict())
    traj_steps_dir = paths.steps_dir(trajectory_dir)
    traj_steps_dir.mkdir(parents=True, exist_ok=True)
    for step in trajectory.steps:
        step_directory = paths.step_dir(trajectory_dir, step.index)
        step_directory.mkdir(parents=True, exist_ok=True)
        _dump_json(paths.action_path(step_directory), step.action.to_dict())
        _dump_json(paths.ui_tree_path(step_directory), step.ui_tree)
    if trajectory.result is not None:
        _dump_json(paths.result_path(trajectory_dir), trajectory.result.to_dict())


def load_dataset_index(index_path: Path) -> DatasetIndex:
    return DatasetIndex.from_dict(_load_json(index_path))
