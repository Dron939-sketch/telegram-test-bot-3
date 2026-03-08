# confinement_reporter.py
from typing import Dict, List, Optional, Any
from datetime import datetime
from confinement_model import ConfinementModel9
from loop_analyzer import LoopAnalyzer
from key_confinement import KeyConfinementDetector


class ConfinementReporter:
    """
    Формирует отчеты и ответы на основе конфайнмент-модели
    """
    
    # Эмодзи для разных типов элементов
    ELEMENT_EMOJI = {
        1: "🎯", 2: "⚡", 3: "💰", 4: "🔍", 
        5: "🎭", 6: "🏛", 7: "⚓", 8: "🔗", 9: "🌍"
    }
    
    # Названия типов для людей
    TYPE_NAMES = {
        'result': 'Симптом',
        'immediate_cause': 'Непосредственная причина',
        'common_cause': 'Общая причина',
        'upper_cause': 'Причина верхнего уровня',
        'closing': 'Замыкающий элемент'
    }
    
    def __init__(self, model: ConfinementModel9, user_name: str = "друг"):
        self.model = model
        self.user_name = user_name
        self.loop_analyzer = LoopAnalyzer(model)
        self.loops = self.loop_analyzer.analyze()
        self.key_detector = KeyConfinementDetector(model, self.loops)
        self.key = self.key_detector.detect()
    
    def get_summary(self) -> str:
        """
        Возвращает краткое резюме модели
        """
        if not self.model.elements.get(1):
            return "🧠 *Модель еще не построена*\n\nПройди тест, чтобы увидеть свою конфайнмент-модель."
        
        lines = []
        
        # Заголовок с именем
        lines.append(f"🧠 *КОНФАЙНМЕНТ-МОДЕЛЬ* для {self.user_name}\n")
        
        # Результат (главный симптом)
        result = self.model.elements[1]
        if result:
            lines.append(f"🎯 *Главный симптом:*")
            # Ограничиваем длину для краткого отчета
            short_desc = result.description.replace('*', '').replace('**', '')
            if len(short_desc) > 100:
                short_desc = short_desc[:100] + "..."
            lines.append(f"   {short_desc}\n")
        
        # Ключевой конфайнмент
        if self.key:
            lines.append(f"⛓ *Ключевое ограничение:*")
            lines.append(f"   {self.key['description']}")
            lines.append("")
        
        # Петли
        if self.loops:
            strongest = self.loop_analyzer.get_strongest_loop()
            if strongest:
                lines.append(f"🔄 *Главная петля:*")
                lines.append(f"   {strongest['description']}")
                impact_pct = strongest.get('impact', 0) * 100
                lines.append(f"   Сила: {impact_pct:.0f}%")
                lines.append("")
        
        # Замыкание
        closure_status = "✅ замкнута" if self.model.is_closed else "🔄 разомкнута"
        closure_pct = self.model.closure_score * 100
        lines.append(f"📊 *Система:* {closure_status} (степень замыкания {closure_pct:.0f}%)")
        
        # Точка вмешательства (если есть)
        break_points = self.loop_analyzer.get_break_points_summary()
        if break_points and "не обнаружены" not in break_points:
            lines.append("")
            lines.append(f"💡 *Точка вмешательства:*")
            lines.append(f"   {break_points}")
        
        return "\n".join(lines)
    
    def get_detailed_report(self) -> str:
        """
        Возвращает детальный отчет по модели
        """
        if not self.model.elements.get(1):
            return "Модель еще не построена"
        
        lines = []
        
        # Заголовок
        lines.append(f"🧠 *ПОЛНАЯ КОНФАЙНМЕНТ-МОДЕЛЬ*\n")
        lines.append(f"для {self.user_name}\n")
        lines.append("─" * 40 + "\n")
        
        # Все элементы
        lines.append("**🔹 9 ЭЛЕМЕНТОВ СИСТЕМЫ:**\n")
        
        for i in range(1, 10):
            elem = self.model.elements.get(i)
            if not elem:
                continue
            
            emoji = self.ELEMENT_EMOJI.get(i, "🔹")
            
            # Заголовок элемента
            type_name = self.TYPE_NAMES.get(elem.element_type, 'Элемент')
            lines.append(f"{emoji} *{i}. {elem.name}*")
            lines.append(f"   *Тип:* {type_name}")
            
            # Описание (очищаем от маркдауна для читаемости)
            desc = elem.description.replace('*', '').replace('**', '')
            if len(desc) > 150:
                desc = desc[:150] + "..."
            lines.append(f"   *Описание:* {desc}")
            
            # Характеристики
            strength_pct = elem.strength * 100
            vak_names = {
                'visual': '👁️ Визуал',
                'auditory': '👂 Аудиал',
                'kinesthetic': '🤲 Кинестетик',
                'auditory_digital': '🧠 Дискрет',
                'digital': '💭 Мыслитель'
            }
            vak_name = vak_names.get(elem.vak, elem.vak)
            
            lines.append(f"   *Сила:* {strength_pct:.0f}% | *ВАК:* {vak_name}")
            
            # Связи
            if elem.causes:
                causes_str = ", ".join([f"→{c}" for c in elem.causes[:5]])
                lines.append(f"   *Влияет на:* {causes_str}")
            if elem.caused_by:
                caused_by_str = ", ".join([f"←{c}" for c in elem.caused_by[:5]])
                lines.append(f"   *Зависит от:* {caused_by_str}")
            
            # Если это ключевой конфайнмент - помечаем
            if self.key and self.key['element_id'] == i:
                lines.append(f"   ⭐ *КЛЮЧЕВОЕ ОГРАНИЧЕНИЕ*")
            
            lines.append("")
        
        lines.append("─" * 40 + "\n")
        
        # Петли
        if self.loops:
            lines.append("**🔄 РЕКУРСИВНЫЕ ПЕТЛИ:**\n")
            
            # Сортируем по силе
            sorted_loops = sorted(self.loops, key=lambda x: x.get('impact', 0), reverse=True)
            
            for i, loop in enumerate(sorted_loops[:5], 1):
                impact_pct = loop.get('impact', 0) * 100
                
                # Цветовой индикатор
                color_indicator = {
                    'red': '🔴',
                    'orange': '🟠',
                    'yellow': '🟡',
                    'blue': '🔵',
                    'gray': '⚪'
                }.get(loop.get('color'), '🔄')
                
                lines.append(f"{color_indicator} *Петля {i}:* {loop['description']}")
                lines.append(f"   *Сила:* {impact_pct:.0f}%")
                
                # Показываем элементы в петле
                elem_names = []
                for eid in loop.get('cycle', []):
                    elem = self.model.elements.get(eid)
                    if elem:
                        # Берем короткое имя
                        name = elem.name.split()[1] if ' ' in elem.name else elem.name
                        elem_names.append(f"{eid}({name})")
                
                if elem_names:
                    lines.append(f"   *Цепочка:* {' → '.join(elem_names)}")
                lines.append("")
        
        lines.append("─" * 40 + "\n")
        
        # Ключевой конфайнмент
        if self.key:
            lines.append("**⛓ КЛЮЧЕВОЕ ОГРАНИЧЕНИЕ**\n")
            lines.append(self.key['description'])
            lines.append("")
            
            # Интервенция
            intervention = self.key.get('intervention', {})
            if intervention:
                lines.append("**💡 РЕКОМЕНДУЕМАЯ ИНТЕРВЕНЦИЯ**\n")
                lines.append(f"*Подход:* {intervention.get('approach', 'Не определен')}")
                lines.append(f"*Метод:* {intervention.get('method', 'Не определен')}")
                lines.append(f"*Длительность:* {intervention.get('duration', '7-30 дней')}")
                lines.append(f"*Сложность:* {intervention.get('difficulty', 'Средняя')}")
                lines.append("")
                lines.append(f"*Упражнение:*")
                lines.append(f"_{intervention.get('exercise', 'Нет упражнения')}_")
        
        # Подвал с датой
        lines.append("")
        lines.append("─" * 40)
        created = self.model.created_at.strftime("%d.%m.%Y %H:%M")
        updated = self.model.updated_at.strftime("%d.%m.%Y %H:%M")
        lines.append(f"📅 Создано: {created}")
        lines.append(f"🔄 Обновлено: {updated}")
        
        return "\n".join(lines)
    
    def get_simple_advice(self) -> str:
        """
        Возвращает простой совет на основе модели
        """
        if not self.key:
            return "💡 *Совет*\n\nПройди тест, чтобы я мог понять твою ситуацию и дать персональный совет."
        
        elem = self.key['element']
        
        # Простые советы для каждого типа
        simple_advice = {
            1: f"Ты замечаешь, что {elem.description[:50].lower()}... Это только вершина айсберга. Попробуй сегодня просто понаблюдать за этим симптомом без оценки.",
            2: f"Твое поведение — ключ к изменениям. Попробуй сегодня в похожей ситуации сделать наоборот и запиши, что произошло.",
            3: f"Твоя стратегия работает против тебя. Что если сегодня попробовать другой подход? Любое маленькое изменение уже сдвинет систему.",
            4: f"Этот паттерн незаметен, но именно он запускает всё. Начни его замечать: поставь напоминание на телефоне 3 раза в день.",
            5: f"Твое убеждение «{elem.description[:30]}» ограничивает. Найди сегодня одно исключение из этого правила.",
            6: f"Система вокруг тебя не меняется сама. Что ты можешь изменить в своем окружении уже сегодня?",
            7: f"Глубинное убеждение — корень проблемы. Попробуй записать, откуда оно взялось и когда помогло тебе выжить.",
            8: f"Эта связка соединяет противоречия. Что если временно разорвать эту связь и посмотреть, что произойдет?",
            9: f"Твоя картина мира замыкает систему. Попробуй сегодня найти 3 доказательства того, что мир может быть другим."
        }
        
        advice = simple_advice.get(elem.id, "Ключевое ограничение требует осознания. Начни с малого: просто замечай его.")
        
        # Добавляем имя пользователя
        name_part = f", {self.user_name}" if self.user_name != "друг" else ""
        
        return f"💡 *Совет для тебя{name_part}*\n\n{advice}"
    
    def get_intervention(self) -> Optional[Dict[str, Any]]:
        """
        Возвращает полную интервенцию
        """
        if not self.key:
            return None
        
        return self.key.get('intervention')
    
    def get_confinement_map(self) -> str:
        """
        Возвращает ASCII-схему конфайнмент-модели
        """
        if not all(self.model.elements.get(i) for i in [1, 2, 3, 4, 5, 6, 7, 8, 9]):
            return "Схема недоступна"
        
        lines = []
        lines.append("```")
        lines.append("        КОНФАЙНМЕНТ-МОДЕЛЬ")
        lines.append("")
        lines.append("         [9] 🔒 ЗАМЫКАНИЕ")
        lines.append("          /       \\")
        lines.append("        [7]       [8]")
        lines.append("         |         |")
        lines.append("        [6]──────[5]")
        lines.append("         |         |")
        lines.append("    [2]──[3]──────[4]")
        lines.append("     \\    |        /")
        lines.append("      \\   |       /")
        lines.append("       \\  |      /")
        lines.append("        [1] 🔴 СИМПТОМ")
        lines.append("")
        
        # Легенда
        lines.append("ЭЛЕМЕНТЫ:")
        for i in range(1, 10):
            elem = self.model.elements[i]
            if elem:
                short_name = elem.name[:15]
                marker = "⭐" if self.key and self.key['element_id'] == i else "  "
                lines.append(f"  {i}. {marker} {short_name}")
        
        lines.append("```")
        return "\n".join(lines)
    
    def get_voice_message_text(self) -> str:
        """
        Возвращает текст для голосового сообщения (более разговорный)
        """
        if not self.key:
            return "Привет! Я пока не построил твою модель. Пройди тест, и я расскажу, как устроена твоя психологическая система."
        
        elem = self.key['element']
        
        texts = {
            1: f"{self.user_name}, я вижу, что главный симптом — это {elem.description[:30]}... Он возвращается снова и снова, потому что вся система его воспроизводит. Но это только верхушка айсберга.",
            2: f"Знаешь, {self.user_name}, ключ к изменениям — в твоем поведении. Именно оно запускает цепную реакцию. Попробуй сегодня сделать что-то по-другому, и система начнет меняться.",
            3: f"{self.user_name}, твоя стратегия сейчас работает против тебя. Она кажется единственно возможной, но это ловушка. Давай поищем альтернативы?",
            4: f"Есть один паттерн, {self.user_name}, который ты можешь даже не замечать. Но именно через него все замыкается. Начни его отслеживать — это первый шаг.",
            5: f"{self.user_name}, центральное убеждение «{elem.description[:20]}» пронизывает все уровни твоей жизни. Это линза, через которую ты смотришь на мир.",
            6: f"Система вокруг тебя, {self.user_name}, создает правила игры. Семья, работа, культура — они держат проблему. Что можно изменить в контексте?",
            7: f"{self.user_name}, глубинное убеждение — это корень. Оттуда все растет. Поработаем с ним через письменные практики?",
            8: f"Есть связка, {self.user_name}, которая соединяет несовместимое. Она удерживает противоречия. Если ее разорвать, система потеряет устойчивость.",
            9: f"{self.user_name}, твоя картина мира замыкает систему. Именно она не дает ей измениться. Давай попробуем увидеть мир иначе?"
        }
        
        return texts.get(elem.id, f"{self.user_name}, я нашел ключевое ограничение в твоей системе. Оно требует внимания и осознания.")
