"""
Обработчики для сексуального теста (aiogram version)
"""

import logging
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

logger = logging.getLogger(__name__)

# Импортируем вопросы
try:
    from sexual_questions import SEXUAL_QUESTIONS
    logger.info(f"✅ Загружено {len(SEXUAL_QUESTIONS)} вопросов")
except Exception as e:
    logger.error(f"❌ Ошибка загрузки вопросов: {e}")
    SEXUAL_QUESTIONS = []

# Импортируем интерпретации
try:
    from sexual_interpretations import format_sexual_profile
    logger.info(f"✅ Загружены интерпретации")
except Exception as e:
    logger.error(f"❌ Ошибка загрузки интерпретаций: {e}")
    
    def format_sexual_profile(a, b, c):
        return "Сексуальный профиль временно недоступен"

async def sexual_test_start(callback: types.CallbackQuery, state: FSMContext):
    """Начало сексуального теста"""
    await callback.answer()
    
    user_id = callback.from_user.id
    logger.info(f"🔞 sexual_test_start для пользователя {user_id}")
    
    # Инициализируем данные для теста
    await state.update_data(
        sexual_current=0,
        sexual_last_answered=-1,
        sexual_processing=False,
        sexual_scores={
            "temperament": {"PREDATOR": 0, "ARTIST": 0, "OBSERVER": 0, "PLAYER": 0},
            "fetishes": {"SMELL": 0, "MATERIALS": 0, "BODY_PARTS": 0, "SITUATIONS": 0},
            "formats": {
                "MHM": 0, "HWH": 0, "SWING": 0, "BDSM_DOM": 0, "BDSM_SUB": 0,
                "BDSM_LIGHT": 0, "ROLE_PLAY": 0, "RISK": 0, "TOYS": 0, "VIDEO": 0,
                "VIRTUAL": 0, "MONO": 0, "TRADITION": 0, "ADAPT": 0
            }
        }
    )
    
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
    
    builder = InlineKeyboardBuilder()
    builder.button(text="▶️ Начать тест", callback_data="sexual_ask_0")
    builder.adjust(1)
    
    # Удаляем предыдущее сообщение
    try:
        await callback.message.delete()
    except:
        pass
    
    await callback.message.answer(intro_text, reply_markup=builder.as_markup())

async def sexual_ask_question(callback: types.CallbackQuery, state: FSMContext):
    """Задаёт вопрос сексуального теста"""
    await callback.answer()
    
    data = await state.get_data()
    current = data.get('sexual_current', 0)
    
    logger.info(f"📝 sexual_ask_question: current={current}")
    
    if current >= len(SEXUAL_QUESTIONS):
        logger.info(f"🏁 Все вопросы заданы, завершаем тест")
        await sexual_finish(callback, state)
        return
    
    question = SEXUAL_QUESTIONS[current]
    
    # Прогресс-бар
    progress = get_progress_bar(current + 1, len(SEXUAL_QUESTIONS))
    
    # Определяем блок для отображения
    blocks = {
        "temperament": "ТЕМПЕРАМЕНТ",
        "fetishes": "ФЕТИШИ",
        "formats": "ФОРМАТЫ"
    }
    block_name = blocks.get(question.get("block", ""), "")
    
    question_text = (
        f"🔞 <b>СЕКСУАЛЬНЫЙ ПРОФАЙЛ: {block_name}</b>\n\n"
        f"<b>Вопрос {current+1}/{len(SEXUAL_QUESTIONS)}</b>\n"
        f"<code>{progress}</code>\n\n"
        f"<b>{question['text']}</b>"
    )
    
    builder = InlineKeyboardBuilder()
    
    for option_id, option in question["options"].items():
        # callback_data: sexual_ans_0_a
        builder.button(
            text=option["text"], 
            callback_data=f"sexual_ans_{current}_{option_id}"
        )
    
    builder.adjust(1)
    
    # Удаляем предыдущее сообщение
    try:
        await callback.message.delete()
    except:
        pass
    
    await callback.message.answer(question_text, reply_markup=builder.as_markup())

