#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для автоматической очистки bot3.py от неиспользуемого кода
Запуск: python cleanup_bot.py
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

def remove_unused_imports(content):
    """Удаляет неиспользуемые импорты"""
    
    # Список импортов для удаления
    unused_imports = [
        r'from modes import get_available_modes, get_mode_description.*?\n',
        r'from test_questions import STAGE_2_SCORING, CLARIFYING_QUESTIONS, DISCREPANCY_QUESTIONS.*?\n',
        r'from test_questions import get_question_text, get_question_options, get_option_text, get_option_value.*?\n',
        r'from hypno_module import Anchoring.*?\n',
    ]
    
    for pattern in unused_imports:
        content = re.sub(pattern, '', content)
    
    print("✅ Удалены неиспользуемые импорты")
    return content

def remove_unused_functions(content):
    """Удаляет неиспользуемые функции"""
    
    # Паттерны для поиска неиспользуемых функций
    unused_functions = [
        (r'def should_be_ironic\(.*?\).*?(?=\n\s*def|\n\s*async def|\n\s*$)', 
         'should_be_ironic'),
        (r'def needs_clarification\(.*?\).*?(?=\n\s*def|\n\s*async def|\n\s*$)', 
         'needs_clarification'),
        (r'def check_consistency\(.*?\).*?(?=\n\s*def|\n\s*async def|\n\s*$)', 
         'check_consistency'),
        (r'def get_priority_order\(.*?\).*?(?=\n\s*def|\n\s*async def|\n\s*$)', 
         'get_priority_order'),
    ]
    
    removed = 0
    for pattern, name in unused_functions:
        if re.search(pattern, content, flags=re.DOTALL):
            content = re.sub(pattern, '', content, flags=re.DOTALL)
            print(f"  - Удалена функция {name}")
            removed += 1
    
    if removed > 0:
        print(f"✅ Удалено {removed} неиспользуемых функций")
    return content

def cleanup_fsm_states(content):
    """Удаляет неиспользуемые состояния FSM"""
    
    # Ищем класс TestStates
    class_pattern = r'(class TestStates\(StatesGroup\):.*?)(?=\n\s*#|\n\s*def|\n\s*$)'
    class_match = re.search(class_pattern, content, flags=re.DOTALL)
    
    if class_match:
        class_content = class_match.group(1)
        
        # Список состояний для удаления
        unused_states = [
            'clarifying_test',
            'alternative_test',
            'viewing_confinement',
            'viewing_intervention',
            'route_generation',
            'reality_check_active',
        ]
        
        for state in unused_states:
            # Удаляем строку с состоянием
            state_pattern = rf'\n\s*{state} = State\(\)'
            class_content = re.sub(state_pattern, '', class_content)
        
        # Заменяем в исходном контенте
        content = content.replace(class_match.group(1), class_content)
        print("✅ Очищены неиспользуемые состояния FSM")
    
    return content

def remove_unused_globals(content):
    """Удаляет неиспользуемые глобальные переменные"""
    
    # Удаляем user_routes если не используется
    if 'user_routes' in content and 'user_routes' not in content[content.find('user_routes'):]:
        content = re.sub(r'user_routes: Dict\[int, Dict\[str, Any\]\] = \{\}\n', '', content)
        print("✅ Удалена неиспользуемая глобальная переменная user_routes")
    
    # Удаляем hypno если не используется
    if 'hypno = HypnoOrchestrator()' in content and 'hypno.' not in content:
        content = re.sub(r'hypno = HypnoOrchestrator\(\)\n', '', content)
        print("✅ Удалена неиспользуемая переменная hypno")
    
    # Удаляем anchoring если не используется
    if 'anchoring = Anchoring()' in content and 'anchoring.' not in content:
        content = re.sub(r'anchoring = Anchoring\(\)\n', '', content)
        print("✅ Удалена неиспользуемая переменная anchoring")
    
    return content

def fix_send_message_usage(content):
    """Заменяет прямые message.answer на safe_send_message"""
    
    # Ищем все места с message.answer в handle_context_message
    pattern = r'(await message\.answer\(f?"📝 \{bold\(\'Давайте познакомимся\'\)\}\\\n\\n\{question\}",\s*reply_markup=keyboard\))'
    
    # Заменяем на safe_send_message
    replacement = 'await safe_send_message(\n        message,\n        f"📝 {bold(\'Давайте познакомимся\')}\\n\\n{question}",\n        reply_markup=keyboard,\n        parse_mode=\'HTML\',\n        delete_previous=True\n    )'
    
    content = re.sub(pattern, replacement, content)
    print("✅ Исправлены вызовы message.answer на safe_send_message")
    
    return content

def cleanup_duplicate_code(content):
    """Удаляет дублирующийся код"""
    
    # Удаляем show_destinations если не используется (используется show_dynamic_destinations)
    if 'async def show_destinations' in content and 'show_destinations' not in content[content.find('async def show_destinations'):]:
        pattern = r'async def show_destinations\(.*?\).*?(?=\n\s*async def|\n\s*def|\n\s*$)'
        content = re.sub(pattern, '', content, flags=re.DOTALL)
        print("✅ Удалена неиспользуемая функция show_destinations")
    
    return content

def main():
    """Главная функция"""
    
    filename = 'bot3.py'
    
    if not os.path.exists(filename):
        print(f"❌ Файл {filename} не найден!")
        alt = input("Введите имя файла: ").strip()
        if alt and os.path.exists(alt):
            filename = alt
        else:
            return
    
    # Создаем резервную копию
    backup_file(filename)
    
    # Читаем файл
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_length = len(content)
    
    # Применяем все очистки
    content = remove_unused_imports(content)
    content = remove_unused_functions(content)
    content = cleanup_fsm_states(content)
    content = remove_unused_globals(content)
    content = fix_send_message_usage(content)
    content = cleanup_duplicate_code(content)
    
    # Дополнительно: удаляем пустые строки, которые могли образоваться
    content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
    
    new_length = len(content)
    
    # Сохраняем изменения
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n🎉 Очистка завершена!")
    print(f"📊 Размер файла: {original_length} → {new_length} символов")
    print(f"📉 Удалено: {original_length - new_length} символов ({((original_length - new_length)/original_length*100):.1f}%)")
    print(f"📦 Резервная копия сохранена")

if __name__ == "__main__":
    main()
