# services.py
"""
Функции для работы с внешними API и тяжелые генерации
"""
import os
import json
import logging
import aiohttp
import asyncio
import tempfile
import re
import time
from typing import Optional, Dict, List, Any

from config import DEEPSEEK_API_KEY, DEEPGRAM_API_KEY, YANDEX_API_KEY, COMMUNICATION_MODES
from profiles import VECTORS, LEVEL_PROFILES
from test_questions import get_deep_patterns_description

logger = logging.getLogger(__name__)

# ============================================
# API ФУНКЦИИ
# ============================================

async def speech_to_text(voice_file_path: str) -> str:
    """Преобразует голос в текст через Deepgram"""
    if not DEEPGRAM_API_KEY:
        logger.error("❌ DEEPGRAM_API_KEY не найден")
        return ""
    
    url = "https://api.deepgram.com/v1/listen"
    params = {
        "model": "nova-2",
        "language": "ru",
        "punctuate": "true",
        "smart_format": "true",
        "detect_language": "false"
    }
    
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "audio/ogg"
    }
    
    try:
        logger.info(f"🎤 Отправка голосового сообщения в Deepgram STT")
        
        with open(voice_file_path, 'rb') as audio_file:
            audio_data = audio_file.read()
        
        timeout = aiohttp.ClientTimeout(total=60)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                params=params,
                headers=headers,
                data=audio_data,
                timeout=timeout
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"❌ Ошибка Deepgram API {response.status}: {error_text[:200]}")
                    return ""
                
                result = await response.json()
                
                try:
                    transcript = result["results"]["channels"][0]["alternatives"][0]["transcript"]
                    logger.info(f"✅ Голос распознан: {len(transcript)} символов")
                    return transcript
                except (KeyError, IndexError) as e:
                    logger.error(f"❌ Ошибка парсинга ответа Deepgram: {e}")
                    return ""
                    
    except Exception as e:
        logger.error(f"💥 Ошибка Deepgram STT: {e}")
        return ""


async def text_to_speech(text: str, mode: str = "coach") -> Optional[bytes]:
    """Преобразует текст в голос через Yandex SpeechKit"""
    if not YANDEX_API_KEY:
        logger.error("❌ YANDEX_API_KEY не найден")
        return None
    
    clean_text = text.replace('*', '').replace('_', '').replace('`', '').replace('#', '')
    clean_text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', clean_text)
    
    if len(clean_text) > 1000:
        clean_text = clean_text[:1000] + "..."
    
    url = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
    
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
    }
    
    mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["coach"])
    voice = mode_config.get("voice", "filipp")
    emotion = mode_config.get("voice_emotion", "neutral")
    
    if mode == "coach":
        speed = "1.0"
    elif mode == "friend":
        speed = "0.9"
    elif mode == "trainer":
        speed = "1.1"
    else:
        speed = "1.0"
    
    data = {
        "text": clean_text,
        "voice": voice,
        "emotion": emotion,
        "speed": speed,
        "format": "oggopus",
    }
    
    try:
        logger.info(f"🎧 Отправка в Яндекс TTS: голос {voice}, эмоция {emotion}, скорость {speed}")
        
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=headers,
                data=data,
                timeout=timeout
            ) as response:
                
                if response.status == 200:
                    audio_data = await response.read()
                    logger.info(f"✅ Аудио получено: {len(audio_data)} байт")
                    return audio_data
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Ошибка Yandex TTS {response.status}: {error_text}")
                    return None
                    
    except Exception as e:
        logger.error(f"💥 Ошибка Yandex TTS: {e}")
        return None


async def call_deepseek(prompt: str, system_message: str = "", max_tokens: int = 500, retry_count: int = 3) -> Optional[str]:
    """Вызов DeepSeek API"""
    if not DEEPSEEK_API_KEY:
        logger.error("❌ DEEPSEEK_API_KEY не найден")
        return None

    url = "https://api.deepseek.com/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})

    data = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": max_tokens,
    }

    for attempt in range(retry_count):
        try:
            logger.info(f"📡 Попытка {attempt + 1}/{retry_count}")
            
            timeout = aiohttp.ClientTimeout(total=120)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=headers,
                    json=data,
                    timeout=timeout
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"❌ Ошибка API {response.status}: {error_text[:200]}")
                        
                        if response.status == 429:
                            wait_time = (2 ** attempt) + random.random()
                            await asyncio.sleep(wait_time)
                            continue
                        elif response.status >= 500:
                            wait_time = (2 ** attempt) + random.random()
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            return None
                    
                    result = await response.json()
                    
                    if result and "choices" in result and len(result["choices"]) > 0:
                        content = result["choices"][0]["message"]["content"]
                        logger.info(f"✅ Успех! Длина ответа: {len(content)} символов")
                        return content
                    else:
                        logger.error(f"❌ Странный формат ответа: {result}")
                        return None
                            
        except asyncio.TimeoutError:
            logger.error(f"⏰ Таймаут соединения (попытка {attempt + 1})")
            if attempt < retry_count - 1:
                wait_time = (2 ** attempt) + random.random()
                await asyncio.sleep(wait_time)
        except Exception as e:
            logger.error(f"💥 Неожиданная ошибка: {e}")
            if attempt < retry_count - 1:
                wait_time = (2 ** attempt) + random.random()
                await asyncio.sleep(wait_time)
    
    logger.error("❌ ВСЕ ПОПЫТКИ НЕ УДАЛИСЬ")
    return None


