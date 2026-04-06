"""
Утилиты для отправки сообщений
"""
import logging
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest

from formatters import clean_text_for_safe_display

logger = logging.getLogger(__name__)


async def safe_send_message(message: Message, text: str, reply_markup=None, parse_mode: str = 'HTML', delete_previous: bool = True):
    """Безопасно отправляет сообщение с HTML-разметкой и удаляет предыдущее"""
    
    # Удаляем предыдущее сообщение бота, если оно было
    if delete_previous and hasattr(message, 'message_id'):
        try:
            await message.delete()
        except TelegramBadRequest as e:
            if "message can't be deleted" not in str(e).lower():
                logger.warning(f"Не удалось удалить сообщение: {e}")
        except Exception as e:
            logger.warning(f"Ошибка при удалении сообщении: {e}")
    
    try:
        return await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except TelegramBadRequest as e:
        if "can't parse entities" in str(e).lower():
            # Если ошибка парсинга, отправляем без форматирования
            clean_text = clean_text_for_safe_display(text)
            return await message.answer(clean_text, reply_markup=reply_markup)
        raise


async def send_with_status_cleanup(message: Message, text: str, status_msg: Message = None, reply_markup=None, parse_mode: str = 'HTML'):
    """Отправляет сообщение и удаляет статусное сообщение"""
    
    # Удаляем статусное сообщение, если оно есть
    if status_msg:
        try:
            await status_msg.delete()
        except Exception:
            pass

    # Удаляем предыдущее сообщение бота
    try:
        await message.delete()
    except Exception:
        pass
    
    # Отправляем новое сообщение
    try:
        return await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except TelegramBadRequest as e:
        if "can't parse entities" in str(e).lower():
            clean_text = clean_text_for_safe_display(text)
            return await message.answer(clean_text, reply_markup=reply_markup)
        raise
