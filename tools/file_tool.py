import os
import glob as _glob

class FileTool:
    """Read, write, list, and search files."""

    name = "file"
    description = "File operations: read, write, append, list, search, delete"

    def read(self, path: str) -> dict:
        try:
            with open(os.path.expanduser(path), "r", encoding="utf-8") as f:
                return {"content": f.read(), "error": None}
        except Exception as e:
            return {"content": "", "error": str(e)}

    def write(self, path: str, content: str) -> dict:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(os.path.expanduser(path))), exist_ok=True)
            with open(os.path.expanduser(path), "w", encoding="utf-8") as f:
                f.write(content)
            return {"success": True, "error": None}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def append(self, path: str, content: str) -> dict:
        try:
            with open(os.path.expanduser(path), "a", encoding="utf-8") as f:
                f.write(content)
            return {"success": True, "error": None}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list(self, pattern: str = "*", directory: str = ".") -> dict:
        try:
            full = os.path.join(os.path.expanduser(directory), pattern)
            files = _glob.glob(full, recursive=True)
            return {"files": files, "error": None}
        except Exception as e:
            return {"files": [], "error": str(e)}

    def search(self, path: str, query: str) -> dict:
        try:
            results = []
            with open(os.path.expanduser(path), "r", encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    if query.lower() in line.lower():
                        results.append({"line": i, "content": line.rstrip()})
            return {"results": results, "error": None}
        except Exception as e:
            return {"results": [], "error": str(e)}

    def delete(self, path: str) -> dict:
        try:
            os.remove(os.path.expanduser(path))
            return {"success": True, "error": None}
        except Exception as e:
            return {"success": False, "error": str(e)}