async def generate_response_with_full_context(user_id: int, user_message: str, state_data: dict, user_contexts: dict) -> str:
    """Генерирует ответ с учётом полного контекста пользователя"""
    
    user_context = user_contexts.get(user_id)
    
    mode = "coach"
    if user_context:
        mode = user_context.communication_mode
    elif state_data.get("communication_mode"):
        mode = state_data["communication_mode"]
    
    mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["coach"])
    
    profile_data = state_data.get("profile_data", {})
    profile_code = profile_data.get('display_name', 'не определен')
    
    full_context = ""
    if user_context:
        full_context = user_context.get_prompt_context()
    
    address = user_context.get_address() if user_context and mode == "friend" else ""
    
    history = state_data.get("history", [])
    history_text = ""
    for entry in history[-5:]:
        role = "Клиент" if entry["role"] == "user" else "Психолог"
        history_text += f"{role}: {entry['text']}\n"
    
    # Добавляем информацию о текущем маршруте, если есть
    route_info = ""
    if state_data.get("current_destination"):
        dest = state_data["current_destination"]
        route_info = f"\nТЕКУЩАЯ ЦЕЛЬ: {dest.get('name', '')}\n"
        route_info += f"ЭТАП: {state_data.get('route_step', 1)}/3\n"
    
    base_prompt = f"""Ты — Фреди, виртуальный психолог, оцифрованная версия Андрея Мейстера.
Ты общаешься с пользователем.

ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ: {profile_code}

КОНТЕКСТ ПОЛЬЗОВАТЕЛЯ:
{full_context}

{route_info}

РЕЖИМ ОБЩЕНИЯ: {mode_config['display_name']}
{mode_config['responsibility']}

ИНСТРУКЦИЯ: {mode_config['system_prompt']}

ИСТОРИЯ ДИАЛОГА:
{history_text}

СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ: {user_message}

ОТВЕТ (учитывая контекст и режим):"""
    
    response = await call_deepseek(base_prompt, max_tokens=500)
    
    if not response:
        if user_context and user_context.weather_cache:
            weather = user_context.weather_cache
            if weather['temp'] < 0 and "грусть" in user_message.lower():
                response = f"Слушайте, погода {weather['icon']} действительно может влиять на настроение. Расскажите подробнее?"
            else:
                response = f"Я слышу вас. Что именно вас беспокоит?"
        else:
            response = f"Я слышу вас. Расскажите подробнее?"
    
    return response


