#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
МОДУЛЬ 4: ИНТЕГРАЦИЯ С ОТВЕТАМИ (confinement_reporter.py)
Формирует отчеты и ответы на основе конфайнмент-модели
"""

from datetime import datetime
from typing import Optional, Dict, List, Any
import logging

# Импортируем необходимые классы из других модулей
from confinement_model import ConfinementModel9, ConfinementElement
from loop_analyzer import LoopAnalyzer
from key_confinement import KeyConfinementDetector

# Настройка логирования
logger = logging.getLogger(__name__)


class ConfinementReporter:
    """
    Формирует отчеты и ответы на основе конфайнмент-модели
    """
    
    def __init__(self, model: ConfinementModel9, user_name: str = "друг"):
        """
        Инициализация репортера
        
        Args:
            model: построенная конфайнмент-модель
            user_name: имя пользователя для обращений
        """
        self.model = model
        self.user_name = user_name
        self.loop_analyzer = LoopAnalyzer(model)
        self.loops = self.loop_analyzer.analyze()
        self.key_detector = KeyConfinementDetector(model, self.loops)
        self.key = self.key_detector.detect()
        
        logger.info(f"ConfinementReporter инициализирован для {user_name}")
    
    def get_summary(self) -> str:
        """
        Возвращает краткое резюме модели для быстрого понимания
        
        Returns:
            str: краткий отчет о модели
        """
        if not self.model.elements[1]:
            return "Модель еще не построена"
        
        lines = []
        
        # Заголовок
        lines.append(f"🧠 *КОНФАЙНМЕНТ-МОДЕЛЬ*\n")
        
        # Результат (главный симптом)
        result = self.model.elements[1]
        lines.append(f"🎯 *Результат:* {result.description[:100]}...\n")
        
        # Ключевой конфайнмент
        if self.key:
            lines.append(f"⛓ *Ключевое ограничение:*")
            lines.append(self.key['description'])
            lines.append("")
        
        # Петли
        if self.loops:
            strongest = self.loop_analyzer.get_strongest_loop()
            if strongest:
                lines.append(f"🔄 *Главная петля:*")
                lines.append(strongest['description'])
                lines.append(f"Сила: {strongest['impact']:.1%}")
                lines.append("")
        
        # Замыкание
        closure_status = "✅ замкнута" if self.model.is_closed else "🔄 не замкнута"
        lines.append(f"📊 *Система:* {closure_status} (степень {self.model.closure_score:.1%})")
        
        return "\n".join(lines)
    
    def get_detailed_report(self) -> str:
        """
        Возвращает детальный отчет по модели со всеми элементами
        
        Returns:
            str: подробный отчет о модели
        """
        lines = []
        
        lines.append(f"🧠 *ПОЛНАЯ КОНФАЙНМЕНТ-МОДЕЛЬ*\n")
        
        # Все элементы
        lines.append("**9 элементов системы:**\n")
        
        for i in range(1, 10):
            elem = self.model.elements[i]
            if not elem:
                continue
            
            # Эмодзи для разных типов
            emoji = {
                1: "🎯", 2: "⚡", 3: "💰", 4: "🔍", 
                5: "🎭", 6: "🏛", 7: "⚓", 8: "🔗", 9: "🌍"
            }.get(i, "🔹")
            
            lines.append(f"{emoji} **{i}. {elem.name}**")
            lines.append(f"   {elem.description[:100]}")
            lines.append(f"   Сила: {elem.strength:.1%} | ВАК: {elem.vak}")
            
            # Связи
            if elem.causes:
                causes_str = ", ".join([f"→{c}" for c in elem.causes[:3]])
                lines.append(f"   Влияет на: {causes_str}")
            lines.append("")
        
        # Петли
        if self.loops:
            lines.append("🔄 *Рекурсивные петли:*\n")
            for i, loop in enumerate(self.loops[:3], 1):
                lines.append(f"{i}. {loop['description']}")
                lines.append(f"   Сила: {loop['impact']:.1%}")
                lines.append("")
        
        # Ключевой конфайнмент
        if self.key:
            lines.append("⛓ *КЛЮЧЕВОЕ ОГРАНИЧЕНИЕ*\n")
            lines.append(self.key['description'])
            lines.append("")
            
            # Интервенция
            lines.append("💡 *ЧТО ДЕЛАТЬ*")
            lines.append(f"Подход: {self.key['intervention']['approach']}")
            lines.append(f"Метод: {self.key['intervention']['method']}")
            lines.append(f"Упражнение: {self.key['intervention']['exercise']}")
        
        return "\n".join(lines)
    
    def get_simple_advice(self) -> str:
        """
        Возвращает простой совет на день на основе модели
        
        Returns:
            str: простой совет
        """
        if not self.key:
            return "Пройди тест, чтобы я мог понять твою ситуацию."
        
        elem = self.key['element']
        
        # Простые советы для каждого типа
        simple_advice = {
            1: f"Ты замечаешь, что {elem.description[:50].lower()}... Это только вершина айсберга. Давай копать глубже.",
            2: f"Твое поведение — ключ. Попробуй сегодня сделать наоборот.",
            3: f"Твоя стратегия работает против тебя. Что если попробовать другой подход?",
            4: f"Этот паттерн незаметен, но именно он запускает всё. Начни его замечать.",
            5: f"Твое убеждение «{elem.description[:30]}» ограничивает. Найди одно исключение.",
            6: f"Система вокруг тебя не меняется. Что ты можешь изменить в ней?",
            7: f"Глубинное убеждение — корень. Поработай с ним через письменные практики.",
            8: f"Эта связка соединяет противоречия. Что если разорвать эту связь?",
            9: f"Это замыкающий элемент. Измени его — и система рухнет."
        }
        
        advice = simple_advice.get(elem.id, "Ключевое ограничение требует осознания.")
        
        return f"💡 *Совет дня*\n\n{advice}"
    
    def get_intervention(self) -> Optional[Dict]:
        """
        Возвращает полную интервенцию для работы с ключевым конфайнментом
        
        Returns:
            dict: полная интервенция или None
        """
        if not self.key:
            return None
        
        return self.key['intervention']
    
    def get_markdown_report(self, detailed: bool = False) -> str:
        """
        Возвращает отчет, отформатированный для Telegram (Markdown)
        
        Args:
            detailed: если True - детальный отчет, иначе краткий
            
        Returns:
            str: отчет в Markdown
        """
        if detailed:
            return self.get_detailed_report()
        else:
            return self.get_summary()
    
    def get_text_for_share(self) -> str:
        """
        Возвращает текст для отправки другому человеку
        
        Returns:
            str: текст для общего доступа
        """
        lines = []
        lines.append(f"🧠 *КОНФАЙНМЕНТ-МОДЕЛЬ ПОЛЬЗОВАТЕЛЯ {self.user_name}*\n")
        
        if self.key:
            lines.append(f"🎯 *Ключевое ограничение:*")
            lines.append(self.key['description'])
            lines.append("")
        
        if self.loops:
            strongest = self.loop_analyzer.get_strongest_loop()
            if strongest:
                lines.append(f"🔄 *Главная петля:*")
                lines.append(strongest['description'])
        
        return "\n".join(lines)
    
    def get_json_report(self) -> Dict:
        """
        Возвращает отчет в виде JSON для сохранения
        
        Returns:
            dict: данные отчета
        """
        return {
            'user_name': self.user_name,
            'key_confinement': self.key,
            'loops': self.loops,
            'is_closed': self.model.is_closed,
            'closure_score': self.model.closure_score,
            'generated_at': datetime.now().isoformat()
        }


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С РЕПОРТЕРОМ
# ============================================

def create_reporter_from_user_data(user_data: Dict, user_name: str = "друг") -> Optional[ConfinementReporter]:
    """
    Создает репортер из данных пользователя
    
    Args:
        user_data: словарь с данными пользователя
        user_name: имя пользователя
        
    Returns:
        ConfinementReporter или None
    """
    model_data = user_data.get('confinement_model')
    if not model_data:
        return None
    
    try:
        from confinement_model import ConfinementModel9
        model = ConfinementModel9.from_dict(model_data)
        return ConfinementReporter(model, user_name)
    except Exception as e:
        logger.error(f"Ошибка при создании репортера: {e}")
        return None


def format_intervention_for_display(intervention: Dict) -> str:
    """
    Форматирует интервенцию для красивого отображения
    
    Args:
        intervention: словарь с интервенцией
        
    Returns:
        str: отформатированный текст
    """
    if not intervention:
        return "Интервенция не найдена"
    
    text = f"""
