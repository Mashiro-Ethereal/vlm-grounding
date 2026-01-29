import tempfile
import unittest
from pathlib import Path

from data_format import (
    Action,
    Result,
    Step,
    Task,
    Trajectory,
    iter_sft_samples,
    load_trajectory,
    save_trajectory,
    validate_trajectory_dir,
)


class TestDataFormat(unittest.TestCase):
    def test_load_trajectory_example(self) -> None:
        trajectory_dir = Path("data_format/examples/traj_chrome_001")
        trajectory = load_trajectory(trajectory_dir)

        self.assertEqual(trajectory.trajectory_id, "traj_chrome_001")
        self.assertEqual(trajectory.task.task_id, "chrome_open_google")
        self.assertEqual(len(trajectory.steps), 4)

        indices = [step.index for step in trajectory.steps]
        self.assertEqual(indices, [0, 1, 2, 3])

        for step in trajectory.steps:
            self.assertIsNotNone(step.action.action_type)
            self.assertIsNotNone(step.screenshot_path)
            self.assertTrue(Path(step.screenshot_path).exists())

    def test_iter_sft_samples_history(self) -> None:
        task = Task(task_id="t1", instruction="Do something")
        steps = [
            Step(
                index=0,
                ui_tree={"root": {"id": "node_0"}},
                action=Action(step_index=0, action_type="click", parameters={"x": 1, "y": 2}),
            ),
            Step(
                index=1,
                ui_tree={"root": {"id": "node_1"}},
                action=Action(step_index=1, action_type="type", parameters={"text": "hi"}),
            ),
        ]
        trajectory = Trajectory(trajectory_id="traj_1", task=task, steps=steps)

        samples = list(iter_sft_samples(trajectory))
        self.assertEqual(len(samples), 2)
        self.assertEqual(samples[0]["input"]["history"], [])
        self.assertEqual(len(samples[1]["input"]["history"]), 1)
        self.assertEqual(samples[1]["input"]["history"][0]["action_type"], "click")

    def test_validate_trajectory_dir_warnings(self) -> None:
        trajectory_dir = Path("data_format/examples/traj_chrome_001")
        issues = validate_trajectory_dir(trajectory_dir)

        self.assertTrue(any(issue.severity == "warning" for issue in issues))
        self.assertFalse(any(issue.severity == "error" for issue in issues))

    def test_save_and_reload(self) -> None:
        task = Task(task_id="t2", instruction="Open app", application="demo")
        steps = [
            Step(
                index=0,
                ui_tree={"root": {"id": "node_0"}},
                action=Action(step_index=0, action_type="wait", parameters={"seconds": 1}),
            )
        ]
        result = Result(trajectory_id="traj_demo", success=True, total_steps=1)
        trajectory = Trajectory(trajectory_id="traj_demo", task=task, steps=steps, result=result)

        with tempfile.TemporaryDirectory() as tmp_dir:
            target_dir = Path(tmp_dir) / "traj_demo"
            save_trajectory(trajectory, target_dir)
            reloaded = load_trajectory(target_dir)

        self.assertEqual(reloaded.task.task_id, "t2")
        self.assertEqual(reloaded.steps[0].action.action_type, "wait")
        self.assertIsNotNone(reloaded.result)
        self.assertTrue(reloaded.result.success)


if __name__ == "__main__":
    unittest.main()
