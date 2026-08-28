import os
import json
import threading
import queue
import requests
from datetime import datetime

API_BASE = "https://integrate.api.nvidia.com/v1"


def _call_llm(api_key: str, model_id: str, messages: list, result_queue: queue.Queue, agent_id: str):
    """Worker function for a swarm agent thread."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "model": model_id,
        "messages": messages,
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 4096,
        "stream": False,
    }
    try:
        resp = requests.post(f"{API_BASE}/chat/completions", headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        result_queue.put({"agent_id": agent_id, "result": content, "error": None})
    except Exception as e:
        result_queue.put({"agent_id": agent_id, "result": None, "error": str(e)})


class SwarmTool:
    """Coordinate multiple LLM sub-agents running in parallel."""

    name = "swarm"
    description = "Spawn parallel LLM agents for distributed task execution"

    MODELS = {
        "flash": "stepfun-ai/step-3.5-flash",
        "kimi": "moonshotai/kimi-k2-instruct-0905",
    }

    def __init__(self):
        self.api_key = os.environ.get("NVIDIA_API_KEY", "")
        self._results: dict = {}

    def spawn(self, tasks: list, model: str = "flash", system_prompt: str = None) -> dict:
        """
        Spawn one agent per task and run in parallel.

        tasks: list of str (one prompt per agent)
        Returns: list of results in same order as tasks
        """
        result_queue = queue.Queue()
        threads = []
        model_id = self.MODELS.get(model, model)

        for i, task in enumerate(tasks):
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": task})

            t = threading.Thread(
                target=_call_llm,
                args=(self.api_key, model_id, messages, result_queue, f"agent_{i}"),
                daemon=True,
            )
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=130)

        raw_results = {}
        while not result_queue.empty():
            r = result_queue.get()
            raw_results[r["agent_id"]] = r

        ordered = [raw_results.get(f"agent_{i}", {"result": None, "error": "timeout"}) for i in range(len(tasks))]
        self._results = {f"task_{i}": ordered[i] for i in range(len(tasks))}

        return {"results": ordered, "count": len(ordered), "error": None}

    def broadcast(self, prompt: str, models: list = None, count: int = 3) -> dict:
        """Send same prompt to N agents (for consensus / best-of-N)."""
        if models is None:
            models = ["flash"] * count

        tasks = [prompt] * len(models)
        return self.spawn(tasks, model=models[0])

    def gather(self) -> dict:
        """Return last swarm results."""
        return {"results": self._results, "error": None}
