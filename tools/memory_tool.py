import os
import re
from datetime import datetime

MEMORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory.md")


class MemoryTool:
    """Read and write agent memory stored in memory.md."""

    name = "memory"
    description = "Persistent memory: read, write, search, append to memory.md"

    def read(self, section: str = None) -> dict:
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                content = f.read()
            if section:
                pattern = rf"## {re.escape(section)}\n(.*?)(?=\n## |\Z)"
                match = re.search(pattern, content, re.DOTALL)
                return {"content": match.group(1).strip() if match else "", "error": None}
            return {"content": content, "error": None}
        except Exception as e:
            return {"content": "", "error": str(e)}

    def write_section(self, section: str, content: str) -> dict:
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                full = f.read()

            pattern = rf"(## {re.escape(section)}\n).*?(?=\n## |\Z)"
            replacement = f"## {section}\n{content}\n"

            if re.search(pattern, full, re.DOTALL):
                updated = re.sub(pattern, replacement, full, flags=re.DOTALL)
            else:
                updated = full.rstrip() + f"\n\n## {section}\n{content}\n"

            with open(MEMORY_FILE, "w", encoding="utf-8") as f:
                f.write(updated)
            return {"success": True, "error": None}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def append_to_section(self, section: str, content: str) -> dict:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        return self.write_section(section, f"{self.read(section)['content']}\n- [{timestamp}] {content}")

    def search(self, query: str) -> dict:
        try:
            results = []
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    if query.lower() in line.lower():
                        results.append({"line": i, "content": line.strip()})
            return {"results": results, "error": None}
        except Exception as e:
            return {"results": [], "error": str(e)}

    def log_session(self, entry: str) -> dict:
        return self.append_to_section("Session Log", entry)
