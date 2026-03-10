#!/usr/bin/env python3
"""
Скрипт для добавления обработчика длинных сообщений в bot3.py
Просто запустите: python3 add_handler.py
"""

import re
from pathlib import Path
from datetime import datetime

def main():
    bot_file = Path("bot3.py")
    
    if not bot_file.exists():
        print("❌ Файл bot3.py не найден!")
        return False
    
    # Читаем содержимое
    content = bot_file.read_text(encoding='utf-8')
    
    # Проверяем, есть ли уже функции
    if "def split_long_message" in content:
        print("⚠️ Функции уже существуют. Обновляем...")
    
    # Создаем бэкап
    backup = bot_file.with_suffix(f".py.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    bot_file.rename(backup)
    print(f"✅ Создан бэкап: {backup}")
    
    # Новые функции
    new_functions = '''

# ============================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С ДЛИННЫМИ СООБЩЕНИЯМИ (СТРАХОВКА)
# ============================================

def split_long_message(text: str, max_length: int = 4000) -> list:
    """
    Разбивает длинное сообщение на части по max_length символов,
    стараясь не разрывать слова и абзацы.
    """
    if len(text) <= max_length:
        return [text]
    
    parts = []
    current_part = ""
    
    # Разбиваем по абзацам (двойной перенос строки)
    paragraphs = text.split('\\n\\n')
    
    for para in paragraphs:
        # Если абзац сам по себе слишком длинный
        if len(para) > max_length:
            # Разбиваем по предложениям
            import re
            sentences = re.split(r'(?<=[.!?])\\s+', para)
            for sent in sentences:
                if len(current_part) + len(sent) + 2 <= max_length:
                    if current_part:
                        current_part += "\\n\\n" + sent
                    else:
                        current_part = sent
                else:
                    if current_part:
                        parts.append(current_part)
                    # Если предложение слишком длинное, режем принудительно
                    if len(sent) > max_length:
                        # Режем по словам
                        words = sent.split()
                        temp = ""
                        for word in words:
                            if len(temp) + len(word) + 1 <= max_length:
                                if temp:
                                    temp += " " + word
                                else:
                                    temp = word
                            else:
                                parts.append(temp)
                                temp = word
                        if temp:
                            current_part = temp
                        else:
                            current_part = ""
                    else:
                        current_part = sent
        else:
            if len(current_part) + len(para) + 2 <= max_length:
                if current_part:
                    current_part += "\\n\\n" + para
                else:
                    current_part = para
            else:
                if current_part:
                    parts.append(current_part)
                current_part = para
    
    if current_part:
        parts.append(current_part)
    
    return parts


async def safe_send_long_message(message, text: str, reply_markup=None, parse_mode: str = 'HTML', delete_previous: bool = True):
    """
    Безопасно отправляет длинные сообщения, разбивая их на части
    """
    # Удаляем предыдущее сообщение только если оно есть и мы хотим его удалить
    if delete_previous:
        try:
            await message.delete()
        except Exception as e:
            if "message can't be deleted" not in str(e).lower() and "message to delete not found" not in str(e).lower():
                logger.warning(f"Не удалось удалить сообщение: {e}")
    
    # Разбиваем длинное сообщение
    parts = split_long_message(text)
    
    first_message = None
    for i, part in enumerate(parts):
        try:
            if i == 0:
                # Первая часть с клавиатурой
                first_message = await message.answer(part, reply_markup=reply_markup, parse_mode=parse_mode)
            else:
                # Остальные части без клавиатуры
                await message.answer(part, parse_mode=parse_mode)
        except Exception as e:
            if "can't parse entities" in str(e).lower():
                # Если ошибка парсинга, отправляем без форматирования
                clean_part = clean_text_for_safe_display(part)
                if i == 0:
                    first_message = await message.answer(clean_part, reply_markup=reply_markup)
                else:
                    await message.answer(clean_part)
            else:
                logger.error(f"Ошибка при отправке части {i+1}: {e}")
                # Пробуем отправить без форматирования
                clean_part = clean_text_for_safe_display(part)
                if i == 0:
                    first_message = await message.answer(clean_part, reply_markup=reply_markup)
                else:
                    await message.answer(clean_part)
    
    return first_message
'''

    # Находим место для вставки (после clean_text_for_safe_display)
    clean_func_match = re.search(r'def clean_text_for_safe_display.*?\n\n', content, re.DOTALL)
    if clean_func_match:
        insert_pos = clean_func_match.end()
        content = content[:insert_pos] + new_functions + content[insert_pos:]
        print("✅ Функции split_long_message и safe_send_long_message добавлены")
    else:
        print("❌ Не найдена функция clean_text_for_safe_display")
        return False
    
    # Новая версия safe_send_message
    new_safe_send = '''
async def safe_send_message(message, text: str, reply_markup=None, parse_mode: str = 'HTML', delete_previous: bool = True):
    """Безопасно отправляет сообщение с проверкой длины"""
    
    # Проверяем длину сообщения
    if len(text) > 4000:
        logger.warning(f"⚠️ Сообщение слишком длинное ({len(text)} символов). Разбиваем на части.")
        return await safe_send_long_message(message, text, reply_markup, parse_mode, delete_previous)
    
    # Удаляем предыдущее сообщение с обработкой ошибки "не найдено"
    if delete_previous:
        try:
            await message.delete()
        except Exception as e:
            if "message can't be deleted" not in str(e).lower() and "message to delete not found" not in str(e).lower():
                logger.warning(f"Не удалось удалить сообщение: {e}")
    
    try:
        return await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception as e:
        if "can't parse entities" in str(e).lower():
            # Если ошибка парсинга, отправляем без форматирования
            clean_text = clean_text_for_safe_display(text)
            return await message.answer(clean_text, reply_markup=reply_markup)
        elif "message is too long" in str(e).lower():
            # Если сообщение слишком длинное, разбиваем
            logger.warning(f"⚠️ Telegram вернул ошибку 'message is too long'. Разбиваем на части.")
            return await safe_send_long_message(message, text, reply_markup, parse_mode, False)
        raise
'''
    
    # Заменяем существующую safe_send_message
    safe_send_pattern = r'async def safe_send_message.*?\):.*?(?=\n\S|\Z)'
    safe_send_match = re.search(safe_send_pattern, content, re.DOTALL)
    
    if safe_send_match:
        content = content.replace(safe_send_match.group(0), new_safe_send.strip())
        print("✅ Функция safe_send_message обновлена")
    else:
        print("❌ Не найдена функция safe_send_message")
        return False
    
    # Сохраняем изменения
    bot_file.write_text(content, encoding='utf-8')
    print(f"✅ Файл {bot_file} успешно обновлен!")
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Готово! Теперь бот будет разбивать длинные сообщения на части.")
    else:
        print("\n❌ Произошла ошибка. Проверьте файл bot3.py")
