import os
import requests
import json

class LLMTool:
    def __init__(self):
        self.api_key = os.environ.get('NVIDIA_API_KEY', '')
        self.url = "https://integrate.api.nvidia.com/v1/chat/completions"

    def chat(self, messages, model="meta/llama-3.1-405b-instruct"):
        if not self.api_key:
            return {"error": "NVIDIA_API_KEY not set"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "top_p": 0.95,
            "max_tokens": 4096,
            "stream": False
        }

        try:
            response = requests.post(self.url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            return {"content": result['choices'][0]['message']['content']}
        except Exception as e:
            return {"error": str(e)}

    def stream_chat(self, messages, model="meta/llama-3.1-405b-instruct"):
        # Simplified streaming implementation for the app
        result = self.chat(messages, model)
        if "error" in result:
            yield f"[Error: {result['error']}]"
        else:
            # Chunking for the UI effect
            text = result["content"]
            for i in range(0, len(text), 10):
                yield text[i:i+10]
