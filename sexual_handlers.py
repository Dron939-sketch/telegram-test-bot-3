"""
Обработчики для сексуального теста
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# 👇 ИСПРАВЛЕНО: Импортируем из sexual_questions, а не из sexual_profile
from sexual_questions import SEXUAL_QUESTIONS
from sexual_interpretations import format_sexual_profile
from utils.helpers import calculate_progress, generate_unique_callback

logger = logging.getLogger(__name__)

# Состояния для сексуального теста
SEXUAL_TEST, SEXUAL_RESULTS = range(50, 52)

async def sexual_test_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало сексуального теста"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    logger.info(f"🔞 sexual_test_start ВЫЗВАН для пользователя {user_id}")
    
    await query.answer()
    
    # Инициализируем данные для теста
    context.user_data["sexual_current"] = 0
    context.user_data["sexual_scores"] = {
        "temperament": {"PREDATOR": 0, "ARTIST": 0, "OBSERVER": 0, "PLAYER": 0},
        "fetishes": {"SMELL": 0, "MATERIALS": 0, "BODY_PARTS": 0, "SITUATIONS": 0},
        "formats": {
            "MFM": 0, "FMF": 0, "SWING": 0, "BDSM_DOM": 0, "BDSM_SUB": 0,
            "BDSM_LIGHT": 0, "ROLES": 0, "RISK": 0, "TOYS": 0, "VIDEO": 0,
            "VIRTUAL": 0, "MONO": 0, "TRADITIONAL": 0, "ADAPTIVE": 0, "VOYEURISM": 0
        }
    }
    context.user_data["sexual_last_answered"] = -1
    
    intro_text = (
        f"🔞 <b>ТЕСТ: СЕКСУАЛЬНЫЙ ПРОФАЙЛ</b>\n\n"
        f"24 вопроса о ваших предпочтениях, фетишах и готовности к экспериментам.\n\n"
        f"<b>Что вы узнаете:</b>\n"
        f"• Ваш сексуальный темперамент (Хищник, Художник, Наблюдатель, Игрок)\n"
        f"• Топ-3 ваших скрытых фетиша\n"
        f"• Какие форматы вам подходят (МЖМ, ЖМЖ, BDSM и др.)\n"
        f"• Идеальный сценарий специально для вас\n\n"
        f"📊 <b>Вопросов:</b> 24\n"
        f"⏱ <b>Время:</b> ~7 минут\n\n"
        f"<i>Отвечайте честно — это поможет вам лучше понять себя.</i>"
    )
    
    keyboard = [[InlineKeyboardButton("▶️ Начать тест", callback_data="sexual_start")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(intro_text, reply_markup=reply_markup, parse_mode="HTML")
    return SEXUAL_TEST

async def sexual_ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Задаёт вопрос сексуального теста"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    current = context.user_data.get("sexual_current", 0)
    
    logger.info(f"📝 sexual_ask_question для пользователя {user_id}: current={current}")
    
    if current >= len(SEXUAL_QUESTIONS):
        logger.info(f"🏁 Все вопросы заданы для пользователя {user_id}, завершаем тест")
        return await sexual_finish(update, context)
    
    question = SEXUAL_QUESTIONS[current]
    progress = calculate_progress(current + 1, len(SEXUAL_QUESTIONS))
    
    # Определяем блок для отображения
    blocks = {
        "temperament": "ТЕМПЕРАМЕНТ",
        "fetishes": "ФЕТИШИ",
        "formats": "ФОРМАТЫ"
    }
    block_name = blocks.get(question["block"], "")
    
    question_text = (
        f"🔞 <b>СЕКСУАЛЬНЫЙ ПРОФАЙЛ: {block_name}</b>\n\n"
        f"<b>{question['text']}</b>\n\n"
        f"{progress}"
    )
    
    keyboard = []
    
    for option_id, option in question["options"].items():
        unique_callback = generate_unique_callback("sexual", user_id, current, option_id)
        keyboard.append([
            InlineKeyboardButton(option["text"], callback_data=unique_callback)
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        if hasattr(query, 'message') and query.message:
            await query.edit_message_text(
                question_text, 
                reply_markup=reply_markup, 
                parse_mode="HTML"
            )
            logger.info(f"✅ Вопрос {current+1}/{len(SEXUAL_QUESTIONS)} отправлен пользователю {user_id}")
    except Exception as e:
        logger.error(f"Ошибка при редактировании: {e}")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=question_text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    
    return SEXUAL_TEST

async def sexual_handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ответа сексуального теста"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    try:
        await query.answer()
    except Exception as e:
        logger.error(f"Ошибка при answer(): {e}")
    
    if context.user_data.get("sexual_processing", False):
        logger.debug(f"Пользователь {user_id}: пропускаем повторное нажатие")
        return SEXUAL_TEST
    
    context.user_data["sexual_processing"] = True
    
    try:
        parts = query.data.split("_")
        
        if len(parts) < 3 or parts[0] != "sexual":
            logger.error(f"Неверный формат callback: {query.data}")
            return SEXUAL_TEST
        
        current = int(parts[1])
        option_id = parts[2]
        
        logger.info(f"📥 User {user_id}: получен ответ на вопрос {current}, option={option_id}")
        
        last_answered = context.user_data.get("sexual_last_answered", -1)
        if current <= last_answered:
            logger.debug(f"Вопрос {current} уже отвечен, пропускаем")
            return SEXUAL_TEST
        
        question = SEXUAL_QUESTIONS[current]
        selected_option = question["options"].get(option_id)
        
        if not selected_option:
            logger.error(f"Опция {option_id} не найдена в вопросе {current}")
            return SEXUAL_TEST
        
        # Добавляем баллы
        block = question["block"]
        scores = selected_option.get("scores", {})
        
        for key, value in scores.items():
            if key in context.user_data["sexual_scores"][block]:
                context.user_data["sexual_scores"][block][key] += value
                logger.info(f"   +{value} к {block}.{key}")
            else:
                # Проверяем другие блоки (для форматов)
                for b in ["temperament", "fetishes", "formats"]:
                    if key in context.user_data["sexual_scores"][b]:
                        context.user_data["sexual_scores"][b][key] += value
                        logger.info(f"   +{value} к {b}.{key}")
                        break
        
        context.user_data["sexual_last_answered"] = current
        context.user_data["sexual_current"] = current + 1
        
        return await sexual_ask_question(update, context)
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
        return await sexual_ask_question(update, context)
    finally:
        context.user_data["sexual_processing"] = False

async def sexual_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершение сексуального теста - показ результатов"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    logger.info(f"🎯 sexual_finish вызван для пользователя {user_id}")
    
    scores = context.user_data.get("sexual_scores", {})
    
    # Форматируем результат
    result_text = format_sexual_profile(
        scores["temperament"],
        scores["fetishes"],
        scores["formats"]
    )
    
    # Кнопки для дальнейших действий
    keyboard = [
        [InlineKeyboardButton("📥 Полный разбор (590₽)", callback_data="sexual_premium")],
        [InlineKeyboardButton("◀️ В главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем результат (может быть длинным, разбиваем если нужно)
    if len(result_text) > 4000:
        parts = [result_text[i:i+4000] for i in range(0, len(result_text), 4000)]
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                await query.message.reply_text(part, parse_mode="HTML", reply_markup=reply_markup)
            else:
                await query.message.reply_text(part, parse_mode="HTML")
    else:
        await query.edit_message_text(result_text, parse_mode="HTML", reply_markup=reply_markup)
    
    return SEXUAL_RESULTS

async def sexual_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Покупка премиум-версии"""
    query = update.callback_query
    await query.answer()
    
    premium_text = """
<b>🔞 ПОЛНЫЙ РАЗБОР СЕКСУАЛЬНОГО ПРОФАЙЛА</b>

📖 <b>ЧАСТЬ 1: ГЛУБОКАЯ ДИАГНОСТИКА</b>
• Детальный разбор вашего темперамента (15 аспектов)
• Все ваши фетиши с объяснением (не только топ-3)
• Полная карта ваших форматов с готовностью

📖 <b>ЧАСТЬ 2: 50 КОНКРЕТНЫХ СЦЕНАРИЕВ</b>
• 10 сценариев для вашего темперамента
• 10 сценариев под ваши фетиши
• 10 сценариев для новых форматов
• 10 ролевых игр с диалогами
• 10 быстрых идей на 15 минут

📖 <b>ЧАСТЬ 3: ГАЙД ПО ИДЕАЛЬНОМУ ПАРТНЁРУ</b>
• Как найти партнёра под ваш тип
• Как разговаривать о своих желаниях
• Таблица совместимости со всеми типами

📖 <b>ЧАСТЬ 4: 10-ДНЕВНЫЙ ЧЕЛЛЕНДЖ</b>
• День 1: Арома-вечер
• День 2: Фокус на часть тела
• День 3: Ролевая игра
• И так далее...

📖 <b>ЧАСТЬ 5: МЕДИА-ГАЙД</b>
• 20 фильмов, которые вас заведут
• 15 книг для настроения
• 10 подкастов о сексе
• Плейлист для вашего типа

💰 <b>Цена: 590 ₽</b>

💳 <i>Оплата через ЮKassa — безопасно и удобно</i>
    """
    
    keyboard = [
        [InlineKeyboardButton("💳 Оплатить 590₽", callback_data="sexual_payment")],
        [InlineKeyboardButton("◀️ Назад", callback_data="sexual_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(premium_text, parse_mode="HTML", reply_markup=reply_markup)
    return SEXUAL_RESULTS

# Экспорт
__all__ = [
    'SEXUAL_TEST', 'SEXUAL_RESULTS',
    'sexual_test_start', 'sexual_ask_question',
    'sexual_handle_answer', 'sexual_finish', 'sexual_premium'
]
