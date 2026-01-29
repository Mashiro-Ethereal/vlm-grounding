import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestDataFormatCLI(unittest.TestCase):
    def test_validate_trajectory_cli(self) -> None:
        command = [
            sys.executable,
            "-m",
            "data_format",
            "validate-trajectory",
            "data-format/examples/traj_chrome_001",
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)

        self.assertEqual(result.returncode, 0)
        self.assertIn("warning:", result.stdout)

    def test_validate_trajectory_cli_missing_path(self) -> None:
        command = [
            sys.executable,
            "-m",
            "data_format",
            "validate-trajectory",
            "data-format/examples/does_not_exist",
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)

        self.assertEqual(result.returncode, 2)
        self.assertIn("path does not exist", result.stdout)

    def test_validate_dataset_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            dataset_root = Path(tmp_dir) / "dataset"
            trajectories_dir = dataset_root / "trajectories"
            trajectories_dir.mkdir(parents=True)
            (trajectories_dir / "traj_001").mkdir()
            steps_dir = trajectories_dir / "traj_001" / "steps"
            steps_dir.mkdir()
            (steps_dir / "000").mkdir()
            (trajectories_dir / "traj_001" / "task.json").write_text(
                '{"task_id":"t1","instruction":"demo"}',
                encoding="utf-8",
            )

            command = [
                sys.executable,
                "-m",
                "data_format",
                "validate-dataset",
                str(dataset_root),
            ]
            result = subprocess.run(command, capture_output=True, text=True, check=False)

        self.assertEqual(result.returncode, 1)
        self.assertIn("warning:", result.stdout)
        self.assertIn("error:", result.stdout)


if __name__ == "__main__":
    unittest.main()
