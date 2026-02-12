import os
import json
import requests

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
MODEL = "tngtech/deepseek-r1t2-chimera:free"  # ou outro modelo DeepSeek disponível

class DeepSeekError(Exception):
    pass

def analyze_target_audience(text: str) -> dict:
    if not OPENROUTER_API_KEY:
        raise DeepSeekError("Defina a variável de ambiente OPENROUTER_API_KEY")

    messages = [
        {
            "role": "system",
            "content": "Você é um analista de editais. Responda apenas JSON com: { 'target_audience': string, 'notes': string }."
        },
        {
            "role": "user",
            "content": f"Texto do edital:\n{text}"
        }
    ]

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        # Opcional para ranking no OpenRouter:
        # "HTTP-Referer": "http://localhost",
        # "X-Title": "iaupe-analyser",
    }
    body = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0,
        "max_tokens": 512,
    }

    try:
        resp = requests.post(OPENROUTER_API_URL, headers=headers, json=body, timeout=60)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise DeepSeekError(f"Falha ao chamar OpenRouter: {e}") from e

    data = resp.json()
    output = data.get("choices", [{}])[0].get("message", {}).get("content", "")

    try:
        return json.loads(output)
    except Exception:
        return {"target_audience": "", "notes": output}