async def generate_ai_profile(user_id: int, state_data: dict) -> Optional[str]:
    """
    Отправляет все ответы в DeepSeek и получает развернутый профиль
    """
    
    data = state_data
    
    # Собираем все данные
    scores = {}
    for k in ["СБ", "ТФ", "УБ", "ЧВ"]:
        levels = data.get("behavioral_levels", {}).get(k, [])
        scores[k] = sum(levels) / len(levels) if levels else 3.0
    
    sb_level = level(scores.get("СБ", 3))
    tf_level = level(scores.get("ТФ", 3))
    ub_level = level(scores.get("УБ", 3))
    chv_level = level(scores.get("ЧВ", 3))
    
    perception_type = data.get("perception_type", "не определен")
    thinking_level = data.get("thinking_level", 5)
    deep_patterns = data.get("deep_patterns", {})
    
    # Определяем доминирующий уровень Дилтса
    dilts_counts = data.get("dilts_counts", {})
    dominant_dilts = determine_dominant_dilts(dilts_counts)
    
    dilts_names = {
        "ENVIRONMENT": "Окружение",
        "BEHAVIOR": "Поведение", 
        "CAPABILITIES": "Способности",
        "VALUES": "Ценности",
        "IDENTITY": "Идентичность"
    }
    
    # ВАЖНО: добавляем инструкцию по форматированию
    prompt = f"""ТЫ — ПСИХОЛОГ-АНАЛИТИК. На основе данных теста составь психологический портрет человека.

=== ИСХОДНЫЕ ДАННЫЕ ===

1. ТИП ВОСПРИЯТИЯ: {perception_type}
   (как человек смотрит на мир)

2. УРОВЕНЬ МЫШЛЕНИЯ: {thinking_level}/9
   (1-3 конкретное, 4-6 системное, 7-9 мета-системное)

3. ПОВЕДЕНЧЕСКИЕ ВЕКТОРЫ (уровни 1-6):
   • Реакция на угрозу: {sb_level}/6
   • Отношение к деньгам: {tf_level}/6
   • Понимание мира: {ub_level}/6
   • Отношения с людьми: {chv_level}/6

4. ТОЧКА РОСТА (доминирующий уровень Дилтса): {dilts_names.get(dominant_dilts, "Поведение")}

5. ГЛУБИННЫЕ ПАТТЕРНЫ:
   • Тип привязанности: {deep_patterns.get('attachment', 'не определен')}
   • Защитные механизмы: {', '.join(deep_patterns.get('defense_mechanisms', ['не определены']))}
   • Базовые убеждения: {', '.join(deep_patterns.get('core_beliefs', ['не определены']))}

=== ЗАДАЧА ===
Напиши психологический портрет в 5 блоках:

🔹 БЛОК 1: КЛЮЧЕВАЯ ХАРАКТЕРИСТИКА (2-3 предложения)
   Как одним словом можно описать этого человека? В чем его суть?

🔹 БЛОК 2: СИЛЬНЫЕ СТОРОНЫ (3-4 пункта)
   Что у него получается хорошо? На что можно опираться?

🔹 БЛОК 3: ЗОНЫ РОСТА (3-4 пункта)
   Что мешает, ограничивает, создает проблемы?

🔹 БЛОК 4: КАК ЭТО СФОРМИРОВАЛОСЬ (3-4 предложения)
   Откуда взялись эти паттерны? Свяжи с глубинными паттернами.

🔹 БЛОК 5: ГЛАВНАЯ ЛОВУШКА (2-3 предложения)
   Какой цикл сам себя подпитывает?

СТИЛЬ: Как опытный психолог — честно, по-взрослому, без воды, но с заботой.

!!! ВАЖНОЕ ТРЕБОВАНИЕ К ФОРМАТИРОВАНИЮ !!!
- Используй ТОЛЬКО **жирный текст** для заголовков блоков
- Не используй символы #, _ в других местах
- Каждый пункт в списках начинай с •
- Не оставляй незакрытые символы **
- Проверь, что все ** имеют закрывающую пару

ОБЪЕМ: Не больше 2000 символов всего.
"""
    
    response = await call_deepseek(prompt, max_tokens=2000)
    
    if not response:
        # Запасной вариант
        response = generate_fallback_profile(scores, perception_type, thinking_level, deep_patterns)
    
    return response


def generate_fallback_profile(scores: dict, perception_type: str, thinking_level: int, deep_patterns: dict = None) -> str:
    """Генерирует простой профиль на основе шаблонов"""
    
    sb_level = level(scores.get('СБ', 3))
    tf_level = level(scores.get('ТФ', 3))
    ub_level = level(scores.get('УБ', 3))
    chv_level = level(scores.get('ЧВ', 3))
    
    # Определяем доминирующий вектор
    vectors = {'СБ': sb_level, 'ТФ': tf_level, 'УБ': ub_level, 'ЧВ': chv_level}
    min_vector = min(vectors.items(), key=lambda x: x[1])
    
    profile_templates = {
        'СБ': {
            'key': 'ЗАЩИТНИК',
            'strengths': ['Умеете держать удар', 'Стабильны в стрессе', 'Надежны'],
            'growth': ['Можете замыкаться', 'Пропускаете атаки мимо себя'],
            'origin': 'Сформировалось в среде, где нужно было защищаться'
        },
        'ТФ': {
            'key': 'ДОБЫТЧИК',
            'strengths': ['Умеете зарабатывать', 'Практичны', 'Результативны'],
            'growth': ['Можете зацикливаться на деньгах', 'Рискуете'],
            'origin': 'Выросли в среде, где ресурсы были ограничены'
        },
        'УБ': {
            'key': 'МЫСЛИТЕЛЬ',
            'strengths': ['Глубоко анализируете', 'Видите суть', 'Проницательны'],
            'growth': ['Можете закапываться', 'Сомневаетесь'],
            'origin': 'С детства искали смыслы и объяснения'
        },
        'ЧВ': {
            'key': 'КОММУНИКАТОР',
            'strengths': ['Эмпатичны', 'Легко находите контакт', 'Понимаете людей'],
            'growth': ['Теряете себя в отношениях', 'Зависите от мнения'],
            'origin': 'Сформировались в среде, где важны были связи'
        }
    }
    
    profile = profile_templates.get(min_vector[0], profile_templates['СБ'])
    
    text = f"""
🔹 *КЛЮЧЕВАЯ ХАРАКТЕРИСТИКА*
Вы — «{profile['key']}». {perception_type.lower()}, с мышлением {thinking_level}/9.

🔹 *СИЛЬНЫЕ СТОРОНЫ*
• {profile['strengths'][0]}
• {profile['strengths'][1]}
• {profile['strengths'][2]}

🔹 *ЗОНЫ РОСТА*
• {profile['growth'][0]}
• {profile['growth'][1]}

🔹 *КАК ЭТО СФОРМИРОВАЛОСЬ*
{profile['origin']}. Ваши глубинные паттерны закрепили этот способ взаимодействия с миром.

🔹 *ГЛАВНАЯ ЛОВУШКА*
Вы попадаете в цикл: ситуация → привычная реакция → результат → закрепление реакции.
"""
    return text


