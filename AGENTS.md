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

## Data Format (see `data_format/SPEC.md`)

```
dataset/trajectories/{id}/
├── task.json
├── steps/{NNN}/ (screenshot.png, ui_tree.json, action.json)
├── result.json
└── final_screenshot.png
```

## Container Images (`image/`)

Build and run the desktop container with Chromium and DOM API.

**Container Runtime:** Auto-detect `docker` or `podman` on host (prefer `podman` if both exist).

```bash
# Detect runtime
RUNTIME=$(command -v podman 2>/dev/null || command -v docker 2>/dev/null)

# Build base image first
$RUNTIME build -t localhost/desktopd:latest references/desktopd/

# Build osworld image
$RUNTIME build -t localhost/osworld-desktopd:latest image/

# Run container
$RUNTIME run -d --name osworld -p 8080:8080 -p 8122:8122 localhost/osworld-desktopd:latest
```

**Ports:**
- `8080` - desktopd API (screenshot, keyboard, tablet input)
- `8122` - Chromium DOM API (accessibility tree)

## References

- [`references/desktopd`](references/desktopd) - Original desktopd project (git submodule from https://github.com/AFK-surf/desktopd)
