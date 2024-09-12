from aiogram.fsm.state import State, StatesGroup

class BuyProcess(StatesGroup):
    Start = State()
    Buying = State()
    WaitingAnswer = State()
    WaitingPaymentConfirmation = State()