async def sexual_handle_answer(callback: types.CallbackQuery, state: FSMContext):
    """Обработка ответа сексуального теста"""
    await callback.answer()
    
    data = await state.get_data()
    
    # Проверяем, не обрабатывается ли уже ответ
    if data.get('sexual_processing', False):
        logger.debug("Пропускаем повторное нажатие")
        return
    
    await state.update_data(sexual_processing=True)
    
    try:
        # Парсим callback_data: sexual_ans_0_a
        parts = callback.data.split('_')
        if len(parts) < 4 or parts[0] != "sexual" or parts[1] != "ans":
            logger.error(f"Неверный формат callback: {callback.data}")
            return
        
        current = int(parts[2])
        option_id = parts[3]
        
        logger.info(f"📥 Получен ответ на вопрос {current}, option={option_id}")
        
        # Проверяем, не отвечали ли уже на этот вопрос
        last_answered = data.get('sexual_last_answered', -1)
        if current <= last_answered:
            logger.debug(f"Вопрос {current} уже отвечен, пропускаем")
            return
        
        question = SEXUAL_QUESTIONS[current]
        selected_option = question["options"].get(option_id)
        
        if not selected_option:
            logger.error(f"Опция {option_id} не найдена в вопросе {current}")
            return
        
        # Получаем текущие баллы
        scores = data.get('sexual_scores', {
            "temperament": {"PREDATOR": 0, "ARTIST": 0, "OBSERVER": 0, "PLAYER": 0},
            "fetishes": {"SMELL": 0, "MATERIALS": 0, "BODY_PARTS": 0, "SITUATIONS": 0},
            "formats": {
                "MHM": 0, "HWH": 0, "SWING": 0, "BDSM_DOM": 0, "BDSM_SUB": 0,
                "BDSM_LIGHT": 0, "ROLE_PLAY": 0, "RISK": 0, "TOYS": 0, "VIDEO": 0,
                "VIRTUAL": 0, "MONO": 0, "TRADITION": 0, "ADAPT": 0
            }
        })
        
        # Добавляем баллы
        block = question.get("block", "")
        option_scores = selected_option.get("scores", {})
        
        for key, value in option_scores.items():
            if block and key in scores.get(block, {}):
                scores[block][key] += value
                logger.info(f"   +{value} к {block}.{key}")
            else:
                # Ищем в других блоках
                for b in ["temperament", "fetishes", "formats"]:
                    if key in scores.get(b, {}):
                        scores[b][key] += value
                        logger.info(f"   +{value} к {b}.{key}")
                        break
        
        # Обновляем состояние
        await state.update_data(
            sexual_scores=scores,
            sexual_last_answered=current,
            sexual_current=current + 1,
            sexual_processing=False
        )
        
        # Задаём следующий вопрос
        await sexual_ask_question(callback, state)
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}", exc_info=True)
        await state.update_data(sexual_processing=False)
        await sexual_ask_question(callback, state)

async def sexual_finish(callback: types.CallbackQuery, state: FSMContext):
    """Завершение сексуального теста - показ результатов"""
    await callback.answer()
    
    data = await state.get_data()
    scores = data.get('sexual_scores', {})
    
    logger.info(f"🎯 sexual_finish: расчёт результатов")
    
    # Форматируем результат
    try:
        result_text = format_sexual_profile(
            scores.get("temperament", {}),
            scores.get("fetishes", {}),
            scores.get("formats", {})
        )
    except Exception as e:
        logger.error(f"Ошибка форматирования: {e}")
        result_text = "❌ Ошибка при формировании результатов. Пожалуйста, попробуйте позже."
    
    # Кнопки для дальнейших действий
    builder = InlineKeyboardBuilder()
    builder.button(text="📥 Полный разбор (590₽)", callback_data="sexual_premium")
    builder.button(text="◀️ В главное меню", callback_data="restart")
    builder.adjust(1)
    
    # Удаляем предыдущее сообщение
    try:
        await callback.message.delete()
    except:
        pass
    
    # Отправляем результат (разбиваем если длинный)
    if len(result_text) > 4000:
        parts = [result_text[i:i+4000] for i in range(0, len(result_text), 4000)]
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                await callback.message.answer(part, reply_markup=builder.as_markup())
            else:
                await callback.message.answer(part)
    else:
        await callback.message.answer(result_text, reply_markup=builder.as_markup())

async def sexual_premium(callback: types.CallbackQuery, state: FSMContext):
    """Покупка премиум-версии"""
    await callback.answer()
    
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
    
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Оплатить 590₽", callback_data="sexual_payment")
    builder.button(text="◀️ Назад", callback_data="sexual_back")
    builder.adjust(1)
    
    try:
        await callback.message.edit_text(premium_text, reply_markup=builder.as_markup())
    except:
        await callback.message.delete()
        await callback.message.answer(premium_text, reply_markup=builder.as_markup())

def get_progress_bar(current, total, length=10):
    """Возвращает прогресс-бар"""
    filled = int((current / total) * length)
    return "█" * filled + "░" * (length - filled)

# Экспорт
__all__ = [
    'sexual_test_start', 'sexual_ask_question',
    'sexual_handle_answer', 'sexual_finish', 'sexual_premium'
]
