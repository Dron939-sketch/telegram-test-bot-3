import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("DEEPSEEK_API_KEY")

print("=== ТЕСТ AI ===")
print(f"Ключ найден: {bool(api_key)}")
print(f"Длина ключа: {len(api_key) if api_key else 0}")

if api_key:
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        
        # Тест 1: Проверка моделей
        print("\n1. Проверка доступа к API...")
        r = requests.get("https://api.deepseek.com/v1/models", headers=headers)
        print(f"Статус: {r.status_code}")
        
        # Тест 2: Реальный запрос к AI
        print("\n2. Тестовый запрос к AI...")
        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": "Привет! Как дела? Ответь одним предложением."}
            ],
            "temperature": 0.7
        }
        r = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        print(f"Статус: {r.status_code}")
        if r.status_code == 200:
            result = r.json()
            print(f"Ответ AI: {result['choices'][0]['message']['content']}")
        else:
            print(f"Ошибка: {r.text}")
            
    except Exception as e:
        print(f"Ошибка: {e}")
