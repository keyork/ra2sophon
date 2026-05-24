"""RA2 Agent — AI agent for Red Alert 2: Yuri's Revenge.

Reads game state from a running RA2:YR process via memory inspection
and sends commands via ctypes Win32 API calls.
"""

from .reader import GameReader, GameState, HouseInfo
from .controller import GameController

__all__ = [
    "GameReader",
    "GameState",
    "HouseInfo",
    "GameController",
]
