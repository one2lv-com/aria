"""
Swarm Coordinator — orchestrates multiple agents on complex tasks.
Splits a goal into sub-tasks, runs them in parallel, then synthesizes results.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.llm_tool import LLMTool
from tools.swarm_tool import SwarmTool


class SwarmCoordinator:
    """High-level coordinator: decompose → spawn → synthesize."""

    def __init__(self):
        self.llm = LLMTool()
        self.swarm = SwarmTool()

    def decompose(self, goal: str, model: str = "flash") -> list:
        """Ask the LLM to break a goal into parallel sub-tasks."""
        prompt = (
            f"You are a task decomposer. Break the following goal into 3-5 independent sub-tasks "
            f"that can be executed in parallel. Return ONLY a JSON array of strings.\n\nGoal: {goal}"
        )
        result = self.llm.chat([{"role": "user", "content": prompt}], model=model)
        if result["error"]:
            return [goal]
        import json, re
        match = re.search(r"\[.*\]", result["content"], re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
        return [goal]

    def synthesize(self, goal: str, sub_results: list, model: str = "kimi") -> str:
        """Combine sub-agent results into a final coherent answer."""
        numbered = "\n".join(f"{i+1}. {r.get('result', '[no result]')}" for i, r in enumerate(sub_results))
        prompt = (
            f"You are a synthesis agent. Given the original goal and results from parallel sub-agents, "
            f"produce a single coherent final answer.\n\nGoal: {goal}\n\nSub-agent results:\n{numbered}"
        )
        result = self.llm.chat([{"role": "user", "content": prompt}], model=model, max_tokens=8192)
        return result.get("content", "[synthesis failed]")

    def run(self, goal: str, decompose_model: str = "flash", execute_model: str = "flash",
            synthesize_model: str = "kimi") -> dict:
        """Full swarm pipeline: decompose → execute in parallel → synthesize."""
        tasks = self.decompose(goal, model=decompose_model)
        swarm_result = self.swarm.spawn(tasks, model=execute_model)
        sub_results = swarm_result.get("results", [])
        final = self.synthesize(goal, sub_results, model=synthesize_model)
        return {
            "goal": goal,
            "tasks": tasks,
            "sub_results": sub_results,
            "final": final,
        }
