# OSWorld Desktop Image

Extended desktop container image with Chromium DOM API access for UI automation and training data collection.

## Overview

This image extends `desktopd` to provide programmatic access to Chromium's DOM and accessibility trees via an HTTP API. It enables agents to inspect web page structure without relying solely on screenshots.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Container                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐  │
│  │   Sway      │    │  Chromium   │    │ chromium_with   │  │
│  │ (Wayland)   │◄───│  Browser    │◄───│ _api.py         │  │
│  └─────────────┘    └──────┬──────┘    └────────┬────────┘  │
│                            │ CDP                │ HTTP      │
│                            │ :9222              │ :8122     │
│                            ▼                    ▼           │
│                     Chrome DevTools        REST API         │
│                       Protocol            (JSON output)     │
└─────────────────────────────────────────────────────────────┘
```

### Components

| Component | Port | Purpose |
|-----------|------|---------|
| desktopd | 8080 | Desktop automation (screenshots, input, window tree) |
| Chromium CDP | 9222 | Chrome DevTools Protocol (internal) |
| DOM API | 8122 | HTTP API for DOM/accessibility trees |

## Usage

### Building the Image

```bash
# Ensure base image exists
podman build -t localhost/desktopd:latest /path/to/desktopd

# Build this image
podman build -t localhost/osworld-desktopd:latest .
```

### Running the Container

```bash
podman run -d \
  -p 8080:8080 \
  -p 8122:8122 \
  localhost/osworld-desktopd:latest
```

### Starting Chromium with API

Inside the container (or via desktopd's execute endpoint):

```bash
# Launch with blank page
/chromium_with_api.py &

# Launch with specific URL
/chromium_with_api.py https://example.com &

# Launch with multiple URLs (opens as tabs)
/chromium_with_api.py https://example.com https://google.com &
```

### API Endpoints

#### `GET /` or `GET /layout`

Returns the layout/accessibility tree for all open tabs, including element coordinates and viewport information.

**Response:**
```json
{
  "tabs": [
    {
      "id": "ABC123",
      "url": "https://example.com",
      "title": "Example Domain",
      "layout": {
        "viewport": {
          "visualViewport": {"x": 0, "y": 0, "width": 1920, "height": 1080, "scale": 1},
          "layoutViewport": {"x": 0, "y": 0, "width": 1920, "height": 1080},
          "contentSize": {"width": 1920, "height": 2500}
        },
        "nodes": [
          {
            "nodeId": "1",
            "role": {"type": "role", "value": "RootWebArea"},
            "name": {"type": "computedString", "value": "Example Domain"},
            "childIds": ["2", "3"],
            "backendDOMNodeId": 1,
            "bounds": {"x": 0, "y": 0, "width": 1920, "height": 2500}
          },
          {
            "nodeId": "2",
            "role": {"type": "role", "value": "button"},
            "name": {"type": "computedString", "value": "Submit"},
            "backendDOMNodeId": 42,
            "bounds": {
              "x": 100, "y": 200, "width": 80, "height": 32,
              "borderBox": {"x": 98, "y": 198, "width": 84, "height": 36}
            }
          }
        ]
      }
    }
  ]
}
```

**Coordinate System:**
- All coordinates are in CSS pixels relative to the document origin (top-left)
- `bounds.x/y/width/height` - Content box (innermost, excludes padding/border)
- `bounds.borderBox` - Border box (includes padding and border, excludes margin)
- To convert document coordinates to screen coordinates, subtract `viewport.visualViewport.x/y`

See [`layout_schema.jsonc`](./layout_schema.jsonc) for the complete JSON schema documenting all fields in the accessibility tree and DOM fallback responses.

#### `GET /targets` or `GET /tabs`

Lists all CDP debugging targets (pages, service workers, etc.).

**Response:**
```json
[
  {
    "id": "ABC123",
    "type": "page",
    "title": "Example Domain",
    "url": "https://example.com",
    "webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/page/ABC123"
  }
]
```

#### `GET /health`

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "chromium_pid": 1234
}
```

