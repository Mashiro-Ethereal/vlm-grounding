# OSWorld-Desktopd Agent Documentation

## Project Overview

Desktop daemon service and data format utilities for collecting SFT training data from desktop UI interactions.

## Server Scripts (`server/`)

### `server/main.py` (1797 lines)
Flask HTTP server for desktop automation. Cross-platform (Linux/Windows/macOS).

**Key Endpoints:**
- `/execute` POST - Execute shell commands
- `/screenshot` GET - Capture screen with cursor
- `/accessibility` GET - Get UI tree
- `/setup/launch` POST - Launch applications
- `/setup/upload` POST - Upload files
- `/setup/download_file` POST - Download files
- `/setup/activate_window` POST - Activate window
- `/setup/close_window` POST - Close window
- `/start_recording` POST - Start screen recording
- `/end_recording` POST - End screen recording
- `/run_python` POST - Execute Python code

**Platform imports:** Linux: `pyatspi`, Windows: `pywinauto`, macOS: `AppKit/Quartz`

### `server/pyxcursor.py` (148 lines)
X11 cursor capture using XFixes. Classes: `Xcursor` for cursor image extraction.

## Data Format Module (`data_format/`)

### `models.py` - Dataclasses: Task, Action, Step, Result, Trajectory, DatasetIndex
### `constants.py` - File constants: ACTION_FILENAME, SCREENSHOT_FILENAME, etc.
### `io.py` - I/O: load_trajectory(), save_trajectory(), load_dataset_index()
### `validation.py` - validate_trajectory_dir(), validate_dataset_dir()
### `sft.py` - iter_sft_samples() for SFT training data generation
### `cli.py` - CLI: `python -m data_format validate-trajectory <path>`

## Data Format (see `data-format/SPEC.md`)

```
dataset/trajectories/{id}/
├── task.json
├── steps/{NNN}/ (screenshot.png, ui_tree.json, action.json)
├── result.json
└── final_screenshot.png
```
