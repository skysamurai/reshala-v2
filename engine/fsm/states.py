"""Backward-compatible re-export from domain.fsm.states."""
from domain.fsm.states import FSMState, ActiveSubState, WaitReason, TransitionTable

__all__ = ["FSMState", "ActiveSubState", "WaitReason", "TransitionTable"]
