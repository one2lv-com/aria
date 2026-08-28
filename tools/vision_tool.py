"""
VisionTool - Image Analysis using NVIDIA NIM Vision Models
Supports NVIDIA API Catalog endpoints with proper error handling.
"""

import os
import requests
import json
from typing import Dict, Any, Optional


class VisionTool:
    def __init__(self):
        self.api_key = os.environ.get('NVIDIA_API_KEY', '')
        # Use the standard NVIDIA NIM endpoint
        self.url = "https://integrate.api.nvidia.com/v1/chat/completions"
        # Default vision model from NVIDIA API Catalog
        self.default_model = "nvidia/phi-3-vision-instruct"
        # Alternative models available:
        # "microsoft/phi-3.5-vision-instruct"
        # "nvidia/nemotron-3b-vision"
        # "meta/llama-3.2-90b-vision-instruct"

    def analyze(self, image_url: str, query: str = "What is in this image?", 
                model: Optional[str] = None, temperature: float = 0.2,
                max_tokens: int = 1024) -> Dict[str, Any]:
        """
        Analyze an image using NVIDIA NIM vision model.
        
        Args:
            image_url: HTTPS URL to the image (publicly accessible)
            query: Question/prompt about the image
            model: Specific model to use (default: phi-3-vision)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum response tokens
            
        Returns:
            Dict with 'analysis' key containing the response, or 'error' key
        """
        if not self.api_key:
            return {"error": "NVIDIA_API_KEY not set. Set environment variable or pass --key to agent."}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        payload = {
            "model": model or self.default_model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": query},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            }],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }

        try:
            response = requests.post(
                self.url, 
                headers=headers, 
                json=payload, 
                timeout=60
            )
            
            if response.status_code == 401:
                return {"error": "Invalid API key. Check NVIDIA_API_KEY."}
            elif response.status_code == 404:
                return {"error": f"Model not found. Try a different model. Available: phi-3-vision, nemotron-3b-vision, llama-3.2-vision"}
            elif response.status_code == 400:
                return {"error": f"Bad request: {response.text[:200]}"}
            
            response.raise_for_status()
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message'].get('content', '')
                return {
                    "analysis": content,
                    "model": result.get('model', model or self.default_model),
                    "usage": result.get('usage', {})
                }
            else:
                return {"error": f"Unexpected response format: {result}"}
                
        except requests.exceptions.Timeout:
            return {"error": "Request timed out (60s). Image may be too large or server busy."}
        except requests.exceptions.ConnectionError:
            return {"error": "Connection failed. Check network/internet access."}
        except Exception as e:
            return {"error": f"Vision analysis failed: {str(e)}"}

    def analyze_local(self, image_path: str, query: str = "What is in this image?",
                      model: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze a local image file by uploading to a temporary host.
        Note: For production, you'd upload to your own storage (S3, GCS, etc.)
        This is a placeholder - local files need to be accessible via URL.
        """
        if not os.path.exists(image_path):
            return {"error": f"File not found: {image_path}"}
        
        # For Colab/local use, you'd need to upload the file first
        # This is a stub - implement based on your hosting
        return {
            "error": "Local file analysis requires uploading to a public URL first. "
                     "Use analyze() with an HTTPS URL. "
                     "For Colab: upload to Google Drive and use shareable link, "
                     "or use a temporary file host."
        }

    def list_models(self) -> Dict[str, Any]:
        """Return list of known vision models on NVIDIA NIM."""
        return {
            "models": [
                {"id": "nvidia/phi-3-vision-instruct", "name": "Phi-3 Vision", "context": "128k"},
                {"id": "microsoft/phi-3.5-vision-instruct", "name": "Phi-3.5 Vision", "context": "128k"},
                {"id": "nvidia/nemotron-3b-vision", "name": "Nemotron 3B Vision", "context": "4k"},
                {"id": "meta/llama-3.2-90b-vision-instruct", "name": "Llama 3.2 90B Vision", "context": "128k"},
                {"id": "nvidia/cosmos-1.0-vision", "name": "Cosmos Vision", "context": "8k"}
            ],
            "note": "Model availability depends on your NVIDIA API Catalog access."
        }
