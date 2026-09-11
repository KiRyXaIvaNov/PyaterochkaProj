import httpx
import json
from typing import AsyncGenerator, Optional, Dict, Any

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:7b"

SYSTEM_PROMPT = """Ты — интеллектуальный ассистент технической поддержки ТПУ (Томского политехнического университета).
Твоя задача — помогать пользователям, используя предоставленный контекст из базы знаний.
Отвечай вежливо, точно и по делу. Если в контексте нет ответа на вопрос, честно скажи об этом и предложи обратиться к оператору."""

async def generate_answer(prompt: str, context: Optional[str] = None) -> str:
    """
    Отправляет одиночный запрос к Qwen2.5:7b и возвращает полный ответ.
    """
    full_prompt = f"Контекст из базы знаний:\n{context}\n\nВопрос пользователя: {prompt}" if context else prompt

    payload = {
        "model": MODEL_NAME,
        "prompt": full_prompt,
        "system": SYSTEM_PROMPT,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "top_p": 0.9
        }
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(OLLAMA_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "Ошибка: Получен пустой ответ от модели.")
        except httpx.HTTPError as e:
            return f"Ошибка при обращении к локальной модели Qwen: {str(e)}"

async def stream_answer(prompt: str, context: Optional[str] = None) -> AsyncGenerator[str, None]:
    """
    Потоковая генерация ответа (стриминг) для передачи на фронтенд в режиме реального времени.
    """
    full_prompt = f"Контекст из базы знаний:\n{context}\n\nВопрос пользователя: {prompt}" if context else prompt

    payload = {
        "model": MODEL_NAME,
        "prompt": full_prompt,
        "system": SYSTEM_PROMPT,
        "stream": True,
        "options": {
            "temperature": 0.2
        }
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            async with client.stream("POST", OLLAMA_URL, json=payload) as response:
                async for line in response.aiter_lines():
                    if line:
                        chunk = json.loads(line)
                        yield chunk.get("response", "")
        except httpx.HTTPError as e:
            yield f"[Ошибка потоковой передачи: {str(e)}]"