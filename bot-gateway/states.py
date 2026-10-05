from aiogram.fsm.state import StatesGroup, State


class ReceiveStates(StatesGroup):
    choosing_consumable = State()
    entering_new_name = State()
    entering_quantity = State()
    entering_supplier = State()


class UseStates(StatesGroup):
    choosing_consumable = State()
    entering_quantity = State()


class WorkLogStates(StatesGroup):
    choosing_service = State()
    entering_new_service_name = State()
    entering_new_service_price = State()
    choosing_consumables = State()
    entering_consumable_quantity = State()
    entering_client_name = State()
    entering_cost = State()
