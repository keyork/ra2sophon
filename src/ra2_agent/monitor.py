"""Monitor mode - continuously read and display game state.

Shows comprehensive dual-faction state with per-type breakdowns.
Auto-reconnects when game opens/closes.
"""

from __future__ import annotations

import os
import sys
import time
import logging

from .reader import GameReader

logger = logging.getLogger(__name__)


def format_monitor(state) -> str:
    """Format the full game state for terminal display."""
    lines = []
    lines.append("=" * 60)
    lines.append("  RA2:YR State Monitor  (Ctrl+C to stop)")
    lines.append("=" * 60)

    active = state.active_houses

    if not active:
        if state.player_ptr == 0:
            lines.append("  (Not in battle - in menu or lobby)")
        else:
            lines.append(f"  PlayerPtr: 0x{state.player_ptr:08X}")
            lines.append("  (No active houses - game may be loading)")
        lines.append("=" * 60)
        return "\n".join(lines)

    from .type_stats import format_faction_state

    for house in active:
        lines.append(format_faction_state(house, show_breakdown=True))
        lines.append("")

    if len(active) >= 2:
        lines.append("-" * 60)
        for house in active:
            name = house.house_type_name or f"P{house.array_index}"
            tag = " *" if house.is_current_player else ""
            lines.append(
                f"  {name}{tag}: "
                f"${house.credits or 0}  "
                f"Pwr {house.power_surplus:+d}  "
                f"Bldg:{house.building_total} "
                f"Units:{house.vehicle_total}"
            )

    lines.append("=" * 60)
    return "\n".join(lines)


def run_monitor(interval: float = 1.0) -> None:
    """Run continuous game state monitoring with auto-reconnect."""
    reader = GameReader()
    retry_delay = 2.0

    try:
        while True:
            if not reader.attach():
                os.system("cls" if os.name == "nt" else "clear")
                print("  Waiting for game... (Ctrl+C to stop)")
                time.sleep(retry_delay)
                continue

            try:
                while True:
                    os.system("cls" if os.name == "nt" else "clear")
                    try:
                        state = reader.read_game_state()
                        print(format_monitor(state))
                    except Exception as e:
                        print(f"  Read error: {e}")
                        print(f"  (Game may have closed)")
                        break

                    sys.stdout.flush()
                    time.sleep(interval)

            except KeyboardInterrupt:
                raise

            reader.detach()
            os.system("cls" if os.name == "nt" else "clear")
            print("  Game disconnected. Waiting for reconnect...")
            time.sleep(retry_delay)

    except KeyboardInterrupt:
        print("\n  Monitor stopped.")
    finally:
        if reader.is_attached:
            reader.detach()
