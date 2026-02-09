# osworld-desktopd

## Data format module

This repo includes a small Python module for working with the OSWorld-Desktopd dataset
layout described in `data_format/SPEC.md`.

Example usage:

```python
from pathlib import Path

from data_format import iter_sft_samples, load_trajectory, validate_trajectory_dir

trajectory = load_trajectory(Path("data_format/examples/traj_chrome_001"))
samples = list(iter_sft_samples(trajectory))
issues = validate_trajectory_dir(Path("data_format/examples/traj_chrome_001"))

print(len(samples))
print([issue.message for issue in issues])
```

Manual data lives in `data_format/examples` and the tests load it to make sure
the parsing utilities stay in sync with the spec.

CLI validation:

```bash
python3 -m data_format validate-trajectory data_format/examples/traj_chrome_001
python3 -m data_format validate-dataset /path/to/dataset
```

Run tests:

```bash
python3 -m unittest discover -s tests
```
## Post-processing

Extract data and crop images:
```bash
conda activate sft-ui
python batch_crop_images.py
```

Filter UI tree and draw bounding boxes:
```bash
conda activate sft-ui
python process_all_datasets.py
```
