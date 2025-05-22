import subprocess
import sys
import pytest

pytest.importorskip("app.cli", reason="CLI module not yet implemented")


def test_cli_help():
    result = subprocess.run([sys.executable, "-m", "app.cli", "--help"], capture_output=True)
    assert result.returncode == 0
    assert b"Usage" in result.stdout or b"--help" in result.stdout 