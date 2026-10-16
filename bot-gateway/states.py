from aiogram.fsm.state import StatesGroup, State


class ReceiveStates(StatesGroup):
    choosing_consumable = State()
    entering_new_name = State()
    choosing_new_kind = State()
    entering_pack_size = State()
    entering_pieces = State()


class UseStates(StatesGroup):
    choosing_consumable = State()
    choosing_mode = State()
    entering_amount = State()


class WorkLogStates(StatesGroup):
    choosing_service = State()
    entering_new_service_name = State()
    entering_new_service_price = State()
    choosing_consumables = State()
    choosing_consumable_mode = State()
    entering_consumable_quantity = State()
    entering_client_name = State()
    entering_cost = State()


class ImportStates(StatesGroup):
    waiting_file = State()
    confirming = State()
