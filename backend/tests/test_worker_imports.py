import os
import subprocess
import sys
from pathlib import Path


def test_worker_job_import_registers_related_models() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(backend_dir)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from sqlalchemy.orm import configure_mappers; "
            "from app.task_handlers.jobs import execute_task; "
            "configure_mappers(); "
            "print(execute_task.name)",
        ],
        cwd=backend_dir,
        env=env,
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "tasks.execute"
