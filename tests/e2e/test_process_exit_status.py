import subprocess
import sys


def test_compile_process_returns_zero() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "compileall", "-q", "src", "tests"],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