## Implementation Details

### chromium_with_api.py

The script performs three functions:

1. **Chromium Launch**: Starts Chromium with remote debugging enabled via `--remote-debugging-port=9222`. Additional flags disable sandboxing (required in containers) and first-run dialogs.

2. **CDP Communication**: Uses the Chrome DevTools Protocol to:
   - List open tabs via `GET http://127.0.0.1:9222/json`
   - Connect to each tab's WebSocket endpoint
   - Execute `Accessibility.getFullAXTree` for the accessibility tree
   - Falls back to `DOM.getDocument` if accessibility unavailable

3. **HTTP Server**: Exposes results on port 8122 as JSON. The server runs in a daemon thread while the main thread monitors Chromium's lifecycle.

### CDP Methods Used

| Method | Purpose |
|--------|---------|
| `DOM.enable` | Enable DOM domain events |
| `DOM.getDocument` | Get DOM tree with specified depth (fallback) |
| `DOM.getBoxModel` | Get bounding box for a DOM node |
| `Accessibility.enable` | Enable accessibility domain |
| `Accessibility.getFullAXTree` | Get complete accessibility tree |
| `Page.enable` | Enable page domain events |
| `Page.getLayoutMetrics` | Get viewport and content size metrics |

### Chromium Flags

```
--disable-seccomp-filter-sandbox  # Required for containerized execution
--test-type                       # Suppress test automation banner
--remote-debugging-port=9222      # Enable CDP
--remote-allow-origins=*          # Allow WebSocket connections from any origin
--no-first-run                    # Skip first-run wizard
--no-default-browser-check        # Skip default browser prompt
--disable-background-networking   # Reduce background activity
--disable-sync                    # Disable account sync
--disable-translate               # Disable translation prompts
--metrics-recording-only          # Disable metrics upload
```

## Integration with desktopd

The DOM API complements desktopd's existing capabilities:

| Task | Tool |
|------|------|
| Visual observation | desktopd `/api/v1/screenshot` |
| Keyboard input | desktopd `/api/v1/keyboard` |
| Mouse/touch input | desktopd `/api/v1/tablet` |
| Window management | desktopd `/api/v1/tree` |
| DOM inspection | DOM API `/layout` |
| Element enumeration | DOM API `/layout` |

### Example Workflow

```python
import requests

DESKTOPD = "http://localhost:8080/api/v1"
DOM_API = "http://localhost:8122"

# Get accessibility tree with coordinates
layout = requests.get(f"{DOM_API}/layout").json()

# Find a button by its accessible name and click it
for tab in layout["tabs"]:
    viewport = tab["layout"].get("viewport", {})
    scroll_x = viewport.get("visualViewport", {}).get("x", 0)
    scroll_y = viewport.get("visualViewport", {}).get("y", 0)

    for node in tab["layout"].get("nodes", []):
        if node.get("role", {}).get("value") == "button":
            name = node.get("name", {}).get("value", "")
            if "Submit" in name and "bounds" in node:
                bounds = node["bounds"]
                # Calculate center point in screen coordinates
                center_x = bounds["x"] + bounds["width"] / 2 - scroll_x
                center_y = bounds["y"] + bounds["height"] / 2 - scroll_y

                # Click via desktopd tablet API
                requests.post(f"{DESKTOPD}/tablet", json={
                    "x": center_x,
                    "y": center_y,
                    "action": "tap"
                })
                break

# Take screenshot for verification
screenshot = requests.get(f"{DESKTOPD}/screenshot")
```

## Limitations

- **Single browser instance**: The script manages one Chromium process. For multiple isolated browsers, run multiple containers.
- **No cross-origin iframes**: CDP's `pierce: true` attempts to access iframes, but cross-origin restrictions may limit visibility.
- **Hidden elements**: Elements with `display: none` or zero dimensions will not have `bounds` in the response.
- **WebSocket per request**: Each API call creates new WebSocket connections. For high-frequency polling, consider implementing connection pooling.
