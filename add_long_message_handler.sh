#!/bin/bash

# Файл для обновления
BOT_FILE="bot3.py"

# Проверяем, существует ли файл
if [ ! -f "$BOT_FILE" ]; then
    echo "❌ Файл $BOT_FILE не найден!"
    exit 1
fi

# Создаем бэкап
cp "$BOT_FILE" "${BOT_FILE}.backup_$(date +%Y%m%d_%H%M%S)"
echo "✅ Создан бэкап"

# Проверяем, есть ли уже функции
if grep -q "def split_long_message" "$BOT_FILE"; then
    echo "⚠️ Функции уже существуют. Пропускаем..."
    exit 0
fi

# Находим место для вставки (после функций форматирования)
LINE_NUM=$(grep -n "def clean_text_for_safe_display" "$BOT_FILE" | cut -d: -f1)

if [ -z "$LINE_NUM" ]; then
    echo "❌ Не найдено место для вставки"
    exit 1
fi

# Создаем временный файл с новыми функциями
cat > /tmp/new_functions.txt << 'EOF'


# ============================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С ДЛИННЫМИ СООБЩЕНИЯМИ (СТРАХОВКА)
# ============================================

def split_long_message(text: str, max_length: int = 4000) -> List[str]:
    """
    Разбивает длинное сообщение на части по max_length символов,
    стараясь не разрывать слова и абзацы.
    """
    if len(text) <= max_length:
        return [text]
    
    parts = []
    current_part = ""
    
    # Разбиваем по абзацам (двойной перенос строки)
    paragraphs = text.split('\n\n')
    
    for para in paragraphs:
        # Если абзац сам по себе слишком длинный
        if len(para) > max_length:
            # Разбиваем по предложениям
            sentences = re.split(r'(?<=[.!?])\s+', para)
            for sent in sentences:
                if len(current_part) + len(sent) + 2 <= max_length:
                    if current_part:
                        current_part += "\n\n" + sent
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
                    current_part += "\n\n" + para
                else:
                    current_part = para
            else:
                if current_part:
                    parts.append(current_part)
                current_part = para
    
    if current_part:
        parts.append(current_part)
    
    return parts


async def safe_send_long_message(message: Message, text: str, reply_markup=None, parse_mode: str = 'HTML', delete_previous: bool = True):
    """
    Безопасно отправляет длинные сообщения, разбивая их на части
    """
    # Удаляем предыдущее сообщение только если оно есть и мы хотим его удалить
    if delete_previous:
        try:
            await message.delete()
        except TelegramBadRequest as e:
            if "message can't be deleted" not in str(e).lower() and "message to delete not found" not in str(e).lower():
                logger.warning(f"Не удалось удалить сообщение: {e}")
        except Exception as e:
            logger.warning(f"Ошибка при удалении сообщения: {e}")
    
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
        except TelegramBadRequest as e:
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
EOF

# Вставляем функции после clean_text_for_safe_display
awk -v line="$LINE_NUM" 'NR==line {print; system("cat /tmp/new_functions.txt"); next} 1' "$BOT_FILE" > "${BOT_FILE}.tmp"
mv "${BOT_FILE}.tmp" "$BOT_FILE"

echo "✅ Функции добавлены!"

# Теперь обновляем safe_send_message
# Находим существующую функцию
MSG_LINE=$(grep -n "async def safe_send_message" "$BOT_FILE" | head -1 | cut -d: -f1)

if [ ! -z "$MSG_LINE" ]; then
    # Создаем новую версию функции
    cat > /tmp/new_safe_send.txt << 'EOF'

async def safe_send_message(message: Message, text: str, reply_markup=None, parse_mode: str = 'HTML', delete_previous: bool = True):
    """Безопасно отправляет сообщение с проверкой длины"""
    
    # Проверяем длину сообщения
    if len(text) > 4000:
        logger.warning(f"⚠️ Сообщение слишком длинное ({len(text)} символов). Разбиваем на части.")
        return await safe_send_long_message(message, text, reply_markup, parse_mode, delete_previous)
    
    # Удаляем предыдущее сообщение с обработкой ошибки "не найдено"
    if delete_previous:
        try:
            await message.delete()
        except TelegramBadRequest as e:
            if "message can't be deleted" not in str(e).lower() and "message to delete not found" not in str(e).lower():
                logger.warning(f"Не удалось удалить сообщение: {e}")
        except Exception as e:
            logger.warning(f"Ошибка при удалении сообщения: {e}")
    
    try:
        return await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except TelegramBadRequest as e:
        if "can't parse entities" in str(e).lower():
            # Если ошибка парсинга, отправляем без форматирования
            clean_text = clean_text_for_safe_display(text)
            return await message.answer(clean_text, reply_markup=reply_markup)
        elif "message is too long" in str(e).lower():
            # Если сообщение слишком длинное, разбиваем
            logger.warning(f"⚠️ Telegram вернул ошибку 'message is too long'. Разбиваем на части.")
            return await safe_send_long_message(message, text, reply_markup, parse_mode, False)
        raise
EOF

    # Заменяем функцию (удаляем старую и вставляем новую)
    sed -i "${MSG_LINE},/^async def/c\\$(cat /tmp/new_safe_send.txt)" "$BOT_FILE"
    echo "✅ safe_send_message обновлена!"
else
    echo "⚠️ Функция safe_send_message не найдена. Добавьте её вручную."
fi

echo "🎉 Готово! Проверьте файл $BOT_FILE"
