import subprocess
import sys
import tempfile
import time
from pathlib import Path


def execute_python_code(code: str, test_code: str = "", timeout_seconds: int = 3) -> dict:
    """Run Python code with a short timeout for lightweight coding assessment.

    This is intentionally not a full online judge. It executes small educational
    snippets in a temporary file, captures output/errors, and stops long runs.
    """
    start = time.perf_counter()
    program = code
    if test_code:
        program = f"{code}\n\n{test_code}\nprint('All checks passed')\n"

    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "submission.py"
        path.write_text(program, encoding="utf-8")
        try:
            result = subprocess.run(
                [sys.executable, str(path)],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": "Execution timed out.",
                "execution_time": timeout_seconds,
            }

    elapsed = round(time.perf_counter() - start, 4)
    return {
        "success": result.returncode == 0,
        "output": result.stdout,
        "error": result.stderr,
        "execution_time": elapsed,
    }
