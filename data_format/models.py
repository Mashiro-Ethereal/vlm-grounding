from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _split_extra(data: Dict[str, Any], known_fields: List[str]) -> Dict[str, Any]:
    return {key: value for key, value in data.items() if key not in known_fields}


@dataclass(frozen=True)
class Task:
    task_id: str
    instruction: str
    osworld_task_id: Optional[str] = None
    application: Optional[str] = None
    difficulty: Optional[str] = None
    expected_steps: Optional[int] = None
    success_criteria: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        known = [
            "task_id",
            "instruction",
            "osworld_task_id",
            "application",
            "difficulty",
            "expected_steps",
            "success_criteria",
        ]
        extra = _split_extra(data, known)
        return cls(
            task_id=data["task_id"],
            instruction=data["instruction"],
            osworld_task_id=data.get("osworld_task_id"),
            application=data.get("application"),
            difficulty=data.get("difficulty"),
            expected_steps=data.get("expected_steps"),
            success_criteria=data.get("success_criteria"),
            extra=extra,
        )

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "task_id": self.task_id,
            "instruction": self.instruction,
        }
        if self.osworld_task_id is not None:
            data["osworld_task_id"] = self.osworld_task_id
        if self.application is not None:
            data["application"] = self.application
        if self.difficulty is not None:
            data["difficulty"] = self.difficulty
        if self.expected_steps is not None:
            data["expected_steps"] = self.expected_steps
        if self.success_criteria is not None:
            data["success_criteria"] = self.success_criteria
        data.update(self.extra)
        return data


@dataclass(frozen=True)
class Action:
    step_index: int
    action_type: str
    parameters: Dict[str, Any]
    target_element: Optional[Dict[str, Any]] = None
    reasoning: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Action":
        known = ["step_index", "action_type", "parameters", "target_element", "reasoning"]
        extra = _split_extra(data, known)
        return cls(
            step_index=data["step_index"],
            action_type=data["action_type"],
            parameters=data.get("parameters", {}),
            target_element=data.get("target_element"),
            reasoning=data.get("reasoning"),
            extra=extra,
        )

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "step_index": self.step_index,
            "action_type": self.action_type,
            "parameters": self.parameters,
        }
        if self.target_element is not None:
            data["target_element"] = self.target_element
        if self.reasoning is not None:
            data["reasoning"] = self.reasoning
        data.update(self.extra)
        return data


@dataclass(frozen=True)
class Step:
    index: int
    ui_tree: Dict[str, Any]
    action: Action
    screenshot_path: Optional[str] = None


@dataclass(frozen=True)
class Result:
    trajectory_id: str
    success: bool
    total_steps: int
    completion_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    model_info: Optional[Dict[str, Any]] = None
    evaluation: Optional[Dict[str, Any]] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Result":
        known = [
            "trajectory_id",
            "success",
            "total_steps",
            "completion_time_ms",
            "error_message",
            "model_info",
            "evaluation",
        ]
        extra = _split_extra(data, known)
        return cls(
            trajectory_id=data["trajectory_id"],
            success=bool(data["success"]),
            total_steps=int(data["total_steps"]),
            completion_time_ms=data.get("completion_time_ms"),
            error_message=data.get("error_message"),
            model_info=data.get("model_info"),
            evaluation=data.get("evaluation"),
            extra=extra,
        )

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "trajectory_id": self.trajectory_id,
            "success": self.success,
            "total_steps": self.total_steps,
        }
        if self.completion_time_ms is not None:
            data["completion_time_ms"] = self.completion_time_ms
        if self.error_message is not None:
            data["error_message"] = self.error_message
        if self.model_info is not None:
            data["model_info"] = self.model_info
        if self.evaluation is not None:
            data["evaluation"] = self.evaluation
        data.update(self.extra)
        return data


@dataclass(frozen=True)
class Trajectory:
    trajectory_id: str
    task: Task
    steps: List[Step]
    result: Optional[Result] = None
    final_screenshot_path: Optional[str] = None
    root_dir: Optional[str] = None


@dataclass(frozen=True)
class DatasetIndexEntry:
    id: str
    task_id: str
    success: bool
    steps: int
    application: Optional[str] = None
    model: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DatasetIndexEntry":
        known = ["id", "task_id", "success", "steps", "application", "model"]
        extra = _split_extra(data, known)
        return cls(
            id=data["id"],
            task_id=data["task_id"],
            success=bool(data["success"]),
            steps=int(data["steps"]),
            application=data.get("application"),
            model=data.get("model"),
            extra=extra,
        )

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "id": self.id,
            "task_id": self.task_id,
            "success": self.success,
            "steps": self.steps,
        }
        if self.application is not None:
            data["application"] = self.application
        if self.model is not None:
            data["model"] = self.model
        data.update(self.extra)
        return data


@dataclass(frozen=True)
class DatasetIndex:
    version: str
    trajectories: List[DatasetIndexEntry]
    total_trajectories: Optional[int] = None
    successful: Optional[int] = None
    failed: Optional[int] = None
    created_at: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DatasetIndex":
        known = ["version", "trajectories", "total_trajectories", "successful", "failed", "created_at"]
        extra = _split_extra(data, known)
        trajectories = [DatasetIndexEntry.from_dict(item) for item in data.get("trajectories", [])]
        return cls(
            version=data["version"],
            trajectories=trajectories,
            total_trajectories=data.get("total_trajectories"),
            successful=data.get("successful"),
            failed=data.get("failed"),
            created_at=data.get("created_at"),
            extra=extra,
        )

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "version": self.version,
            "trajectories": [entry.to_dict() for entry in self.trajectories],
        }
        if self.created_at is not None:
            data["created_at"] = self.created_at
        if self.total_trajectories is not None:
            data["total_trajectories"] = self.total_trajectories
        if self.successful is not None:
            data["successful"] = self.successful
        if self.failed is not None:
            data["failed"] = self.failed
        data.update(self.extra)
        return data
