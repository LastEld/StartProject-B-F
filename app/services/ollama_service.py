import httpx
import json
from typing import List, Dict, Any, Optional
from app.core.settings import settings
import logging

logger = logging.getLogger(__name__)

class SimpleChatMessage:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

async def get_ollama_response(project_id: int, user_prompt: str, chat_history: List[SimpleChatMessage], model_name: str = "llama3") -> str:
    # Sends a prompt and chat history to Ollama and returns the AI response.
    ollama_url = f"{settings.OLLAMA_BASE_URL}/api/chat"
    messages = []
    for msg in chat_history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": user_prompt})
    payload = {
        "model": model_name,
        "messages": messages,
        "stream": False
    }
    timeout_config = httpx.Timeout(10.0, read=60.0)
    async with httpx.AsyncClient(timeout=timeout_config) as client:
        try:
            logger.info(f"Sending request to Ollama: {ollama_url} with model {model_name} for project {project_id}")
            response = await client.post(ollama_url, json=payload)
            response.raise_for_status()
            response_data = response.json()
            if response_data.get("message") and response_data["message"].get("content"):
                ai_content = response_data["message"]["content"]
                logger.info(f"Received response from Ollama for project {project_id}")
                return ai_content.strip()
            else:
                logger.error(f"Ollama response for project {project_id} missing expected content: {response_data}")
                return "Error: Jarvis received an unexpected response format from the AI."
        except httpx.TimeoutException:
            logger.error(f"Timeout while contacting Ollama for project {project_id} at {ollama_url}")
            return "Error: Jarvis timed out waiting for a response from the AI."
        except httpx.RequestError as e:
            logger.error(f"Request error while contacting Ollama for project {project_id}: {e}")
            return f"Error: Jarvis encountered a network issue trying to reach the AI: {e.__class__.__name__}."
        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON response from Ollama for project {project_id}. Response text: {response.text if \"response\" in locals() else \"Response object not available\"}")
            return "Error: Jarvis received an invalid response from the AI."
        except Exception as e:
            logger.error(f"An unexpected error occurred in get_ollama_response for project {project_id}: {e}", exc_info=True)
            return f"Error: An unexpected issue occurred with Jarvis: {e.__class__.__name__}."