💡 *ИНТЕРВЕНЦИЯ ДЛЯ РАБОТЫ С КОНФАЙНМЕНТОМ*

🎯 *Цель:* {intervention.get('target', 'Не указана')}

📌 *Описание:*
{intervention.get('description', 'Нет описания')}

⚡ *Что делать:*
{intervention.get('exercise', 'Нет упражнения')}

📊 *Продолжительность:* {intervention.get('duration', 'Не указана')}
"""
    
    if 'expected' in intervention:
        text += f"\n✨ *Ожидаемый результат:*\n{intervention['expected']}"
    
    return text


# ============================================
# ПРИМЕР ИСПОЛЬЗОВАНИЯ (для тестирования)
# ============================================

if __name__ == "__main__":
    # Этот код выполнится только при прямом запуске файла
    print("🧪 Тестирование ConfinementReporter...")
    
    # Создаем тестовую модель (упрощенно)
    from confinement_model import ConfinementModel9, ConfinementElement
    
    test_model = ConfinementModel9(user_id=12345)
    
    # Заполняем тестовыми данными
    test_model.elements[1] = ConfinementElement(1, "🎯 Симптом")
    test_model.elements[1].description = "Постоянная тревога и беспокойство"
    test_model.elements[1].strength = 1.0
    
    test_model.elements[2] = ConfinementElement(2, "🛡 Избегание")
    test_model.elements[2].description = "Избегаю ситуаций, которые вызывают тревогу"
    test_model.elements[2].strength = 0.8
    
    # Добавляем связи
    test_model.elements[1].causes = [2]
    test_model.elements[2].caused_by = [1]
    
    # Создаем репортер
    reporter = ConfinementReporter(test_model, "Тестовый")
    
    # Выводим отчеты
    print("\n📋 КРАТКИЙ ОТЧЕТ:")
    print(reporter.get_summary())
    
    print("\n💡 СОВЕТ:")
    print(reporter.get_simple_advice())
    
    print("\n✅ Тест завершен")
