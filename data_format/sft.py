from __future__ import annotations

from typing import Dict, Iterable, List

from .models import Action, Trajectory


def _action_history(actions: List[Action]) -> List[Dict[str, object]]:
    return [action.to_dict() for action in actions]


def iter_sft_samples(trajectory: Trajectory) -> Iterable[Dict[str, object]]:
    history: List[Action] = []
    for step in trajectory.steps:
        sample = {
            "input": {
                "instruction": trajectory.task.instruction,
                "screenshot": step.screenshot_path,
                "ui_tree": step.ui_tree,
                "history": _action_history(history),
            },
            "output": {
                "action": step.action.to_dict(),
                "reasoning": step.action.reasoning,
            },
        }
        yield sample
        history.append(step.action)
