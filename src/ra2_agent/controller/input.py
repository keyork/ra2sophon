"""Low-level Win32 input primitives for RA2:YR controller.

Provides ctypes structs and Win32 constants for keyboard (SendInput)
and mouse (PostMessage/SendInput) input.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import time

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


# ── Helpers ────────────────────────────────────────────────────────────────────

def _key_lparam(vk: int, key_up: bool = False) -> int:
    """Build lParam for WM_KEYDOWN/UP: (scan_code << 16) | repeat_count."""
    scan = user32.MapVirtualKeyW(vk, 0)
    flags = (scan << 16) | 1
    if key_up:
        flags |= (1 << 30) | (1 << 31)  # previous key down + transition
    return flags


def send_key_press(vk: int) -> None:
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


def post_click(hwnd: int, x: int, y: int, button: str = "left") -> None:
    """Click at (x, y) via PostMessage — no physical cursor movement."""
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


def sendinput_click(x: int, y: int, button: str = "left") -> None:
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
