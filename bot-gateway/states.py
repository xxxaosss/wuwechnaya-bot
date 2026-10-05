from aiogram.fsm.state import StatesGroup, State


class ReceiveStates(StatesGroup):
    choosing_consumable = State()
    entering_new_name = State()
    entering_quantity = State()
    entering_supplier = State()


class UseStates(StatesGroup):
    choosing_consumable = State()
    entering_quantity = State()
