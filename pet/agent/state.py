"""轻量状态机"""

from enum import Enum

from PySide6.QtCore import QObject, Signal


class PetState(Enum):
    IDLE = "idle"
    AUTONOMOUS = "autonomous"
    INTERACTING = "interacting"


class StateMachine(QObject):
    """简单状态机，维护当前状态并做合法性检查"""

    state_changed = Signal(str)

    _TRANSITIONS = {
        PetState.IDLE:        [PetState.AUTONOMOUS, PetState.INTERACTING],
        PetState.AUTONOMOUS:  [PetState.IDLE, PetState.INTERACTING],
        PetState.INTERACTING: [PetState.IDLE, PetState.AUTONOMOUS],
    }

    def __init__(self, initial: PetState = PetState.IDLE, parent=None):
        super().__init__(parent)
        self._state = initial

    @property
    def state(self) -> PetState:
        return self._state

    @property
    def can_decide(self) -> bool:
        return self._state not in (PetState.AUTONOMOUS, PetState.INTERACTING)

    def transition(self, new_state: PetState) -> bool:
        allowed = self._TRANSITIONS.get(self._state, [])
        if new_state in allowed or new_state == self._state:
            if new_state != self._state:
                self._state = new_state
                self.state_changed.emit(new_state.value)
            return True
        return False

    def try_transition(self, new_state: PetState) -> bool:
        """原子化的 can_decide 检查 + 状态转移"""
        if not self.can_decide:
            return False
        return self.transition(new_state)

    def force(self, new_state: PetState):
        self._state = new_state
        self.state_changed.emit(new_state.value)
