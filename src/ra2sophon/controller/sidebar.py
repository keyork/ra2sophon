"""Game controller for RA2:YR — sidebar, selection, building placement."""

from __future__ import annotations

import ctypes
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .input import (
    user32,
    send_key_press,
    post_click,
    sendinput_click,
    VK_ESCAPE,
    VK_Q,
    VK_W,
    VK_I,
    VK_R,
    VK_H,
    VK_S,
    VK_X,
    VK_G,
    VK_F,
    VK_P,
    VK_T,
    VK_D,
    VK_K,
    VK_L,
    VK_Z,
    VK_N,
    VK_M,
)


# ── Sidebar layout configuration ────────────────────────────────────────────

@dataclass
class SidebarLayout:
    """Sidebar pixel positions for a specific game resolution."""
    sidebar_width: int
    build_item_start_y: int
    build_item_height: int
    build_item_x: int

DEFAULT_SIDEBAR_LAYOUT = SidebarLayout(
    sidebar_width=168,
    build_item_start_y=680,
    build_item_height=50,
    build_item_x=2440,
)


# ── Enums ──────────────────────────────────────────────────────────────────────

class SidebarTab(Enum):
    BUILDING = "building"
    DEFENSE = "defense"
    INFANTRY = "infantry"
    UNIT = "unit"


# ── Main controller ────────────────────────────────────────────────────────────

class GameController:
    """Controls RA2:YR via ctypes SendInput (keyboard) + PostMessage (mouse)."""

    # Game window title (exact, with trailing space)
    WINDOW_TITLE = "Yuris Revenge "

    def __init__(
        self,
        resolution: tuple[int, int] = (2560, 1440),
        sidebar_layout: SidebarLayout = DEFAULT_SIDEBAR_LAYOUT,
    ) -> None:
        self.width, self.height = resolution
        self.sidebar_layout = sidebar_layout
        self.sidebar_left = self.width - self.sidebar_layout.sidebar_width
        self.game_width = self.sidebar_left
        self._hwnd: Optional[int] = None

    # ── Window management ──────────────────────────────────────────────────────

    @property
    def hwnd(self) -> int:
        """Get game window handle, caching after first lookup."""
        if self._hwnd is None:
            self._hwnd = user32.FindWindowW(None, self.WINDOW_TITLE)
        return self._hwnd or 0

    def bring_to_front(self) -> bool:
        """Bring the game window to foreground."""
        hwnd = self.hwnd
        if not hwnd:
            return False
        # Show window if minimized
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        time.sleep(0.1)
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.3)
        return user32.GetForegroundWindow() == hwnd

    # ── Keyboard (SendInput with virtual keys) ─────────────────────────────────

    def _send_key(self, vk: int) -> None:
        """Press and release a key via SendInput."""
        send_key_press(vk)

    def press_key(self, vk: int) -> None:
        """Press a virtual key."""
        self._send_key(vk)

    def press_escape(self) -> None:
        self._send_key(VK_ESCAPE)

    # ── Mouse (PostMessage to window handle) ───────────────────────────────────

    def _post_click(self, x: int, y: int, button: str = "left") -> None:
        """Click at (x, y) via PostMessage — no physical cursor movement."""
        post_click(self.hwnd, x, y, button)

    def _sendinput_click(self, x: int, y: int, button: str = "left") -> None:
        """Click via SendInput — moves physical cursor."""
        sendinput_click(x, y, button)

    # ── Sidebar interaction ────────────────────────────────────────────────────

    def switch_tab(self, tab: SidebarTab) -> None:
        """Switch to a sidebar tab."""
        vk_map = {
            SidebarTab.BUILDING: VK_Q,
            SidebarTab.DEFENSE: VK_W,
            SidebarTab.INFANTRY: VK_I,
            SidebarTab.UNIT: VK_R,
        }
        self._send_key(vk_map[tab])
        time.sleep(0.2)

    def click_sidebar_slot(self, slot: int) -> None:
        """Click a sidebar build item by slot index (0-based).

        Build items are in the lower sidebar area, starting at y=680.
        Uses PostMessage so cursor doesn't move.
        """
        if slot < 0:
            return
        x = self.sidebar_layout.build_item_x
        y = self.sidebar_layout.build_item_start_y + slot * self.sidebar_layout.build_item_height + self.sidebar_layout.build_item_height // 2
        self._post_click(x, y)

    def click_sidebar_slot_sendinput(self, slot: int) -> None:
        """Click sidebar slot via SendInput (moves cursor). Use only if PostMessage doesn't work."""
        if slot < 0:
            return
        x = self.sidebar_layout.build_item_x
        y = self.sidebar_layout.build_item_start_y + slot * self.sidebar_layout.build_item_height + self.sidebar_layout.build_item_height // 2
        self._sendinput_click(x, y)

    def scroll_sidebar_up(self) -> None:
        self._send_key(0x68)  # Numpad 8

    def scroll_sidebar_down(self) -> None:
        self._send_key(0x62)  # Numpad 2

    # ── Game area interaction ──────────────────────────────────────────────────

    def click_game(self, game_x: int, game_y: int, button: str = "left") -> None:
        """Click at a position in the game area (sidebar excluded) via PostMessage."""
        self._post_click(game_x, game_y, button)

    def click_game_sendinput(self, game_x: int, game_y: int, button: str = "left") -> None:
        """Click game area via SendInput (moves cursor)."""
        self._sendinput_click(game_x, game_y, button)

    # ── Selection ──────────────────────────────────────────────────────────────

    def center_base(self) -> None:
        """Press H to center view on base."""
        self._send_key(VK_H)
        time.sleep(0.2)

    def select_all_combatants(self) -> None:
        self._send_key(VK_P)

    def select_type(self) -> None:
        self._send_key(VK_T)

    def stop_selected(self) -> None:
        self._send_key(VK_S)

    def scatter_selected(self) -> None:
        self._send_key(VK_X)

    def guard_selected(self) -> None:
        self._send_key(VK_G)

    # ── Building placement ─────────────────────────────────────────────────────

    def place_building(self, game_x: int, game_y: int) -> None:
        """Click to place a building in the game area via PostMessage."""
        self._post_click(game_x, game_y)

    def place_building_sendinput(self, game_x: int, game_y: int) -> None:
        """Place building via SendInput (moves cursor)."""
        self._sendinput_click(game_x, game_y)

    def cancel_placement(self) -> None:
        """Right-click to cancel building placement."""
        self._post_click(100, 100, button="right")
        time.sleep(0.05)
