"""RA2 Agent — AI agent for Red Alert 2: Yuri's Revenge.

Reads game state from a running RA2:YR process via memory inspection
and sends commands via ctypes Win32 API calls.

Subpackages:
    memory      — Memory offsets, process reading, type registry, game state
    controller  — Keyboard/mouse input, sidebar interaction
    display     — Terminal formatting for game state
    cli         — Command-line interface (monitor, probe, stats)
"""

from .memory import GameReader, GameState, HouseInfo, TypeCount
from .controller import GameController, SidebarLayout

__all__ = [
    "GameReader",
    "GameState",
    "HouseInfo",
    "TypeCount",
    "GameController",
    "SidebarLayout",
]
