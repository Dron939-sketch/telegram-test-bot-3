"""
Общие переменные и экземпляры бота
"""
from aiogram import Bot
from models import UserContext, ReminderManager, DestinationManager, Statistics
from hypno_module import HypnoOrchestrator, TherapeuticTales, Anchoring

# Глобальные хранилища
user_data = {}
user_names = {}
user_contexts = {}
user_routes = {}

# Инициализируем менеджеры
reminder_manager = ReminderManager()
destination_manager = DestinationManager()
stats = Statistics()

# Инициализируем гипнотический оркестратор
hypno = HypnoOrchestrator()
tales = TherapeuticTales()
anchoring = Anchoring()

# Экземпляр бота (будет установлен позже)
bot_instance = None


def set_bot(bot: Bot):
    """Устанавливает экземпляр бота"""
    global bot_instance
    bot_instance = bot
    reminder_manager.set_bot(bot)
