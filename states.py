"""
Состояния FSM
"""
from aiogram.fsm.state import State, StatesGroup


class TestStates(StatesGroup):
    # Существующие состояния
    stage_1 = State()
    stage_2 = State()
    stage_3 = State()
    stage_4 = State()
    stage_5 = State()
    results = State()
    awaiting_question = State()
    pretest_question = State()
    awaiting_context = State()
    mode_selection = State()
    
    # Состояния коррекции
    profile_confirmation = State()
    clarifying_selection = State()
    clarifying_test = State()
    alternative_test = State()
    
    # Состояния для работы с моделью
    viewing_confinement = State()
    viewing_intervention = State()
    
    # НОВЫЕ состояния
    profile_generated = State()
    destination_selection = State()
    route_generation = State()
    route_active = State()
    route_step_active = State()
    
    # НОВЫЕ СОСТОЯНИЯ ДЛЯ ПРОВЕРКИ РЕАЛЬНОСТИ
    collecting_life_context = State()      # сбор базового контекста жизни
    collecting_goal_context = State()      # сбор контекста под конкретную цель
    theoretical_path_shown = State()       # показан теоретический путь
    reality_check_active = State()          # активна проверка реальности
    feasibility_result = State()            # результат проверки
