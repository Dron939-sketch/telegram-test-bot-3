#!/bin/bash

echo "🔧 ИСПРАВЛЕНИЕ ВСЕХ ОШИБОК БОТА"
echo "================================"

# 1. Исправляем Markdown во всех файлах
echo "📝 1. Исправляем Markdown..."
find . -name "*.py" -exec sed -i 's/<i>/_/g' {} \;
find . -name "*.py" -exec sed -i 's/<\/i>/_/g' {} \;
find . -name "*.py" -exec sed -i "s/\*\([^*]*\)\*/**\1**/g" {} \;

# 2. Исправляем callback_data
echo "🔄 2. Исправляем callback_data..."
sed -i 's/callback_data="start_test"/callback_data="start_context"/g' bot3.py

# 3. Исправляем импорты в models.py
echo "📦 3. Исправляем импорты..."
sed -i 's/from main import/from bot3 import/g' models.py

# 4. Добавляем обработку таймаутов
echo "⏱️ 4. Добавляем защиту от таймаутов..."
cat >> bot3.py << 'EOF'

# ===== ЗАЩИТА ОТ ТАЙМАУТОВ =====
async def safe_callback_answer(callback, text=None):
    try:
        if text:
            await callback.answer(text)
        else:
            await callback.answer()
    except Exception as e:
        if "request is too old" in str(e):
            print(f"⚠️ Пропущен устаревший callback")
        else:
            raise
EOF

# 5. Добавляем проверку API ключей
echo "🔑 5. Добавляем проверку API..."
cat >> services.py << 'EOF'

def check_api_keys():
    """Проверяет наличие всех необходимых ключей"""
    from config import DEEPSEEK_API_KEY, DEEPGRAM_API_KEY, YANDEX_API_KEY
    missing = []
    if not DEEPSEEK_API_KEY: missing.append("DEEPSEEK_API_KEY")
    if not DEEPGRAM_API_KEY: missing.append("DEEPGRAM_API_KEY") 
    if not YANDEX_API_KEY: missing.append("YANDEX_API_KEY")
    if missing:
        print(f"⚠️ Отсутствуют ключи: {', '.join(missing)}")
        return False
    return True
EOF

# 6. Добавляем команду для сброса контекста
echo "🧹 6. Добавляем сброс контекста..."
cat >> bot3.py << 'EOF'

async def cmd_reset_context(message: Message, state: FSMContext):
    """Сбрасывает контекст пользователя"""
    user_id = message.from_user.id
    if user_id in user_contexts:
        user_contexts[user_id].city = None
        user_contexts[user_id].gender = None
        user_contexts[user_id].age = None
        await message.answer("✅ Контекст сброшен! Теперь можете начать заново.")
    else:
        await message.answer("❌ Контекст не найден")
EOF

# 7. Регистрируем новую команду
echo "➕ 7. Добавляем команду /reset_context"
sed -i '/dp.message.register(cmd_context/a \ \ \ \ dp.message.register(cmd_reset_context, Command("reset_context"))' bot3.py

echo "✅ ВСЕ ИСПРАВЛЕНИЯ ПРИМЕНЕНЫ!"
echo "🚀 Перезапустите бота командой: python3 bot3.py"
