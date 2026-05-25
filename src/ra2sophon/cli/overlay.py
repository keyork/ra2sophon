"""Game overlay window — always-on-top, frameless, semi-transparent.

Shows real-time RA2:YR battlefield stats. Press F9 to toggle show/hide.
Appearance is configurable via data/overlay.toml.

Usage:
    python -m ra2sophon overlay
"""

from __future__ import annotations

import ctypes
import logging
import tomllib
import tkinter as tk
from pathlib import Path

from ..memory import GameReader
from ..memory.types import HouseInfo, GameState, TypeCount

logger = logging.getLogger(__name__)

# ── Win32 constants ───────────────────────────────────────────────────────────
GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010
HWND_TOPMOST = -1
HOTKEY_ID = 1
MSG_STRUCT_SIZE = 48
MOD_NOREPEAT = 0x4000
VK_F9 = 0x78
WM_HOTKEY = 0x0312

user32 = ctypes.windll.user32
SetWindowLongW = user32.SetWindowLongW
GetWindowLongW = user32.GetWindowLongW
SetWindowPos = user32.SetWindowPos
RegisterHotKey = user32.RegisterHotKey
UnregisterHotKey = user32.UnregisterHotKey
PeekMessageW = user32.PeekMessageW

# ── Load overlay config from TOML ────────────────────────────────────────────

def _load_config() -> dict:
    """Load overlay.toml, falling back to defaults for missing keys."""
    toml_path = Path(__file__).resolve().parent.parent / "data" / "overlay.toml"
    try:
        with open(toml_path, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        logger.warning("overlay.toml not found, using defaults")
        return {}


_CFG = _load_config()

_ov = _CFG.get("overlay", {})
OVERLAY_ALPHA = _ov.get("alpha", 0.90)
OVERLAY_POSITION = _ov.get("position", "+10+10")
REFRESH_MS = _ov.get("refresh_ms", 1000)
MAX_LINE_WIDTH = _ov.get("line_width", 50)

_frame = _ov.get("frame", {})
FRAME_PAD_X = _frame.get("pad_x", 8)
FRAME_PAD_Y = _frame.get("pad_y", 6)

_timing = _ov.get("timing", {})
INIT_DELAY_MS = _timing.get("init_delay_ms", 200)
HOTKEY_POLL_MS = _timing.get("hotkey_poll_ms", 100)

_fonts = _ov.get("fonts", {})
FONT_HEADER = tuple(_fonts.get("header", ["Consolas", 10, "bold"]))
FONT_BODY = tuple(_fonts.get("body", ["Consolas", 9]))
FONT_STATUS = tuple(_fonts.get("status", ["Consolas", 10]))

_clr = _CFG.get("colors", {})
BG_COLOR = _clr.get("background", "#1a1a2e")
FG_SEPARATOR = _clr.get("separator", "#333355")
FG_HEADER = _clr.get("header", "#ffd54f")
FG_POWER_OK = _clr.get("power_ok", "#66bb6a")
FG_POWER_LOW = _clr.get("power_low", "#ff7043")

_faction = _clr.get("faction", {})
FACTION_COLORS: dict[str, str] = {
    "allied": _faction.get("allied", "#4fc3f7"),
    "soviet": _faction.get("soviet", "#ef5350"),
    "yuri": _faction.get("yuri", "#ab47bc"),
}
FG_UNKNOWN = _faction.get("unknown", "#e0e0e0")

_cat = _clr.get("category", {})
CATEGORY_COLORS: dict[str, str] = {
    "Building": _cat.get("Building", "#90a4ae"),
    "Infantry": _cat.get("Infantry", "#a5d6a7"),
    "Vehicle":  _cat.get("Vehicle", "#80cbc4"),
    "Naval":    _cat.get("Naval", "#80deea"),
    "Aircraft": _cat.get("Aircraft", "#b39ddb"),
}


def _make_overlay_style(hwnd: int) -> None:
    """No-activate + tool window so overlay never steals focus from game."""
    ex = GetWindowLongW(hwnd, GWL_EXSTYLE)
    ex |= WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
    ex &= ~WS_EX_APPWINDOW
    SetWindowLongW(hwnd, GWL_EXSTYLE, ex)
    SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                 SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)


