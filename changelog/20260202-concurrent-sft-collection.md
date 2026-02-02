# Concurrent SFT Data Collection

## Added
- `scripts/collect_sft_data_concurrent.py` - Concurrent SFT data collection script
  - Supports multiple container workers for parallel collection
  - Includes 100 general website task definitions (news, search engines, tech docs, dev tools, education, productivity, design, utilities)
  - Thread-safe logging and progress tracking
  - Automatic container runtime detection (docker/podman)
- `scripts/start_workers.sh` - Helper script to start multiple osworld container workers
- `scripts/stop_workers.sh` - Helper script to stop container workers

dataset is collected at dataset/sft_100
