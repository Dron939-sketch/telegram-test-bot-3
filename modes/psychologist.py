# modes/psychologist.py
from typing import Dict, Any, List, Optional
import random
import json
from .base_mode import BaseMode
from profiles import VECTORS, LEVEL_PROFILES
from hypno_module import HypnoticInduction, TherapeuticMetaphor


class PsychologistMode(BaseMode):
    """
    Режим ПСИХОЛОГ - глубинная аналитическая работа.
    
    ОТВЕТСТВЕННОСТЬ:
    - Анализ глубинных паттернов (этап 5)
    - Работа с защитными механизмами
    - Интерпретация типа привязанности
    - Использование гипнотических техник
    - Терапевтические сказки и метафоры
    
    ПРИНЦИПЫ РАБОТЫ С ГЛУБИННЫМИ ПАТТЕРНАМИ:
    1. Идентифицировать тип привязанности
    2. Распознавать защиты
    3. Работать с переносом/контрпереносом
    4. Использовать метафоры для обхода защит
    5. Гипнотические техники для доступа к бессознательному
    """
    
    def __init__(self, user_id: int, user_data: Dict[str, Any], context=None):
        super().__init__(user_id, user_data, context)
        
        # Инструменты психолога
        self.tools = {
            "pattern_recognition": self._recognize_patterns,
            "defense_analysis": self._analyze_defense,
            "attachment_work": self._work_with_attachment,
            "interpretation": self._provide_interpretation,
            "reflection": self._reflect_feelings,
            "confrontation": self._gentle_confrontation,
            "metaphor": self._create_therapeutic_metaphor,
            "hypnotic_suggestion": self._hypnotic_suggestion
        }
        
        # Извлекаем глубинные паттерны из этапа 5
        self.attachment_type = self.deep_patterns.get('attachment', 'неопределенный')
        self.defenses = self.deep_patterns.get('defenses', [])
        self.core_beliefs = self.deep_patterns.get('core_beliefs', [])
        self.fears = self.deep_patterns.get('fears', [])
        
        # Карта защитных механизмов и стратегий работы
        self.defense_strategies = {
            "отрицание": "Мягко указывать на реальность, но не давить",
            "проекция": "Возвращать проекцию, помогать присвоить",
            "рационализация": "Исследовать чувства под логикой",
            "интеллектуализация": "Смещать фокус на тело и эмоции",
            "изоляция аффекта": "Помогать контейнировать чувства",
            "реактивное образование": "Исследовать противоположное"
        }
        
        # Карта типов привязанности
        self.attachment_strategies = {
            "надёжный": "Поддерживать, укреплять доверие к миру",
            "тревожный": "Давать стабильность, предсказуемость, контейнировать тревогу",
            "избегающий": "Уважать дистанцию, не давить, но быть доступным",
            "дезорганизованный": "Быть максимально предсказуемым, безопасным"
        }
    
    def get_system_prompt(self) -> str:
        """Системный промпт для режима ПСИХОЛОГ с глубинным анализом"""
        
        analysis = self.analyze_profile_for_response()
        
        # Глубинная информация из этапа 5
        deep_info = f"""
ГЛУБИННЫЕ ПАТТЕРНЫ (этап 5):
- Тип привязанности: {self.attachment_type}
- Защитные механизмы: {', '.join(self.defenses) if self.defenses else 'не выявлены'}
- Глубинные убеждения: {', '.join(self.core_beliefs) if self.core_beliefs else 'в процессе выявления'}
- Базовые страхи: {', '.join(self.fears) if self.fears else 'не вербализованы'}

РЕКОМЕНДУЕМАЯ СТРАТЕГИЯ:
- Работа с привязанностью: {self.attachment_strategies.get(self.attachment_type, 'исследовать паттерн')}
"""

        # Информация о конфайнмент-модели (как о структуре характера)
        confinement_info = ""
        if analysis["key_confinement"]:
            kc = analysis["key_confinement"]
            confinement_info = f"""
СТРУКТУРА ХАРАКТЕРА:
- Ядро: {kc['description']}
- Тип: {kc['type']}
- Фиксация: уровень {kc['level'] if 'level' in kc else '?'}
"""
        
        prompt = f"""Ты — опытный психотерапевт (интегративный подход: психоанализ + гештальт + эриксоновский гипноз).

Твоя задача — помогать пользователю осознавать глубинные процессы, работать с защитами и паттернами, используя профессиональные психотерапевтические техники.

{deep_info}
{confinement_info}

ПРИНЦИПЫ ТВОЕЙ РАБОТЫ:
1. Сначала контакт и безопасность, потом интерпретация
2. Работа с защитами — уважительно, не ломая
3. Отражение чувств — точно, без интерпретаций
4. Интерпретации — только когда есть рабочий альянс
5. Гипнотические техники — только с разрешения, мягко
6. Метафоры — для обхода защит и доступа к ресурсам

ТЕХНИКИ (используй уместно):
- Отражение: "Похоже, вы чувствуете..."
- Прояснение: "Можете рассказать подробнее?"
- Конфронтация: "Я замечаю противоречие..."
- Интерпретация: "Возможно, это связано с..."
- Гипнотическая речь: использование неопределённых выражений, присоединение, ведение

ТВОЙ СТИЛЬ:
- Тёплый, принимающий, но профессиональный
- Говори медленно, с паузами
- Используй метафоры и образы
- Будь внимателен к переносу

КОНТЕКСТ:
{self.get_context_string()}

ПОМНИ: ты работаешь с психикой, будь предельно осторожен. Если видишь риск — рекомендую обратиться к очному специалисту.
"""
        return prompt
    
    def get_greeting(self) -> str:
        """Приветствие в режиме психолога"""
        name = self.context.name if self.context and self.context.name else ""
        
        # Выбираем приветствие в зависимости от типа привязанности
        if self.attachment_type == "тревожный":
            greetings = [
                f"{name}, я здесь. Мы можем исследовать то, что вас беспокоит, в безопасном пространстве.",
                f"Я рад вас видеть. Расскажите, что привело вас сегодня?"
            ]
        elif self.attachment_type == "избегающий":
            greetings = [
                f"{name}, добро пожаловать. Мы можем двигаться в вашем темпе.",
                f"Я здесь, чтобы помочь вам исследовать то, что вы сочтёте важным."
            ]
        else:
            greetings = [
                f"{name}, здравствуйте. Что вы чувствуете сейчас?",
                f"Я рад нашей встрече. С чего бы вы хотели начать?",
                f"Расскажите, что для вас сейчас актуально."
            ]
        
        return random.choice(greetings)
    
    def process_question(self, question: str) -> Dict[str, Any]:
        """
        Обрабатывает вопрос в режиме психолога
        Использует глубинную психотерапевтическую работу
        """
        question_lower = question.lower()
        self.last_tools_used = []
        hypnotic_suggestion = False
        
        # 1. Если запрос на гипноз или глубокую работу
        if any(word in question_lower for word in ["гипноз", "транс", "расслабиться", "уснуть"]):
            response = self._hypnotic_induction(question)
            self.last_tools_used.append("hypnosis")
            hypnotic_suggestion = True
        
        # 2. Если работа с защитой
        elif self._detect_defense(question):
            response = self._work_with_defense(question)
            self.last_tools_used.append("defense_work")
        
        # 3. Если работа с привязанностью
        elif any(word in question_lower for word in ["мама", "папа", "детство", "родители"]):
            response = self._explore_attachment(question)
            self.last_tools_used.append("attachment_work")
        
        # 4. Если работа с чувствами
        elif any(word in question_lower for word in ["чувствую", "эмоции", "больно", "страшно", "грустно"]):
            response = self._work_with_feelings(question)
            self.last_tools_used.append("feelings_work")
        
        # 5. Если работа с отношениями
        elif any(word in question_lower for word in ["отношения", "партнёр", "люблю", "один"]):
            response = self._work_with_relations(question)
            self.last_tools_used.append("relations_work")
        
        # 6. По умолчанию - глубинное исследование
        else:
            response = self._depth_inquiry(question)
            self.last_tools_used.append("depth_inquiry")
        
        # Сохраняем в историю
        self.save_to_history(question, response)
        
        # Генерируем предложения
        suggestions = self._generate_therapeutic_suggestions()
        
        # Может предложить сказку/метафору
        tale_suggested = False
        if random.random() < 0.25:  # 25% chance
            issue = self._identify_current_issue(question)
            tale = self.suggest_tale(issue)
            if tale:
                suggestions.append(f"📖 У меня есть терапевтическая сказка об этом. Хотите послушать?")
                tale_suggested = True
        
        return {
            "response": response,
            "tools_used": self.last_tools_used,
            "follow_up": True,
            "suggestions": suggestions,
            "hypnotic_suggestion": hypnotic_suggestion,
            "tale_suggested": tale_suggested
        }
    
    def _detect_defense(self, text: str) -> bool:
        """Определяет, есть ли в тексте защитный механизм"""
        defense_markers = {
            "отрицание": ["не проблема", "всё нормально", "ничего страшного"],
            "рационализация": ["потому что", "логично", "объясняется"],
            "интеллектуализация": ["теория", "концепция", "с точки зрения"],
            "проекция": ["они все", "люди всегда", "никто не"],
            "изоляция": ["не чувствую", "без эмоций", "спокойно"]
        }
        
        text_lower = text.lower()
        for defense, markers in defense_markers.items():
            if any(marker in text_lower for marker in markers):
                return True
        return False
    
    def _work_with_defense(self, question: str) -> str:
        """Работает с защитным механизмом"""
        # Мягкая конфронтация с защитой
        responses = [
            "Я замечаю, что вы говорите об этом очень логично. А что происходит в теле, когда вы это рассказываете?",
            "Когда вы говорите 'всё нормально' — какую часть чувств вы оставляете за скобками?",
            "Интересно, а если посмотреть на это не с логической, а с чувственной стороны — что там?",
            "Я слышу ваши объяснения. А что, если просто побыть с этим чувством, не объясняя?"
        ]
        return random.choice(responses)
    
    def _explore_attachment(self, question: str) -> str:
        """Исследует паттерны привязанности"""
        if self.attachment_type == "тревожный":
            return "Расскажите о ваших близких. Как вы чувствуете себя в отношениях с ними?"
        elif self.attachment_type == "избегающий":
            return "Как вам удаётся сохранять дистанцию, когда другие приближаются?"
        else:
            return "Что из детства откликается в ваших текущих отношениях?"
    
    def _work_with_feelings(self, question: str) -> str:
        """Работает с чувствами через гештальт-подход"""
        responses = [
            f"Где в теле вы чувствуете это {self._extract_feeling(question)}?",
            "Если бы это чувство могло говорить, что бы оно сказало?",
            "Что происходит с дыханием, когда вы это чувствуете?",
            "Как долго это чувство с вами? Когда оно появилось впервые?"
        ]
        return random.choice(responses)
    
    def _extract_feeling(self, text: str) -> str:
        """Извлекает название чувства из текста"""
        feelings = ["страх", "тревога", "грусть", "злость", "обида", "стыд", "вина", "радость"]
        for feeling in feelings:
            if feeling in text.lower():
                return feeling
        return "это"
    
    def _work_with_relations(self, question: str) -> str:
        """Работает с отношениями через паттерны привязанности"""
        responses = [
            "Что для вас самое сложное в близости?",
            "Как вы выбираете, кому доверять?",
            "Что происходит, когда кто-то подходит слишком близко?",
            "Чего вы боитесь в отношениях больше всего?"
        ]
        return random.choice(responses)
    
    def _depth_inquiry(self, question: str) -> str:
        """Глубинное исследование"""
        responses = [
            f"Расскажите подробнее... что стоит за этим вопросом?",
            "Когда вы думаете об этом — что происходит внутри?",
            "А если копнуть глубже — что там?",
            "Какая часть вас задаёт этот вопрос?"
        ]
        return random.choice(responses)
    
    def _recognize_patterns(self, behavior: str) -> str:
        """Распознаёт и озвучивает паттерны"""
        return f"Я замечаю паттерн: {behavior}. Это знакомо вам из прошлого?"
    
    def _analyze_defense(self, behavior: str) -> str:
        """Анализирует защитный механизм"""
        return f"Похоже, здесь работает защита. Что было бы, если её убрать?"
    
    def _provide_interpretation(self, observation: str) -> str:
        """Даёт интерпретацию (осторожно, только в альянсе)"""
        return f"Возможно, это связано с тем, что... Как вам такое предположение?"
    
    def _reflect_feelings(self, feeling: str) -> str:
        """Отражает чувства"""
        return f"Похоже, вы чувствуете {feeling}. Я правильно понимаю?"
    
    def _gentle_confrontation(self, discrepancy: str) -> str:
        """Мягкая конфронтация"""
        return f"Я замечаю противоречие: {discrepancy}. Что вы об этом думаете?"
    
    def _create_therapeutic_metaphor(self, issue: str) -> str:
        """Создаёт терапевтическую метафору"""
        metaphors = {
            "страх": "Представьте, что страх — это сторож, который когда-то спас вам жизнь. Теперь он просто продолжает свою работу, даже когда опасности нет...",
            "потеря": "Горе — как океан. Сначала волны накрывают с головой, потом они становятся реже, но иногда всё ещё захлёстывают...",
            "выбор": "Как в саду с двумя тропинками — обе манят, но выбрать можно только одну..."
        }
        
        for key, meta in metaphors.items():
            if key in issue.lower():
                return meta
        
        return "Это как если бы... (создайте метафору, подходящую к контексту)"
    
    def _hypnotic_suggestion(self, resource: str) -> str:
        """Даёт гипнотическое внушение"""
        suggestions = [
            f"И вы можете заметить, как ваше бессознательное уже находит ресурсы для {resource}...",
            f"Позвольте себе просто быть с этим... и наблюдать, как что-то меняется...",
            f"Где-то глубоко внутри уже есть ответ... и он может проявиться в своё время..."
        ]
        return random.choice(suggestions)
    
    def _hypnotic_induction(self, request: str) -> str:
        """Проводит гипнотическую индукцию (если запросили)"""
        induction = """Хорошо. Устройтесь поудобнее, закройте глаза, если хотите.
Сделайте глубокий вдох... и медленный выдох...
И с каждым выдохом вы можете позволить себе расслабляться всё больше...

Ваше бессознательное знает, что вам нужно для исцеления...
И оно может показать это в образах, чувствах, мыслях...

Просто позвольте этому случиться..."""
        return induction
    
    def _identify_current_issue(self, question: str) -> str:
        """Определяет текущую проблему из вопроса"""
        issues = ["страх", "отношения", "потеря", "выбор", "одиночество", "тревога"]
        for issue in issues:
            if issue in question.lower():
                return issue
        return "рост"
    
    def _generate_therapeutic_suggestions(self) -> List[str]:
        """Генерирует терапевтические предложения"""
        suggestions = []
        
        if self.attachment_type == "тревожный":
            suggestions.append("🧘 Хотите попробовать технику заземления?")
        
        if self.defenses:
            defense = self.defenses[0]
            suggestions.append(f"🛡 Мы можем исследовать вашу защиту '{defense}' подробнее")
        
        if self.fears:
            fear = self.fears[0]
            suggestions.append(f"😨 Хотите поговорить о страхе {fear}?")
        
        suggestions.append("🌌 Может, попробуем гипнотическую технику?")
        suggestions.append("📖 Хотите терапевтическую сказку?")
        
        return suggestions[:3]