class OverlayApp:
    """Floating overlay that shows live RA2 stats.

    F9 toggles visibility. Window is always-on-top, frameless,
    semi-transparent, and does not steal focus from the game.
    Automatically waits for the game to start and reconnects if it closes.
    """

    def __init__(self) -> None:
        self._reader: GameReader | None = None
        self._visible = True

        # ── Root window ────────────────────────────────────────────────────
        self.root = tk.Tk()
        self.root.title("RA2 Overlay")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", OVERLAY_ALPHA)
        self.root.configure(bg=BG_COLOR, cursor="none")
        self.root.resizable(False, False)
        self.root.geometry(OVERLAY_POSITION)

        # ── Content frame ──────────────────────────────────────────────────
        self._frame = tk.Frame(self.root, bg=BG_COLOR,
                               padx=FRAME_PAD_X, pady=FRAME_PAD_Y)
        self._frame.pack()

        self._title_label = tk.Label(
            self._frame, text="RA2 Sophon  [F9 hide/show]",
            font=FONT_HEADER, fg=FG_HEADER, bg=BG_COLOR,
        )
        self._title_label.pack(anchor="w")

        self._body = tk.Frame(self._frame, bg=BG_COLOR)
        self._body.pack(fill="both")

        # ── Register F9 hotkey ─────────────────────────────────────────────
        self._hwnd = 0
        self.root.after(INIT_DELAY_MS, self._init_win32)

    def _init_win32(self) -> None:
        """Apply overlay style and register global hotkey."""
        self._hwnd = int(self.root.winfo_id())
        _make_overlay_style(self._hwnd)
        if not RegisterHotKey(self._hwnd, HOTKEY_ID, MOD_NOREPEAT, VK_F9):
            logger.warning("Failed to register F9 hotkey")
        self.root.bind("<ButtonPress>", self._return_focus)
        self._poll_hotkey()
        self._refresh()

    def _return_focus(self, event: tk.Event) -> None:
        """Immediately return focus to the game window."""
        fg = user32.GetForegroundWindow()
        if fg and fg != self._hwnd:
            user32.SetForegroundWindow(fg)
        SetWindowPos(self._hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                     SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)

    def _poll_hotkey(self) -> None:
        """Check for F9 hotkey press (non-blocking)."""
        msg = (ctypes.c_char * MSG_STRUCT_SIZE)()
        if PeekMessageW(msg, self._hwnd, WM_HOTKEY, WM_HOTKEY, 1):
            self._toggle_visibility()
        self.root.after(HOTKEY_POLL_MS, self._poll_hotkey)

    def _toggle_visibility(self) -> None:
        self._visible = not self._visible
        if self._visible:
            self.root.deiconify()
            SetWindowPos(self._hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                         SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
        else:
            self.root.withdraw()

    # ── Data display ───────────────────────────────────────────────────────
    def _faction_color(self, house: HouseInfo) -> str:
        return FACTION_COLORS.get(house.faction, FG_UNKNOWN)

    def _format_entries(self, entries: list[TypeCount]) -> list[str]:
        """Format ALL entries into wrapped lines (no truncation)."""
        if not entries:
            return ["(none)"]
        sorted_entries = sorted(entries, key=lambda e: e.count, reverse=True)
        parts = [f"{e.name_cn or e.name} x{e.count}" for e in sorted_entries]
        lines: list[str] = []
        current = ""
        for p in parts:
            if current and len(current) + 2 + len(p) > MAX_LINE_WIDTH:
                lines.append(current)
                current = p
            elif current:
                current += "  " + p
            else:
                current = p
        if current:
            lines.append(current)
        return lines

    def _update_display(self, state: GameState) -> None:
        """Rebuild overlay content from a fresh GameState."""
        for w in self._body.winfo_children():
            w.destroy()

        active = state.active_houses
        if not active:
            tk.Label(
                self._body, text="  (waiting for battle...)",
                font=FONT_BODY, fg=FG_HEADER, bg=BG_COLOR, anchor="w",
            ).pack(anchor="w")
            return

        for house in active:
            color = self._faction_color(house)
            you = " *" if house.is_current_player else ""
            name = house.house_type_name or f"P{house.array_index}"

            # Header
            pwr_s = house.power_surplus
            pwr_color = FG_POWER_OK if pwr_s >= 0 else FG_POWER_LOW
            pwr_tag = "OK" if pwr_s >= 0 else "LOW"

            tk.Label(
                self._body,
                text=f" {name}{you}  ${house.credits or 0}",
                font=FONT_HEADER, fg=color, bg=BG_COLOR, anchor="w",
            ).pack(anchor="w")

            tk.Label(
                self._body,
                text=f"   Power {house.power_produced or 0}/{house.power_drained or 0}"
                     f" (+{pwr_s}) [{pwr_tag}]",
                font=FONT_BODY, fg=pwr_color, bg=BG_COLOR, anchor="w",
            ).pack(anchor="w")

            # Summary
            tk.Label(
                self._body,
                text=f"   Bldg:{house.building_total}  Inf:{house.infantry_total}"
                     f"  Veh:{house.vehicle_total}  Nav:{house.naval_total}"
                     f"  Air:{house.aircraft_total}",
                font=FONT_BODY, fg=FG_UNKNOWN, bg=BG_COLOR, anchor="w",
            ).pack(anchor="w")

            # Detail lines (ALL units, no truncation)
            for cat_name, cat_entries in [
                ("Building", house.buildings),
                ("Infantry", house.infantry),
                ("Vehicle", house.vehicles),
                ("Naval", house.naval),
                ("Aircraft", house.aircraft),
            ]:
                if not cat_entries:
                    continue
                cat_color = CATEGORY_COLORS[cat_name]
                lines = self._format_entries(cat_entries)
                tk.Label(
                    self._body,
                    text=f"   [{cat_name}] {lines[0]}",
                    font=FONT_BODY, fg=cat_color, bg=BG_COLOR, anchor="w",
                ).pack(anchor="w")
                pad = " " * (len(cat_name) + 4)
                for cont in lines[1:]:
                    tk.Label(
                        self._body, text=f"   {pad}{cont}",
                        font=FONT_BODY, fg=cat_color, bg=BG_COLOR, anchor="w",
                    ).pack(anchor="w")

            # Separator
            tk.Frame(self._body, bg=FG_SEPARATOR, height=1).pack(fill="x", pady=2)

    # ── Refresh loop ───────────────────────────────────────────────────────
    def _refresh(self) -> None:
        """Read game state and update overlay. Handles attach/detach lifecycle."""
        if self._hwnd:
            SetWindowPos(self._hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                         SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)

        if self._reader is None:
            reader = GameReader()
            if reader.attach():
                self._reader = reader
                logger.info("Game detected, attached")
            else:
                self._show_status("Waiting for game...")
                self.root.after(REFRESH_MS, self._refresh)
                return

        try:
            state = self._reader.read_game_state()
            self._update_display(state)
        except Exception as e:
            logger.warning("Refresh error: %s", e)
            try:
                self._reader.detach()
            except Exception:
                pass
            self._reader = None
            self._show_status("Game lost, waiting...")

        self.root.after(REFRESH_MS, self._refresh)

    def _show_status(self, text: str) -> None:
        """Show a single status line on the overlay."""
        for w in self._body.winfo_children():
            w.destroy()
        tk.Label(
            self._body, text=f"  {text}",
            font=FONT_STATUS, fg=FG_HEADER, bg=BG_COLOR, anchor="w",
        ).pack(anchor="w")

    def run(self) -> None:
        self.root.mainloop()

    def cleanup(self) -> None:
        if self._hwnd:
            UnregisterHotKey(self._hwnd, HOTKEY_ID)
        if self._reader:
            try:
                self._reader.detach()
            except Exception:
                pass


def run_overlay() -> None:
    """Entry point: show overlay, auto-wait for game."""
    app = None
    try:
        app = OverlayApp()
        app.run()
    finally:
        if app:
            app.cleanup()
