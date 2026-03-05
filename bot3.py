#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
МАТРИЦА ПОВЕДЕНИЙ 4×6 - Telegram Bot
Тест поведенческого профиля с DeepSeek AI интерпретацией
"""

import os
import json
import logging
import requests
from statistics import mean
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════
#  НАСТРОЙКИ
# ══════════════════════════════════════════════

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

# Хранилище данных пользователей (в продакшене использовать БД)
user_data = {}

# ══════════════════════════════════════════════
#  ДАННЫЕ МАТРИЦЫ (ВСЕ ТЕ ЖЕ, ЧТО И РАНЬШЕ)
# ══════════════════════════════════════════════

VECTORS = {
    "СБ": {
        "name": "УГРОЗА",
        "stimulus": "реакция когда на вас давят или угрожают",
        "levels": {
            1: {"name": "СТОПОР", "action": "замираешь", "desc": "Тело и разум отключаются при давлении"},
            2: {"name": "ИЗБЕГАНИЕ", "action": "убегаешь", "desc": "Уходишь от столкновения любым способом"},
            3: {"name": "КАПИТУЛЯЦИЯ", "action": "сдаёшься", "desc": "Соглашаешься лишь бы прекратить давление"},
            4: {"name": "МИМИКРИЯ", "action": "притворяешься", "desc": "Внешне спокоен, внутри скрываешь реакцию"},
            5: {"name": "УМИРОТВОРЕНИЕ", "action": "задабриваешь", "desc": "Ищешь компромисс, снижаешь напряжение"},
            6: {"name": "АТАКА", "action": "бьёшь в ответ", "desc": "Прямо защищаешь свои интересы"},
        }
    },
    "ТФ": {
        "name": "РЕСУРС",
        "stimulus": "стратегия когда нужны деньги или материальные блага",
        "levels": {
            1: {"name": "ПАРАЗИТИЗМ", "action": "просишь", "desc": "Ждёшь что дадут, зависишь от чужой воли"},
            2: {"name": "СОБИРАТЕЛЬСТВО", "action": "ищешь готовое", "desc": "Берёшь что есть вокруг, ищешь удачу"},
            3: {"name": "ТОРГОВЛЯ", "action": "обмениваешь", "desc": "Меняешь своё на чужое, торгуешься"},
            4: {"name": "ТРУД", "action": "производишь", "desc": "Создаёшь сам, вкладываешь усилия"},
            5: {"name": "НАКОПЛЕНИЕ", "action": "копишь", "desc": "Создаёшь резерв, управляешь запасами"},
            6: {"name": "УПРАВЛЕНИЕ", "action": "организуешь", "desc": "Выстраиваешь системы, управляешь людьми"},
        }
    },
    "УБ": {
        "name": "НЕИЗВЕСТНОСТЬ",
        "stimulus": "ответ когда непонятно что происходит",
        "levels": {
            1: {"name": "ОТРИЦАНИЕ", "action": "игнорируешь", "desc": "Делаешь вид что непонятного нет"},
            2: {"name": "МАГИЯ", "action": "мистифицируешь", "desc": "Объясняешь судьбой, знаками, высшими силами"},
            3: {"name": "АВТОРИТЕТ", "action": "принимаешь", "desc": "Берёшь готовое объяснение от эксперта"},
            4: {"name": "ЗАГОВОР", "action": "ищешь умысел", "desc": "Ищешь кто виноват и зачем это делается"},
            5: {"name": "ЭМПИРИКА", "action": "проверяешь", "desc": "Собираешь данные, делаешь выводы сам"},
            6: {"name": "ТЕОРИЯ", "action": "систематизируешь", "desc": "Строишь модель, ищешь закономерности"},
        }
    },
    "ЧВ": {
        "name": "ДРУГОЙ",
        "stimulus": "стратегия в отношении других людей",
        "levels": {
            1: {"name": "ЗАВИСИМОСТЬ", "action": "прилипаешь", "desc": "Не можешь без определённых людей"},
            2: {"name": "КОПИРОВАНИЕ", "action": "подражаешь", "desc": "Копируешь успешных, подстраиваешься под группу"},
            3: {"name": "ДЕМОНСТРАЦИЯ", "action": "показываешь себя", "desc": "Привлекаешь внимание, демонстрируешь себя"},
            4: {"name": "МАНИПУЛЯЦИЯ", "action": "используешь", "desc": "Добиваешься своего через влияние на других"},
            5: {"name": "ПАРТНЁРСТВО", "action": "сотрудничаешь", "desc": "Договариваешься, учитываешь интересы обоих"},
            6: {"name": "СЕТИ", "action": "строишь связи", "desc": "Создаёшь систему отношений, управляешь ею"},
        }
    }
}

# ══════════════════════════════════════════════
#  ВОПРОСЫ ТЕСТА
# ══════════════════════════════════════════════

QUESTIONS = {
    "СБ": [
        {
            "text": "Начальник кричит на вас несправедливо. Что вы делаете?",
            "options": [
                "Теряюсь, не могу ничего сказать",
                "Придумываю причину уйти из ситуации",
                "Соглашаюсь со всем — лишь бы прекратить",
                "Внешне спокоен, внутри кипит",
                "Ищу слова чтобы разрядить обстановку",
                "Говорю прямо что считаю это несправедливым",
            ]
        },
        {
            "text": "В споре вам говорят что вы неправы, хотя вы уверены в обратном:",
            "options": [
                "Замолкаю и не могу найти слова",
                "Меняю тему или ухожу от разговора",
                "Соглашаюсь — так проще",
                "Киваю, но внутренне остаюсь при своём",
                "Пытаюсь найти в их словах долю правды",
                "Спокойно отстаиваю свою позицию",
            ]
        },
        {
            "text": "Кто-то нарушает ваши границы — занял ваше место, взял без спроса. Ваш первый импульс:",
            "options": [
                "Ступор. Стою и не знаю что делать",
                "Молча ухожу, найду другое",
                "Уступаю, хотя злюсь",
                "Делаю вид что не заметил",
                "Вежливо, но твёрдо обозначаю",
                "Прямо говорю — это моё",
            ]
        },
    ],
    "ТФ": [
        {
            "text": "Вам срочно нужны деньги. Что делаете первым?",
            "options": [
                "Прошу в долг у близких",
                "Ищу случайный заработок, подработку",
                "Предлагаю что-то своё в обмен",
                "Берусь за конкретную работу и делаю",
                "Использую отложенный резерв",
                "Организую других чтобы решить задачу",
            ]
        },
        {
            "text": "Как вы в основном зарабатываете или добываете ресурсы?",
            "options": [
                "Скорее через других — сам не очень умею",
                "Нахожу где что лежит плохо — работа, скидки, возможности",
                "Через обмен навыками и услугами",
                "Своим прямым трудом — сколько вложил, столько получил",
                "Зарабатываю и обязательно откладываю",
                "Выстраиваю системы которые работают на меня",
            ]
        },
        {
            "text": "Когда появляются лишние деньги:",
            "options": [
                "Трачу сразу или раздаю — всё равно куда-то денутся",
                "Трачу на текущие потребности",
                "Вкладываю во что-то что можно перепродать",
                "Вкладываю в инструменты для своей работы",
                "Откладываю в резерв — страховка прежде всего",
                "Инвестирую в проекты или людей",
            ]
        },
    ],
    "УБ": [
        {
            "text": "Происходит что-то непонятное — кризис, странные события. Ваша первая реакция:",
            "options": [
                "Стараюсь не думать об этом — само разберётся",
                "Это судьба, карма или знак",
                "Читаю что говорят эксперты и следую их мнению",
                "Ясно кто за этим стоит и зачем",
                "Начинаю собирать информацию и проверять",
                "Строю модель: что происходит и почему",
            ]
        },
        {
            "text": "Вы не понимаете почему люди вокруг ведут себя определённым образом:",
            "options": [
                "Мне не очень важно и интересно разбираться",
                "Видимо такова их природа или так суждено",
                "Есть психология которая это объясняет — читаю",
                "Они что-то скрывают или преследуют скрытые цели",
                "Наблюдаю и ищу закономерности в их поведении",
                "Строю гипотезу, проверяю, уточняю понимание",
            ]
        },
        {
            "text": "Берётесь за незнакомое дело. Как подходите?",
            "options": [
                "Скорее откажусь — слишком непонятно",
                "Буду действовать интуитивно, как пойдёт",
                "Найду курс или эксперта и буду следовать",
                "Изучу чужие неудачи — кто и почему провалился",
                "Попробую сам, увижу что не работает, скорректирую",
                "Сначала разберусь в принципах, потом буду действовать",
            ]
        },
    ],
    "ЧВ": [
        {
            "text": "В новом коллективе вы обычно:",
            "options": [
                "Держусь рядом с кем-то одним кто принял меня",
                "Смотрю как ведут себя остальные и повторяю",
                "Стараюсь произвести впечатление, заявить о себе",
                "Анализирую кто здесь важен и как на них повлиять",
                "Ищу тех с кем интересно работать на равных",
                "Думаю кто из этих людей какую ценность представляет",
            ]
        },
        {
            "text": "Когда вам нужна помощь другого человека:",
            "options": [
                "Трудно просить — боюсь испортить отношения",
                "Делаю как они хотят чтобы потом попросить",
                "Показываю что я особенный и заслуживаю помощи",
                "Нахожу что им нужно и использую это как рычаг",
                "Говорю прямо и предлагаю что-то реальное взамен",
                "У меня обычно есть нужный человек в сети",
            ]
        },
        {
            "text": "Ваши отношения с людьми в целом:",
            "options": [
                "Глубокая привязанность к нескольким без которых тяжело",
                "Хорошо подстраиваюсь под окружение",
                "Нравлюсь многим, люди замечают меня",
                "Умею нужным образом повлиять на нужных людей",
                "Несколько крепких партнёрств на основе доверия",
                "Широкая разнообразная сеть контактов",
            ]
        },
    ]
}

# ══════════════════════════════════════════════
#  ПАТТЕРНЫ, КОРРЕЛЯЦИИ, РЕКОМЕНДАЦИИ
#  (ВСТАВЬТЕ СЮДА ВСЕ ДАННЫЕ ИЗ ПРЕДЫДУЩЕЙ ВЕРСИИ)
# ══════════════════════════════════════════════

LIFE_PATTERNS = {}  # Вставьте из предыдущего кода
CORRELATIONS = []   # Вставьте из предыдущего кода
RECOMMENDATIONS = {} # Вставьте из предыдущего кода

# ══════════════════════════════════════════════
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ══════════════════════════════════════════════

def level(score):
    """Дробный балл → целый уровень"""
    return max(1, min(6, round(score)))

def get_profile_text(scores):
    """Формирует текст профиля"""
    text = "📊 *ВАШ ПРОФИЛЬ*\n\n"
    
    for key, score in scores.items():
        vec = VECTORS[key]
        lvl = level(score)
        info = vec["levels"][lvl]
        
        bar = "█" * lvl + "░" * (6 - lvl)
        text += f"*{key}* `[{bar}]` {score:.1f}/6\n"
        text += f"_{vec['name']}_: *{info['name']}*\n"
        text += f"└ {info['desc']}\n\n"
    
    return text

def get_priority_order(scores: dict) -> list:
    """Определяет порядок приоритетов"""
    tf = level(scores["ТФ"])
    if tf <= 2:
        rest = sorted([(k, v) for k, v in scores.items() if k != "ТФ"], key=lambda x: x[1])
        return ["ТФ"] + [r[0] for r in rest]
    else:
        return [k for k, _ in sorted(scores.items(), key=lambda x: x[1])]

# ══════════════════════════════════════════════
#  ФУНКЦИИ DEEPSEEK API
# ══════════════════════════════════════════════

def call_deepseek(prompt, system_message=""):
    """Вызов DeepSeek API"""
    if not DEEPSEEK_API_KEY:
        return None
    
    try:
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        data = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000,
        }
        
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            logger.error(f"API Error: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"DeepSeek API error: {e}")
        return None

# ══════════════════════════════════════════════
#  ОБРАБОТЧИКИ TELEGRAM
# ══════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user_id = update.effective_user.id
    
    # Инициализируем данные пользователя
    user_data[user_id] = {
        "stage": "menu",
        "scores": {k: [] for k in VECTORS},
        "current_vector": None,
        "current_question": 0,
        "questions_order": []
    }
    
    keyboard = [
        [InlineKeyboardButton("🧠 Пройти тест", callback_data="start_test")],
        [InlineKeyboardButton("ℹ️ О тесте", callback_data="about")],
        [InlineKeyboardButton("🤖 AI-анализ (DeepSeek)", callback_data="ai_info")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🧠 *Добро пожаловать в Матрицу Поведений 4×6!*\n\n"
        "Этот тест поможет понять ваши базовые поведенческие паттерны:\n"
        "• *СБ* — реакция на угрозу\n"
        "• *ТФ* — добыча ресурсов\n"
        "• *УБ* — понимание непонятного\n"
        "• *ЧВ* — отношения с людьми\n\n"
        "Выберите действие:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DTYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    if user_id not in user_data:
        user_data[user_id] = {
            "stage": "menu",
            "scores": {k: [] for k in VECTORS},
            "current_vector": None,
            "current_question": 0,
            "questions_order": []
        }
    
    if data == "start_test":
        user_data[user_id]["stage"] = "testing"
        user_data[user_id]["scores"] = {k: [] for k in VECTORS}
        user_data[user_id]["questions_order"] = []
        
        # Перемешиваем векторы для разнообразия (но все должны быть)
        import random
        vectors = list(VECTORS.keys())
        random.shuffle(vectors)
        user_data[user_id]["questions_order"] = vectors
        
        await send_next_question(update, context)
    
    elif data == "about":
        await query.edit_message_text(
            "📚 *О МАТРИЦЕ ПОВЕДЕНИЙ 4×6*\n\n"
            "Тест основан на модели, описывающей 4 ключевых вектора поведения:\n\n"
            "*СБ (Угроза)* — как вы реагируете, когда на вас давят\n"
            "*ТФ (Ресурс)* — как добываете ресурсы и деньги\n"
            "*УБ (Неизвестность)* — как справляетесь с непонятным\n"
            "*ЧВ (Другой)* — как строите отношения с людьми\n\n"
            "Каждый вектор имеет 6 уровней развития — от базовых реакций до зрелых стратегий.\n\n"
            "После теста вы получите:\n"
            "• Ваш профиль по всем векторам\n"
            "• Объяснение жизненных паттернов\n"
            "• Связи между векторами\n"
            "• Рекомендации по развитию\n"
            "• AI-анализ от DeepSeek",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu")
            ]])
        )
    
    elif data == "ai_info":
        if DEEPSEEK_API_KEY:
            text = "🤖 *DeepSeek AI доступен!*\n\nПосле прохождения теста вы сможете:\n• Получить глубокий анализ профиля\n• Задать вопросы о результатах\n• Получить персональные рекомендации"
        else:
            text = "⚠️ *DeepSeek AI не настроен*\n\nAPI ключ не найден. Доступен только стандартный анализ."
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu")
            ]])
        )
    
    elif data == "back_to_menu":
        keyboard = [
            [InlineKeyboardButton("🧠 Пройти тест", callback_data="start_test")],
            [InlineKeyboardButton("ℹ️ О тесте", callback_data="about")],
            [InlineKeyboardButton("🤖 AI-анализ", callback_data="ai_info")]
        ]
        await query.edit_message_text(
            "🧠 *Матрица Поведений 4×6*\n\nВыберите действие:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data.startswith("answer_"):
        # Обработка ответа на вопрос
        parts = data.split("_")
        answer_idx = int(parts[1])
        
        user = user_data[user_id]
        current_vector = user["current_vector"]
        
        # Сохраняем ответ (индекс ответа + 1 = балл)
        user["scores"][current_vector].append(answer_idx + 1)
        
        # Переходим к следующему вопросу
        await send_next_question(update, context)
    
    elif data.startswith("ai_"):
        # AI-функции после теста
        scores = user_data[user_id]["scores"]
        # Преобразуем списки в средние значения
        avg_scores = {k: round(mean(v), 1) for k, v in scores.items()}
        
        if data == "ai_analysis":
            await query.edit_message_text("🤔 *Анализирую ваш профиль...*\nЭто займет несколько секунд", parse_mode='Markdown')
            
            # Формируем запрос к AI
            profile_text = json.dumps({k: {"уровень": level(v), "тип": VECTORS[k]["levels"][level(v)]["name"]} 
                                      for k, v in avg_scores.items()}, indent=2, ensure_ascii=False)
            
            prompt = f"Проанализируй этот профиль и дай 5 инсайтов:\n{profile_text}"
            response = call_deepseek(prompt, "Ты психолог. Отвечай кратко, по делу, на русском.")
            
            if response:
                await query.edit_message_text(
                    f"🧠 *AI-АНАЛИЗ*\n\n{response}\n\n_Анализ предоставлен DeepSeek_",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("◀️ К результатам", callback_data="show_results")
                    ]])
                )
            else:
                await query.edit_message_text(
                    "⚠️ Не удалось получить ответ от AI. Попробуйте позже.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("◀️ Назад", callback_data="show_results")
                    ]])
                )
        
        elif data == "ai_recommendations":
            await query.edit_message_text("💡 *Генерирую рекомендации...*", parse_mode='Markdown')
            
            bottleneck = get_priority_order(avg_scores)[0]
            prompt = f"Профиль: {avg_scores}. Узкое место: {bottleneck}. Дай 5 конкретных шагов на неделю."
            response = call_deepseek(prompt, "Ты коуч. Только конкретные действия.")
            
            if response:
                await query.edit_message_text(
                    f"📌 *ПЕРСОНАЛЬНЫЕ РЕКОМЕНДАЦИИ*\n\n{response}",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("◀️ К результатам", callback_data="show_results")
                    ]])
                )
            else:
                await query.edit_message_text(
                    "⚠️ Не удалось получить рекомендации.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("◀️ Назад", callback_data="show_results")
                    ]])
                )
    
    elif data == "show_results":
        await show_test_results(update, context)
    
    elif data == "restart_test":
        user_data[user_id] = {
            "stage": "menu",
            "scores": {k: [] for k in VECTORS},
            "current_vector": None,
            "current_question": 0,
            "questions_order": []
        }
        await start(update, context)

async def send_next_question(update: Update, context: ContextTypes.DTYPE):
    """Отправляет следующий вопрос теста"""
    query = update.callback_query
    user_id = update.effective_user.id
    user = user_data[user_id]
    
    # Находим следующий вектор с вопросами
    while user["questions_order"]:
        current_vector = user["questions_order"][0]
        vector_questions = QUESTIONS[current_vector]
        current_q_idx = user["current_question"]
        
        if current_q_idx < len(vector_questions):
            # Есть вопросы в текущем векторе
            user["current_vector"] = current_vector
            question = vector_questions[current_q_idx]
            
            # Формируем клавиатуру с вариантами ответов
            keyboard = []
            for i, option in enumerate(question["options"]):
                keyboard.append([InlineKeyboardButton(
                    f"{i+1}. {option[:30]}..." if len(option) > 30 else f"{i+1}. {option}",
                    callback_data=f"answer_{i}"
                )])
            
            # Кнопка отмены
            keyboard.append([InlineKeyboardButton("❌ Отменить тест", callback_data="back_to_menu")])
            
            progress = f"Вопрос {current_q_idx + 1}/{len(vector_questions)} по вектору {current_vector}"
            
            await query.edit_message_text(
                f"🧠 *{current_vector} — {VECTORS[current_vector]['name']}*\n\n"
                f"_{progress}_\n\n"
                f"{question['text']}",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
            # Увеличиваем счетчик вопроса
            user["current_question"] += 1
            return
        else:
            # Все вопросы в текущем векторе отвечены, переходим к следующему
            user["questions_order"].pop(0)
            user["current_question"] = 0
    
    # Все вопросы закончились - показываем результаты
    await show_test_results(update, context)

async def show_test_results(update: Update, context: ContextTypes.DTYPE):
    """Показывает результаты теста"""
    query = update.callback_query
    user_id = update.effective_user.id
    user = user_data[user_id]
    
    # Вычисляем средние баллы
    scores = {k: round(mean(v), 1) for k, v in user["scores"].items()}
    
    # Профиль
    text = get_profile_text(scores)
    
    # Узкое место
    bottleneck = get_priority_order(scores)[0]
    text += f"\n🎯 *УЗКОЕ МЕСТО:* {bottleneck} — {VECTORS[bottleneck]['name']}\n"
    
    # Кнопки для дальнейших действий
    keyboard = [
        [InlineKeyboardButton("🧠 AI-анализ", callback_data="ai_analysis"),
         InlineKeyboardButton("💡 AI-рекомендации", callback_data="ai_recommendations")],
        [InlineKeyboardButton("📋 Стандартный анализ", callback_data="standard_analysis")],
        [InlineKeyboardButton("🔄 Пройти заново", callback_data="restart_test")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
    ]
    
    if not DEEPSEEK_API_KEY:
        # Если нет API, показываем только стандартный анализ
        keyboard = [
            [InlineKeyboardButton("📋 Стандартный анализ", callback_data="standard_analysis")],
            [InlineKeyboardButton("🔄 Пройти заново", callback_data="restart_test")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
        ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def standard_analysis(update: Update, context: ContextTypes.DTYPE):
    """Показывает стандартный анализ (без AI)"""
    query = update.callback_query
    user_id = update.effective_user.id
    scores = {k: round(mean(v), 1) for k, v in user_data[user_id]["scores"].items()}
    
    text = get_profile_text(scores)
    
    # Паттерны
    text += "\n🔍 *ЖИЗНЕННЫЕ ПАТТЕРНЫ*\n"
    for key in ["ТФ", "СБ", "УБ", "ЧВ"]:
        lvl = level(scores[key])
        if key in LIFE_PATTERNS and lvl in LIFE_PATTERNS[key]:
            text += f"\n*{key}:* {LIFE_PATTERNS[key][lvl][:100]}...\n"
    
    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Назад", callback_data="show_results")
        ]])
    )

async def handle_message(update: Update, context: ContextTypes.DTYPE):
    """Обработчик текстовых сообщений (для диалога с AI)"""
    user_id = update.effective_user.id
    
    if user_id not in user_data or user_data[user_id].get("stage") != "dialogue":
        await update.message.reply_text(
            "Используйте /start для начала работы с ботом",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Меню", callback_data="back_to_menu")
            ]])
        )
        return
    
    # Режим диалога с AI
    if not DEEPSEEK_API_KEY:
        await update.message.reply_text("⚠️ AI-режим недоступен")
        return
    
    scores = user_data[user_id]["scores"]
    avg_scores = {k: round(mean(v), 1) for k, v in scores.items()}
    
    prompt = f"Профиль пользователя: {avg_scores}\n\nВопрос: {update.message.text}\n\nОтветь коротко и по делу."
    response = call_deepseek(prompt, "Ты психолог. Отвечай на русском, 2-3 предложения.")
    
    if response:
        await update.message.reply_text(f"🤖 {response}")
    else:
        await update.message.reply_text("⚠️ Не удалось получить ответ")

# ══════════════════════════════════════════════
#  ЗАПУСК БОТА
# ══════════════════════════════════════════════

def main():
    """Запуск бота"""
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN не найден в переменных окружения")
        return
    
    # Создаем приложение
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запускаем бота
    logger.info("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
