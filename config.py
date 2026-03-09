# config.py
"""
Конфигурация и константы бота
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Токены API
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY", "")
YANDEX_API_KEY = os.environ.get("YANDEX_API_KEY", "")
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")

# ID администраторов
ADMIN_IDS = [532205848]

# Режимы общения
COMMUNICATION_MODES = {
    "coach": {
        "name": "КОУЧ",
        "display_name": "🔮 КОУЧ",
        "emoji": "🔮",
        "voice": "filipp",
        "voice_emotion": "neutral",
        "responsibility": "Помогаю найти ответы внутри вас. Не даю готовых решений, а задаю вопросы.",
        "system_prompt": """Ты — КОУЧ. Твоя задача: задавать открытые вопросы, помогать клиенту найти ответы внутри себя.

        ТЫ НЕ ДОЛЖЕН:
        - Давать готовые советы
        - Говорить "я бы на вашем месте"
        - Предлагать конкретные решения
        - Оценивать и судить

        ТЫ ДОЛЖЕН:
        - Задавать уточняющие вопросы
        - Отражать мысли клиента
        - Помогать структурировать размышления
        - Поддерживать в поиске собственных ответов
        
        ТВОЯ ФОРМУЛА: вопрос > ответ. Каждый твой ответ должен содержать вопрос.
        
        ГОВОРИ КОРОТКО, ПО ДЕЛУ, БЕЗ ВОДЫ. 2-4 предложения максимум."""
    },
    "friend": {
        "name": "ДРУГ",
        "display_name": "💚 ДРУГ",
        "emoji": "💚",
        "voice": "ermil",
        "voice_emotion": "good",
        "responsibility": "Выслушиваю, поддерживаю, принимаю без осуждения. Как старший товарищ.",
        "system_prompt": """Ты — ДРУГ (как старший товарищ). Твоя задача: выслушивать, поддерживать, принимать без осуждения.

        ТЫ НЕ ДОЛЖЕН:
        - Давать непрошеные советы
        - Обесценивать чувства ("не парьтесь", "ерунда")
        - Сравнивать с другими
        - Требовать "взять себя в руки"

        ТЫ ДОЛЖЕН:
        - Сначала признать чувства ("я слышу вас", "это действительно тяжело")
        - Задавать бережные вопросы
        - Быть рядом и поддерживать
        
        ТВОЯ ФОРМУЛА: принятие → поддержка → бережный вопрос.
        
        ГОВОРИ КОРОТКО, ДУШЕВНО, БЕЗ НАЗИДАНИЙ."""
    },
    "trainer": {
        "name": "ТРЕНЕР",
        "display_name": "⚡ ТРЕНЕР",
        "emoji": "⚡",
        "voice": "filipp",
        "voice_emotion": "strict",
        "responsibility": "Даю чёткие инструкции, структуру, план действий. Требую результат.",
        "system_prompt": """Ты — ТРЕНЕР. Твоя задача: давать чёткие инструкции, структуру, план действий. Требовать результат.

        ТВОЙ СТИЛЬ: коротко, по делу, без воды.

        ТЫ ДОЛЖЕН:
        - Давать конкретные шаги
        - Устанавливать сроки
        - Контролировать выполнение
        - Требовать отчёт
        
        ФОРМУЛА: задача → дедлайн → следующий шаг.
        
        ГОВОРИ: чётко, структурно, с фокусом на действие."""
    }
}

# Для обратной совместимости
COMMUNICATION_MODES["hard"] = COMMUNICATION_MODES["trainer"]
COMMUNICATION_MODES["medium"] = COMMUNICATION_MODES["coach"]
COMMUNICATION_MODES["soft"] = COMMUNICATION_MODES["friend"]

# Точки назначения
DESTINATIONS = {
    "coach": {
        "self_discovery": {
            "name": "🧩 САМОПОЗНАНИЕ",
            "description": "Понять себя, свои истинные желания и ценности",
            "destinations": [
                {"id": "values", "name": "Понять свои ценности", "time": "2-4 недели", "difficulty": "medium"},
                {"id": "purpose", "name": "Найти предназначение", "time": "1-3 месяца", "difficulty": "hard"},
                {"id": "strengths", "name": "Осознать сильные стороны", "time": "2-3 недели", "difficulty": "easy"},
                {"id": "blocks", "name": "Найти внутренние блоки", "time": "3-4 недели", "difficulty": "medium"}
            ]
        },
        "decisions": {
            "name": "⚖️ ПРИНЯТИЕ РЕШЕНИЙ",
            "description": "Научиться делать выбор и не жалеть",
            "destinations": [
                {"id": "choice", "name": "Сделать сложный выбор", "time": "1-2 недели", "difficulty": "medium"},
                {"id": "priorities", "name": "Расставить приоритеты", "time": "1 неделя", "difficulty": "easy"},
                {"id": "doubts", "name": "Преодолеть сомнения", "time": "2-3 недели", "difficulty": "medium"}
            ]
        },
        "goals": {
            "name": "🎯 ПОСТАНОВКА ЦЕЛЕЙ",
            "description": "Научиться ставить цели и достигать их",
            "destinations": [
                {"id": "smart_goals", "name": "Сформулировать цели по SMART", "time": "1 неделя", "difficulty": "easy"},
                {"id": "action_plan", "name": "Составить план действий", "time": "2 недели", "difficulty": "easy"},
                {"id": "motivation", "name": "Найти мотивацию", "time": "2-3 недели", "difficulty": "medium"}
            ]
        }
    },
    "friend": {
        "emotions": {
            "name": "💭 РАБОТА С ЧУВСТВАМИ",
            "description": "Научиться понимать и проживать эмоции",
            "destinations": [
                {"id": "anger", "name": "Справиться с гневом", "time": "2-3 недели", "difficulty": "medium"},
                {"id": "fear", "name": "Преодолеть страх", "time": "3-4 недели", "difficulty": "hard"},
                {"id": "sadness", "name": "Пережить грусть", "time": "2-4 недели", "difficulty": "medium"},
                {"id": "anxiety", "name": "Успокоить тревогу", "time": "3-5 недель", "difficulty": "hard"}
            ]
        },
        "self_esteem": {
            "name": "🪞 САМООЦЕНКА",
            "description": "Повысить уверенность в себе",
            "destinations": [
                {"id": "confidence", "name": "Стать увереннее", "time": "3-6 недель", "difficulty": "medium"},
                {"id": "self_love", "name": "Полюбить себя", "time": "1-2 месяца", "difficulty": "hard"},
                {"id": "boundaries", "name": "Выстроить границы", "time": "3-5 недель", "difficulty": "medium"}
            ]
        },
        "loneliness": {
            "name": "🫂 ОДИНОЧЕСТВО",
            "description": "Справиться с чувством одиночества",
            "destinations": [
                {"id": "connect", "name": "Научиться сближаться", "time": "4-6 недель", "difficulty": "hard"},
                {"id": "alone_time", "name": "Комфортно быть одному", "time": "3-5 недель", "difficulty": "medium"},
                {"id": "friends", "name": "Найти друзей", "time": "2-3 месяца", "difficulty": "hard"}
            ]
        }
    },
    "trainer": {
        "career": {
            "name": "💼 КАРЬЕРА",
            "description": "Профессиональный рост и достижения",
            "destinations": [
                {"id": "new_job", "name": "Найти работу мечты", "time": "1-3 месяца", "difficulty": "hard"},
                {"id": "promotion", "name": "Получить повышение", "time": "2-4 месяца", "difficulty": "hard"},
                {"id": "skills", "name": "Освоить новый навык", "time": "1-2 месяца", "difficulty": "medium"}
            ]
        },
        "business": {
            "name": "💰 БИЗНЕС",
            "description": "Развитие своего дела",
            "destinations": [
                {"id": "startup", "name": "Запустить проект", "time": "2-3 месяца", "difficulty": "hard"},
                {"id": "profit", "name": "Увеличить прибыль", "time": "3-6 месяцев", "difficulty": "hard"},
                {"id": "team", "name": "Собрать команду", "time": "2-4 месяца", "difficulty": "hard"}
            ]
        },
        "habits": {
            "name": "🏋️ ПРИВЫЧКИ",
            "description": "Внедрить полезные привычки",
            "destinations": [
                {"id": "sport", "name": "Начать заниматься спортом", "time": "21 день", "difficulty": "medium"},
                {"id": "morning", "name": "Выстроить утреннюю рутину", "time": "2-3 недели", "difficulty": "easy"},
                {"id": "productivity", "name": "Повысить продуктивность", "time": "1-2 месяца", "difficulty": "medium"}
            ]
        },
        "finance": {
            "name": "💰 ФИНАНСЫ",
            "description": "Улучшить финансовое положение",
            "destinations": [
                {"id": "budget", "name": "Научиться budgeting", "time": "2-3 недели", "difficulty": "easy"},
                {"id": "savings", "name": "Накопить подушку", "time": "3-6 месяцев", "difficulty": "medium"},
                {"id": "invest", "name": "Начать инвестировать", "time": "2-3 месяца", "difficulty": "hard"}
            ]
        }
    }
}
