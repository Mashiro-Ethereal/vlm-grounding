"""Path utilities for trajectory data format.

This module provides helper functions for building paths to various files
and directories within the trajectory data structure.
"""

from __future__ import annotations

from pathlib import Path

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

# Dataset-level paths


def trajectories_dir(dataset_dir: Path) -> Path:
    """Return the trajectories directory within a dataset."""
    return dataset_dir / "trajectories"


def dataset_index_path(dataset_dir: Path) -> Path:
    """Return the index.json path within a dataset."""
    return dataset_dir / "index.json"


def dataset_metadata_path(dataset_dir: Path) -> Path:
    """Return the metadata.json path within a dataset."""
    return dataset_dir / METADATA_FILENAME


# Trajectory-level paths


def task_path(trajectory_dir: Path) -> Path:
    """Return the task.json path within a trajectory."""
    return trajectory_dir / TASK_FILENAME


def steps_dir(trajectory_dir: Path) -> Path:
    """Return the steps directory within a trajectory."""
    return trajectory_dir / STEPS_DIRNAME


def result_path(trajectory_dir: Path) -> Path:
    """Return the result.json path within a trajectory."""
    return trajectory_dir / RESULT_FILENAME


def final_screenshot_path(trajectory_dir: Path) -> Path:
    """Return the final_screenshot.png path within a trajectory."""
    return trajectory_dir / FINAL_SCREENSHOT_FILENAME


# Step-level paths


def step_dir(trajectory_dir: Path, step_index: int) -> Path:
    """Return the directory for a specific step."""
    return steps_dir(trajectory_dir) / f"{step_index:03d}"


def action_path(step_directory: Path) -> Path:
    """Return the action.json path within a step directory."""
    return step_directory / ACTION_FILENAME


def ui_tree_path(step_directory: Path) -> Path:
    """Return the ui_tree.json path within a step directory."""
    return step_directory / UI_TREE_FILENAME


def screenshot_path(step_directory: Path) -> Path:
    """Return the screenshot.png path within a step directory."""
    return step_directory / SCREENSHOT_FILENAME
