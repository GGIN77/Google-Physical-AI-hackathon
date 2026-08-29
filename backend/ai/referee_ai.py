import requests
import json
from ai.prompts import PROMPTS

def generate_commentary(game, event_log):
    prompt_template = PROMPTS.get(game, "Summarize the game telemetry.")
    recent_log = event_log[-200:]  # Limit to last 200 samples for low latency

    full_prompt = f"{prompt_template}\n\nMatch Data:\n{json.dumps(recent_log)}"

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "gemma2:2b", "prompt": full_prompt, "stream": False},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("response", "No commentary generated.")
        return f"Ollama Error: Status {response.status_code}"
    except Exception as e:
        return f"Local AI Error: Could not connect to Ollama. ({e})"