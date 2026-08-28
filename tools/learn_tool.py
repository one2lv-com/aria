import os
import re

BASE = os.path.dirname(os.path.dirname(__file__))
SKILLS_MD = os.path.join(BASE, "skills.md")
TOOLS_MD = os.path.join(BASE, "tools.md")
SKILLS_DIR = os.path.join(BASE, "skills")
TOOLS_DIR = os.path.join(BASE, "tools")


class LearnTool:
    """Dynamically add new skills and tools to the agent."""

    name = "learn"
    description = "Add new skills and tools at runtime"

    def add_skill(self, name: str, description: str, trigger: str, code: str = None) -> dict:
        """Register a new skill in skills.md and optionally write Python code."""
        try:
            entry = f"\n### {name}\n- **Description**: {description}\n- **Trigger**: {trigger}\n"
            with open(SKILLS_MD, "a", encoding="utf-8") as f:
                f.write(entry)

            if code:
                skill_path = os.path.join(SKILLS_DIR, f"{name.lower().replace(' ', '_')}.py")
                with open(skill_path, "w", encoding="utf-8") as f:
                    f.write(code)

            return {"success": True, "skill": name, "error": None}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def add_tool(self, name: str, description: str, code: str) -> dict:
        """Write a new tool Python file and register it in tools.md."""
        try:
            tool_path = os.path.join(TOOLS_DIR, f"{name.lower()}_tool.py")
            with open(tool_path, "w", encoding="utf-8") as f:
                f.write(code)

            entry = f"\n### {name}Tool\n- **Module**: tools/{name.lower()}_tool.py\n- **Description**: {description}\n"
            with open(TOOLS_MD, "a", encoding="utf-8") as f:
                f.write(entry)

            # Dynamically import and register
            import importlib.util
            spec = importlib.util.spec_from_file_location(f"tools.{name.lower()}_tool", tool_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            tool_class = getattr(mod, f"{name.capitalize()}Tool", None)
            if tool_class:
                from tools import register_tool
                register_tool(name.lower(), tool_class)

            return {"success": True, "tool": name, "path": tool_path, "error": None}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_skills(self) -> dict:
        try:
            with open(SKILLS_MD, "r", encoding="utf-8") as f:
                content = f.read()
            skills = re.findall(r"### (.+)", content)
            return {"skills": skills, "error": None}
        except Exception as e:
            return {"skills": [], "error": str(e)}

    def list_tools(self) -> dict:
        try:
            with open(TOOLS_MD, "r", encoding="utf-8") as f:
                content = f.read()
            tools = re.findall(r"### (.+)", content)
            return {"tools": tools, "error": None}
        except Exception as e:
            return {"tools": [], "error": str(e)}
