import logging
import sys
import os
import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

@app.post("/")
async def main(request: Request):
    try:
        # Читаем тело запроса от Алисы
        body_raw = await request.body()
        body = json.loads(body_raw)
        logger.error(f"Запрос от Алисы: {json.dumps(body, ensure_ascii=False)}")
        
        user_text = body["request"]["original_utterance"]
        if not user_text:
            user_text = "Привет"
        
        # Проверяем наличие API-ключа
        if not DEEPSEEK_API_KEY:
            logger.error("❌ DEEPSEEK_API_KEY не задан в переменных окружения")
            return JSONResponse(content={
                "version": body["version"],
                "session": body["session"],
                "response": {"text": "Ошибка: не настроен API ключ", "tts": "Ошибка", "end_session": False}
            })
        
        # Запрос к DeepSeek
        headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": user_text}],
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        logger.error(f"Отправляем запрос в DeepSeek: {json.dumps(payload, ensure_ascii=False)}")
        
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=30)
        
        # Логируем статус и тело ответа от DeepSeek (ОЧЕНЬ ВАЖНО)
        logger.error(f"HTTP статус от DeepSeek: {response.status_code}")
        logger.error(f"Тело ответа от DeepSeek: {response.text}")
        
        # Если статус не 200 — выводим ошибку
        if response.status_code != 200:
            error_msg = f"DeepSeek вернул ошибку {response.status_code}: {response.text}"
            logger.error(error_msg)
            return JSONResponse(content={
                "version": body["version"],
                "session": body["session"],
                "response": {"text": "Сервис временно недоступен", "tts": "Ошибка", "end_session": False}
            })
        
        # Парсим ответ
        deepseek_data = response.json()
        if "choices" not in deepseek_data:
            logger.error(f"Нет поля 'choices' в ответе: {deepseek_data}")
            return JSONResponse(content={
                "version": body["version"],
                "session": body["session"],
                "response": {"text": "Неожиданный ответ от DeepSeek", "tts": "Ошибка", "end_session": False}
            })
        
        answer = deepseek_data["choices"][0]["message"]["content"]
        
        # Формируем ответ Алисе
        alice_response = {
            "version": body["version"],
            "session": body["session"],
            "response": {
                "text": answer,
                "tts": answer,
                "end_session": False
            }
        }
        logger.error(f"Ответ Алисе: {json.dumps(alice_response, ensure_ascii=False)}")
        return JSONResponse(content=alice_response)
        
    except Exception as e:
        logger.exception(f"Общая ошибка: {e}")
        return JSONResponse(content={
            "version": "1.0",
            "session": {},
            "response": {"text": "Внутренняя ошибка", "tts": "Ошибка", "end_session": False}
        })