async def generate_psychologist_thought(user_id: int, state_data: dict) -> str:
    """Генерирует мысли психолога с использованием конфайнмент-модели"""
    
    data = state_data
    
    scores = {}
    for k in ["СБ", "ТФ", "УБ", "ЧВ"]:
        levels = data.get("behavioral_levels", {}).get(k, [])
        scores[k] = sum(levels) / len(levels) if levels else 3.0
    
    sb_level = level(scores.get("СБ", 3))
    tf_level = level(scores.get("ТФ", 3))
    ub_level = level(scores.get("УБ", 3))
    chv_level = level(scores.get("ЧВ", 3))
    
    perception_type = data.get("perception_type", "не определен")
    thinking_level = data.get("thinking_level", 5)
    deep_patterns = data.get("deep_patterns", {})
    
    # Получаем конфайнмент-модель
    model_data = data.get('confinement_model')
    model_summary = "не построена"
    if model_data:
        try:
            from models import ConfinementModel9
            model = ConfinementModel9.from_dict(model_data)
            if model.key_confinement:
                elem = model.key_confinement['element']
                model_summary = f"Ключевой элемент: {elem.name} - {elem.description[:100]}"
        except:
            pass
    
    prompt = f"""ТЫ — ПСИХОЛОГ-АНАЛИТИК. Используя конфайнмент-модель, проанализируй состояние пользователя.

=== ДАННЫЕ ПОЛЬЗОВАТЕЛЯ ===

ПРОФИЛЬ:
- Тип восприятия: {perception_type}
- Уровень мышления: {thinking_level}/9
- Поведенческие векторы: СБ={sb_level}, ТФ={tf_level}, УБ={ub_level}, ЧВ={chv_level}

ГЛУБИННЫЕ ПАТТЕРНЫ:
{json.dumps(deep_patterns, ensure_ascii=False, indent=2) if deep_patterns else "не определены"}

КОНФАЙНМЕНТ-МОДЕЛЬ:
{model_summary}

=== ЗАДАЧА ===
Дай развернутый анализ по 4 пунктам:

1. КЛЮЧЕВОЙ ЭЛЕМЕНТ (2-3 предложения)
   Что сейчас держит систему? Где главный зажим?

2. ПЕТЛЯ (2-3 предложения)
   Какой цикл самоподдержания работает?

3. ТОЧКА ВХОДА (2-3 предложения)
   Где можно разорвать эту петлю?

4. ПРОГНОЗ (2-3 предложения)
   Что будет, если ничего не менять? Что будет, если сделать точку входа?

СТИЛЬ: Как опытный психолог — честно, по-взрослому, но с заботой.
ОБЪЕМ: 1500-2000 символов.
"""
    
    response = await call_deepseek(prompt, max_tokens=1500)
    
    if not response:
        response = """🔹 *КЛЮЧЕВОЙ ЭЛЕМЕНТ*
Судя по вашему профилю, основной зажим — в избегании конфликтов. Вы предпочитаете уйти, чем решать.

🔹 *ПЕТЛЯ*
Возникает цикл: проблема → избегание → накопление → взрыв → чувство вины → еще большее избегание.

🔹 *ТОЧКА ВХОДА*
Попробуйте в следующем конфликте не уходить, а сделать паузу и сказать: "Мне нужно подумать". Это разорвет автоматизм.

🔹 *ПРОГНОЗ*
Без изменений: будете накапливать напряжение и взрываться. С изменениями: научитесь экологично отстаивать себя."""
    
    return response


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def level(score: float) -> int:
    """Дробный балл 1..4 → целый уровень 1..6"""
    if score <= 1.49:
        return 1
    elif score <= 2.00:
        return 2
    elif score <= 2.50:
        return 3
    elif score <= 3.00:
        return 4
    elif score <= 3.50:
        return 5
    else:
        return 6


def determine_dominant_dilts(dilts_counts: dict) -> str:
    """Определяет доминирующий уровень Дилтса"""
    if not dilts_counts:
        return "BEHAVIOR"
    dominant = max(dilts_counts.items(), key=lambda x: x[1])
    return dominant[0]
