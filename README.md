# osworld-desktopd

## Data format module

This repo includes a small Python module for working with the OSWorld-Desktopd dataset
layout described in `data-format/SPEC.md`.

Example usage:

```python
from pathlib import Path

from data_format import iter_sft_samples, load_trajectory, validate_trajectory_dir

trajectory = load_trajectory(Path("data-format/examples/traj_chrome_001"))
samples = list(iter_sft_samples(trajectory))
issues = validate_trajectory_dir(Path("data-format/examples/traj_chrome_001"))

print(len(samples))
print([issue.message for issue in issues])
```

Manual data lives in `data-format/examples` and the tests load it to make sure
the parsing utilities stay in sync with the spec.

CLI validation:

```bash
python3 -m data_format validate-trajectory data-format/examples/traj_chrome_001
python3 -m data_format validate-dataset /path/to/dataset
```

Run tests:

```bash
python3 -m unittest discover -s tests
```
