"""
Обработчики команды /start и начальных экранов
"""
import asyncio
import logging
import os
import re

import httpx
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from models import UserContext
from config import COMMUNICATION_MODES
from keyboards import (
    get_restart_keyboard, get_main_menu_keyboard, get_why_details_keyboard
)
from utils import is_test_completed
from formatters import bold
from bot_instance import (
    user_names, user_contexts, stats, safe_send_message
)
from states import TestStates

logger = logging.getLogger(__name__)

FREDI_API_BASE = os.environ.get("FREDI_API_BASE", "https://fredi-backend-flz2.onrender.com")


async def _link_web_user(web_user_id: int, chat_id: int, username: str | None) -> bool:
    """Связывает web_user_id с Telegram chat_id через бэкенд Фреди."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                f"{FREDI_API_BASE}/api/messenger/link",
                json={
                    "user_id": int(web_user_id),
                    "platform": "telegram",
                    "chat_id": str(chat_id),
                    "username": username,
                },
            )
            data = r.json() if r.status_code == 200 else {}
            return bool(data.get("success"))
    except Exception as e:
        logger.error(f"link_web_user error: {e}")
        return False


async def cmd_start(message: Message, state: FSMContext):
    """Обновленный обработчик команды /start"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "Пользователь"

    # Deep-link payload: /start web_<id> — связываем web-пользователя с этим чатом
    text = message.text or ""
    m = re.match(r"^/start(?:@\w+)?\s+web_(\d+)\s*$", text)
    if m:
        web_user_id = int(m.group(1))
        ok = await _link_web_user(
            web_user_id=web_user_id,
            chat_id=message.chat.id,
            username=message.from_user.username,
        )
        if ok:
            await safe_send_message(
                message,
                f"✅ {bold('Аккаунт связан!')}\n\n"
                f"Теперь утренние сообщения от Фреди в 9:00 будут приходить сюда. "
                f"Хорошего дня, {user_name}!"
            )
            return
        else:
            await safe_send_message(
                message,
                "⚠️ Не удалось связать аккаунт. Попробуйте ещё раз позже или напишите в поддержку."
            )
            return

    # Извлекаем mirror_code до очистки state
    _m_mirror = re.match(r"^/start(?:@\w+)?\s+(mirror_\w+)\s*$", text)
    _mirror_code = _m_mirror.group(1) if _m_mirror else None
    user_names[user_id] = user_name

    await state.clear()
    
    # Восстанавливаем mirror_code после очистки state
    if _mirror_code:
        await state.update_data(mirror_code=_mirror_code)
        logger.info(f"🪞 Mirror code saved: user={user_id}, code={_mirror_code}")
    
    if user_id not in user_contexts:
        user_contexts[user_id] = UserContext(user_id)
        user_contexts[user_id].name = user_name
    
    stats.register_start(user_id)
    
    context = user_contexts[user_id]
    
    # Проверяем, есть ли уже профиль
    data = await state.get_data()
    if is_test_completed(data):
        profile_code = data.get("profile_data", {}).get('display_name', 'СБ-4_ТФ-4_УБ-4_ЧВ-4')
        
        text = f"""
🧠 {bold('ФРЕДИ: ВИРТУАЛЬНЫЙ ПСИХОЛОГ')}

👋 О, {user_name}, я вас помню!
(У меня, в отличие от людей, с памятью всё отлично — спасибо базе данных)

📊 {bold('ВАШ ПРОФИЛЬ:')} {profile_code}
(Лежит у меня в архивах, пылится...)

❓ {bold('ЧТО ДЕЛАЕМ?')}

Вы можете:
🔄 Пройти тест заново — вдруг вы изменились?

⬇️ {bold('ВЫБИРАЙТЕ:')}
"""
        
        keyboard = get_restart_keyboard()
        
        await safe_send_message(message, text, reply_markup=keyboard)
        return
    
    # Проверяем, заполнен ли контекст
    if not (context.city and context.gender and context.age):
        welcome_text = (
            f"{user_name}, привет! Ну, здравствуйте, дорогой человек! 👋\n\n"
            f"🧠 {bold('Я — Фреди, виртуальный психолог.')}\n"
            f"Оцифрованная версия Андрея Мейстера, если хотите — его цифровой слепок.\n\n"
            f"🎭 Короче, я — это он, только батарейка дольше держит и пожрать не прошу.\n\n"
            f"🕒 Нам нужно познакомиться, потому что я пока не экстрасенс.\n\n"
            f"🧐 Чтобы я понимал, с кем имею дело и чем могу быть полезен —\n"
            f"давайте-ка пройдём небольшой тест.\n\n"
            f"📊 {bold('Всего 5 этапов:')}\n\n"
            f"1️⃣ Конфигурация восприятия — как вы фильтруете реальность\n"
            f"2️⃣ Конфигурация мышления — как ваш мозг перерабатывает информацию\n"
            f"3️⃣ Конфигурация поведения — что вы делаете на автопилоте\n"
            f"4️⃣ Точка роста — куда двигаться, чтобы не топтаться на месте\n"
            f"5️⃣ Глубинные паттерны — что сформировало вас как личность\n\n"
            f"⏱ {bold('15 минут')} — и я буду знать о вас больше, чем вы думаете.\n\n"
            f"🚀 Ну что, начнём наше знакомство?"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Давай, погнали!", callback_data="start_context")],
            [InlineKeyboardButton(text="🤨 А ты вообще кто такой?", callback_data="why_details")]
        ])
        
        await safe_send_message(message, welcome_text, reply_markup=keyboard)
        return
    
    # Если контекст уже заполнен, показываем меню
    from .modes import show_main_menu
    await show_main_menu(message, context)


async def show_why_details(callback: CallbackQuery, state: FSMContext):
    """Показывает детальную информацию о боте"""
    
    text = f"""
🎭 {bold('Ну, вопрос хороший. Давайте по существу.')}

Видите ли, дорогой человек, я — экспериментальная модель.
Андрей Мейстер однажды подумал: "А что, если я создам свою цифровую копию?
Пусть работает, пока я сплю, ем или просто ленюсь".

Так я и появился. 🧠

🧐 {bold('Что я умею:')}

• Вижу паттерны там, где вы видите просто день сурка
• Нахожу систему в ваших "случайных" решениях
• Понимаю, почему вы выбираете одних и тех же "не тех" людей
• Я реально беспристрастен — у меня нет плохого настроения

🎯 {bold('Конкретно по тесту:')}

1️⃣ Восприятие — поймём, какую линзу вы носите
2️⃣ Мышление — узнаем, как вы пережёвываете реальность
3️⃣ Поведение — посмотрим, что вы делаете "на автомате"
4️⃣ Точка роста — я скажу, куда вам двигаться
5️⃣ Глубинные паттерны — заглянем в детство и подсознание

⏱ {bold('15 минут')} — и я составлю ваш профиль.

👌 Погнали?"""
    
    keyboard = get_why_details_keyboard()
    
    await safe_send_message(callback.message, text, reply_markup=keyboard, delete_previous=True)
    await callback.answer()
