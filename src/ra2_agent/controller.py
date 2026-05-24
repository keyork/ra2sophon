"""Controller - sends commands to RA2 via ctypes SendInput / PostMessage.

Uses ctypes to send keyboard and mouse input directly to the game window.
- Keyboard: SendInput with virtual keys (proven to work with RA2).
- Mouse: PostMessage WM_LBUTTONDOWN/UP to window handle (no cursor movement,
  avoids triggering map scrolling when clicking sidebar).

Window title is "Yuris Revenge " (trailing space).
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

# ── Win32 constants ────────────────────────────────────────────────────────────
user32 = ctypes.windll.user32

INPUT_KEYBOARD = 1
INPUT_MOUSE = 0
KEYEVENTF_KEYUP = 0x0002
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000

WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
MK_LBUTTON = 0x0001

# Virtual key codes
VK_ESCAPE = 0x1B
VK_Q = 0x51
VK_W = 0x57
VK_I = 0x49
VK_R = 0x52
VK_H = 0x48
VK_S = 0x53
VK_X = 0x58
VK_G = 0x47
VK_F = 0x46
VK_P = 0x50
VK_T = 0x54
VK_D = 0x44
VK_K = 0x4B
VK_L = 0x4C
VK_Z = 0x5A
VK_N = 0x4E
VK_M = 0x4D
VK_1 = 0x31
VK_2 = 0x32
VK_3 = 0x33
VK_4 = 0x34
VK_5 = 0x35

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

# lParam helper: (scan_code << 16) | repeat_count
def _key_lparam(vk: int, key_up: bool = False) -> int:
    scan = user32.MapVirtualKeyW(vk, 0)
    flags = (scan << 16) | 1
    if key_up:
        flags |= (1 << 30) | (1 << 31)  # previous key down + transition
    return flags


# ── ctypes structs ─────────────────────────────────────────────────────────────

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wt.WORD),
        ("wScan", wt.WORD),
        ("dwFlags", wt.DWORD),
        ("time", wt.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", wt.DWORD),
        ("dwFlags", wt.DWORD),
        ("time", wt.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", wt.DWORD), ("union", _INPUT_UNION)]


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
        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.union.ki.wVk = vk
        inp.union.ki.dwFlags = 0
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
        time.sleep(0.05)
        inp.union.ki.dwFlags = KEYEVENTF_KEYUP
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
        time.sleep(0.05)

    def press_key(self, vk: int) -> None:
        """Press a virtual key."""
        self._send_key(vk)

    def press_escape(self) -> None:
        self._send_key(VK_ESCAPE)

    # ── Mouse (PostMessage to window handle) ───────────────────────────────────

    def _post_click(self, x: int, y: int, button: str = "left") -> None:
        """Click at (x, y) via PostMessage — no physical cursor movement."""
        hwnd = self.hwnd
        if not hwnd:
            return
        # Convert screen coords to client coords
        point = ctypes.wintypes.POINT(x, y)
        user32.ScreenToClient(hwnd, ctypes.byref(point))
        cx, cy = point.x, point.y
        lparam = (cy << 16) | (cx & 0xFFFF)

        if button == "left":
            user32.PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lparam)
            time.sleep(0.05)
            user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, lparam)
        else:
            user32.PostMessageW(hwnd, WM_RBUTTONDOWN, 0, lparam)
            time.sleep(0.05)
            user32.PostMessageW(hwnd, WM_RBUTTONUP, 0, lparam)
        time.sleep(0.05)

    def _sendinput_click(self, x: int, y: int, button: str = "left") -> None:
        """Click via SendInput — moves physical cursor."""
        user32.SetCursorPos(x, y)
        time.sleep(0.02)
        down = MOUSEEVENTF_LEFTDOWN if button == "left" else MOUSEEVENTF_RIGHTDOWN
        up = MOUSEEVENTF_LEFTUP if button == "left" else MOUSEEVENTF_RIGHTUP
        inp = INPUT()
        inp.type = INPUT_MOUSE
        inp.union.mi.dwFlags = down
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
        time.sleep(0.05)
        inp.union.mi.dwFlags = up
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
        time.sleep(0.05)

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
