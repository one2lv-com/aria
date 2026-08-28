import subprocess
import shlex
import os

class ShellTool:
    """Execute shell commands in a controlled environment."""

    name = "shell"
    description = "Run terminal/bash commands and return output"

    BLOCKED = ["rm -rf /", ":(){ :|:& };:", "mkfs", "dd if="]

    def run(self, command: str, timeout: int = 30, cwd: str = None) -> dict:
        for blocked in self.BLOCKED:
            if blocked in command:
                return {"error": f"Blocked dangerous command: {blocked}", "stdout": "", "stderr": "", "code": -1}

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd or os.getcwd(),
            )
            return {
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "code": result.returncode,
                "error": None,
            }
        except subprocess.TimeoutExpired:
            return {"error": f"Command timed out after {timeout}s", "stdout": "", "stderr": "", "code": -1}
        except Exception as e:
            return {"error": str(e), "stdout": "", "stderr": "", "code": -1}
