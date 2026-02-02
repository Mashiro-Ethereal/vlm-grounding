# SFT Data Collection Infrastructure

## Changes

### Added
- `references/desktopd` - Git submodule for base desktop daemon
- `scripts/collect_sft_data.py` - Automated SFT data collection script
- `data_format/sft_examples/20260202/` - Initial 10 training samples

### Modified
- `image/chromium_with_api.py`
  - Auto-detect display platform (wayland/x11) from environment
  - Add `--no-sandbox` and `--ozone-platform` flags for container support
  - Add `--force-renderer-accessibility` for UI tree extraction
  - Add performance flags: `--enable-gpu-rasterization`, `--enable-zero-copy`
- `AGENTS.md`
  - Document container build/run instructions
  - Add docker/podman auto-detection snippet
  - Reference desktopd submodule
- `.gitignore`
  - Remove global `*.png` ignore to allow SFT screenshots

### Samples Collected
| Task ID | URL | Steps |
|---------|-----|-------|
| example_com_view | example.com | 1 |
| google_search_page | google.com | 1 |
| wikipedia_main | wikipedia.org | 1 |
| github_homepage | github.com | 1 |
| duckduckgo_search | duckduckgo.com | 1 |
| python_docs | docs.python.org | 1 |
| httpbin_get | httpbin.org | 1 |
| jsonplaceholder_api | jsonplaceholder.typicode.com | 1 |
| hn_frontpage | news.ycombinator.com | 1 |
| mdn_web_docs | developer.mozilla.org | 1 |

### Data Format
Each sample contains:
- `task.json` - Task instruction
- `steps/000/screenshot.png` - Pre-action screenshot (compressed with pngquant)
- `steps/000/ui_tree.json` - Accessibility tree from CDP
- `steps/000/action.json` - Action taken
- `final_screenshot.png` - Post-action screenshot
- `result.json` - Success/failure status
