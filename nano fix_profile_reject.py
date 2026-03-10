#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для автоматической замены функции profile_reject
Запуск: python fix_profile_reject.py
"""

import re
import os
import shutil
from datetime import datetime

def backup_file(filename):
    """Создает резервную копию файла"""
    backup_name = f"{filename}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(filename, backup_name)
    print(f"✅ Создана резервная копия: {backup_name}")
    return backup_name

def find_main_file():
    """Ищет основной файл бота"""
    possible_names = [
        "bot3.py",
        "main.py",
        "bot.py",
        "fredi.py",
        "psychologist_bot.py",
        "virtual_psychologist.py",
        "app.py"
    ]
    
    for name in possible_names:
        if os.path.exists(name):
            print(f"✅ Найден файл: {name}")
            return name
    
    py_files = [f for f in os.listdir('.') if f.endswith('.py')]
    for file in py_files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read(5000)
                if 'profile_reject' in content and 'TestStates' in content:
                    print(f"✅ Найден файл: {file} (содержит profile_reject)")
                    return file
        except:
            continue
    
    print("❌ Не удалось найти основной файл бота")
    return None

def create_new_profile_reject_function():
    """Создает новую функцию profile_reject"""
    return '''async def profile_reject(callback: CallbackQuery, state: FSMContext):
    """Пользователь полностью не согласен - показываем анекдот"""
    
    await callback.answer("🔄 Хорошо, попробуем иначе...")
    
    # Очищаем данные теста
    await state.clear()
    
    # Текст с анекдотом
    anecdote = (
        "🧠 <b>ЧЕСТНОСТЬ - ЛУЧШАЯ ПОЛИТИКА</b>\\n\\n"
        "Две подруги решили сходить на ипподром. Приходят, а там скачки, все ставки делают. "
        "Решили и они ставку сделать — вдруг повезёт? Одна другой и говорит: «Слушай, у тебя какой размер груди?». "
        "Вторая: «Второй… а у тебя?». Первая: «Третий… ну давай на пятую поставим — чтоб сумма была…».\\n\\n"
        "Поставили на пятую, лошадь приходит первая, они счастливые прибегают домой с деньгами и мужьям рассказывают, как было дело.\\n\\n"
        "На следующий день мужики тоже решили сходить на скачки — а вдруг им повезёт? Когда решали, на какую ставить, "
        "один говорит: «Ты сколько раз за ночь свою жену можешь удовлетворить?». Другой говорит: «Ну, три…». "
        "Первый: «А я четыре… ну давай на седьмую поставим».\\n\\n"
        "Поставили на седьмую, первой пришла вторая.\\n\\n"
        "Мужики переглянулись: «Не напиздили бы — выиграли…».\\n\\n"
        "<b>Мораль:</b> Если врать в тесте — результат будет как у мужиков на скачках. Хотите попробовать еще раз?"
    )
    
    # Кнопки: "🔄 Пройти тест еще раз" и "👋 Досвидули"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 ПРОЙТИ ТЕСТ ЕЩЕ РАЗ", callback_data="restart_test")],
        [InlineKeyboardButton(text="👋 ДОСВИДУЛИ", callback_data="goodbye")]
    ])
    
    await safe_send_message(
        callback.message,
        anecdote,
        reply_markup=keyboard,
        parse_mode='HTML',
        delete_previous=True
    )'''

def create_goodbye_function():
    """Создает функцию handle_goodbye"""
    return '''async def handle_goodbye(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки Досвидули"""
    
    await callback.answer("👋 Пока-пока! Возвращайтесь, если передумаете...")
    
    # Отправляем прощальное сообщение
    await safe_send_message(
        callback.message,
        "👋 <b>До свидания!</b>\\n\\nБуду рад помочь, если решите вернуться. Просто напишите /start",
        parse_mode='HTML',
        delete_previous=True
    )
    
    # Очищаем состояние
    await state.clear()'''

def fix_callback_handler(content):
    """Добавляет обработчик goodbye в callback_handler"""
    
    pattern = r'(async def callback_handler.*?)(elif data == "profile_reject":.*?await profile_reject\(callback, state\))(.*?)(?=\n\s*elif|\n\s*except|\n\s*$)'
    replacement = r'\1\2\n    \n    elif data == "goodbye":\n        await handle_goodbye(callback, state)\3'
    
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    if new_content == content:
        pattern2 = r'(elif data == "profile_reject":.*?await profile_reject\(callback, state\))(.*?)(?=\n\s*elif|\n\s*except)'
        replacement2 = r'\1\n    \n    elif data == "goodbye":\n        await handle_goodbye(callback, state)\2'
        new_content = re.sub(pattern2, replacement2, content, flags=re.DOTALL)
    
    return new_content

def main():
    """Главная функция"""
    
    print("🔍 Поиск основного файла бота...")
    filename = find_main_file()
    
    if not filename:
        print("❌ Файл не найден. Укажите имя файла вручную:")
        filename = input("Имя файла: ").strip()
        if not os.path.exists(filename):
            print(f"❌ Файл {filename} не найден!")
            return
    
    backup_file(filename)
    
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    old_pattern = r'async def profile_reject\(.*?\).*?await back_to_intro\(callback\).*?(?=\n\s*async def|\n\s*def|\n\s*$)'
    
    if re.search(old_pattern, content, flags=re.DOTALL):
        new_function = create_new_profile_reject_function()
        content = re.sub(old_pattern, new_function, content, flags=re.DOTALL)
        print("✅ Функция profile_reject заменена")
    else:
        print("❌ Старая функция profile_reject не найдена!")
        simple_pattern = r'(async def profile_reject\(callback: CallbackQuery, state: FSMContext\):.*?)(?=\n\s*async def|\n\s*def|\n\s*$)'
        if re.search(simple_pattern, content, flags=re.DOTALL):
            new_function = create_new_profile_reject_function()
            content = re.sub(simple_pattern, new_function, content, flags=re.DOTALL)
            print("✅ Функция profile_reject заменена")
    
    if 'async def handle_goodbye' not in content:
        goodbye_func = create_goodbye_function()
        if 'async def main' in content:
            content = content.replace('async def main', f'{goodbye_func}\n\n\nasync def main')
            print("✅ Функция handle_goodbye добавлена")
        else:
            content += f'\n\n\n{goodbye_func}'
            print("✅ Функция handle_goodbye добавлена в конец файла")
    
    new_content = fix_callback_handler(content)
    if new_content != content:
        content = new_content
        print("✅ Обработчик goodbye добавлен в callback_handler")
    else:
        print("⚠️ Не удалось автоматически добавить обработчик в callback_handler")
        print("   Добавьте вручную:")
        print('   elif data == "goodbye":')
        print('       await handle_goodbye(callback, state)')
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n🎉 Все изменения применены к файлу {filename}!")

if __name__ == "__main__":
    main()
