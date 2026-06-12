import logging
import sys
import os
import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests

# Настройка логирования
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

@app.post("/")
async def main(request: Request):
    try:
        # 1. Получаем и логируем тело запроса (только один раз!)
        body_raw = await request.body()
        logger.error(f"=REQ====================\n{body_raw.decode()}\n====================")
        
        # Парсим JSON
        body = json.loads(body_raw)
        
        # 2. Извлекаем текст пользователя
        user_text = body["request"]["original_utterance"]
        if not user_text:
            user_text = "Привет"
        
        # 3. Проверяем, есть ли API-ключ
        if not DEEPSEEK_API_KEY:
            logger.error("DEEPSEEK_API_KEY не задан в переменных окружения")
            raise Exception("API ключ DeepSeek не настроен")
        
        # 4. Запрос к DeepSeek
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": user_text}],
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()  # вызовет исключение при HTTP ошибке
        
        # 5. Разбираем ответ DeepSeek
        deepseek_data = response.json()
        answer = deepseek_data["choices"][0]["message"]["content"]
        
        # 6. Формируем ответ для Алисы (обязательные поля)
        alice_response = {
            "version": body["version"],
            "session": body["session"],
            "response": {
                "text": answer,
                "tts": answer,          # <-- это поле важно для голоса
                "end_session": False
            }
        }
        
        logger.error(f"Ответ Алисе: {json.dumps(alice_response, ensure_ascii=False)}")
        return JSONResponse(content=alice_response)
    
    except Exception as e:
        logger.exception("Ошибка в обработчике")
        # Возвращаем понятную ошибку, чтобы Алиса не молчала
        error_response = {
            "version": body.get("version", "1.0") if 'body' in locals() else "1.0",
            "session": body.get("session", {}) if 'body' in locals() else {},
            "response": {
                "text": "Извините, произошла техническая ошибка. Попробуйте позже.",
                "tts": "Извините, произошла ошибка.",
                "end_session": False
            }
        }
        return JSONResponse(content=error_response, status_code=200)  # 200, чтобы Алиса не ругалась
