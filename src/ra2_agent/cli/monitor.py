"""Monitor mode - continuously read and display game state.

Shows comprehensive dual-faction state with per-type breakdowns.
Auto-reconnects when game opens/closes.
"""

from __future__ import annotations

import os
import sys
import time
import logging

from ..memory import GameReader
from ..display import format_monitor

logger = logging.getLogger(__name__)


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
