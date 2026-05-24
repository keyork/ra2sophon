"""RA2 Agent — Main entry point.

Usage:
    python -m ra2_agent          # Read game state once and print
    python -m ra2_agent probe    # Interactive memory probe for offset discovery
    python -m ra2_agent monitor  # Continuous game state monitoring
"""

from __future__ import annotations

import logging
import sys
import time

from ..memory import GameReader
from .probe import MemoryProbe
from .monitor import run_monitor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ra2_agent")


def print_state(reader: GameReader) -> None:
    """Read and display current game state."""
    state = reader.read_game_state()

    print(f"\n{'='*55}")
    print(f"  RA2:YR Game State")
    print(f"{'='*55}")
    print(f"  PlayerPtr:     0x{state.player_ptr:08X}")
    print(f"  Observer Mode: {state.observer_mode}")
    print(f"  House Count:   {len(state.houses)}")

    player = state.current_player
    if player:
        surplus = (player.power_produced or 0) - (player.power_drained or 0)
        status = "OK" if surplus >= 0 else "LOW!"
        print(f"\n  [Current Player]")
        print(f"    Credits:   ${player.credits}")
        print(f"    Spent:     ${player.credits_spent}")
        print(f"    Power:     {player.power_produced} / {player.power_drained} "
              f"(surplus: {surplus}) [{status}]")
        print(f"    Buildings: {player.building_total}    Units: {player.vehicle_total}")

    # Show other valid houses (skip empty/invalid)
    for i, house in enumerate(state.houses):
        if house.is_current_player:
            continue
        # Skip houses with no credits and no power (neutral/empty)
        if not house.credits and not house.power_produced:
            continue
        # Skip houses with obviously invalid data
        if (house.credits is not None and house.credits < 0) or \
           (house.power_produced is not None and house.power_produced < 0):
            continue
        print(f"\n  House #{i} (AI/Other): "
              f"credits=${house.credits}  "
              f"power={house.power_produced}/{house.power_drained}")

    print(f"{'='*55}\n")


def cmd_probe(reader: GameReader) -> None:
    """Launch interactive memory probe."""
    state = reader.read_game_state()
    player = state.current_player

    if not player:
        print("ERROR: Could not find current player HouseClass.")
        print(f"PlayerPtr = 0x{state.player_ptr:08X}")
        if state.player_ptr:
            print("PlayerPtr is non-zero, will probe that address directly.")
            probe = MemoryProbe(reader)
            probe.interactive_scan(state.player_ptr)
        return

    print(f"Current player HouseClass @ 0x{player.address:08X}")
    probe = MemoryProbe(reader)
    probe.interactive_scan(player.address)


def cmd_monitor(reader: GameReader) -> None:
    """Continuous game state monitoring."""
    from .monitor import run_monitor
    run_monitor(interval=1.0)


def cmd_objects(reader: GameReader) -> None:
    """Scan for player-owned objects (units, buildings, etc.)."""
    from ..memory.objects import scan_player_objects
    print("Scanning for player objects (may take 10-20s)...")
    result = scan_player_objects(reader)
    print(f"\nFound {result.total} player-owned objects:")
    print(f"  Buildings:  {len(result.buildings)}")
    print(f"  Infantry:   {len(result.infantry)}")
    print(f"  Units:      {len(result.units)}")
    print(f"  Aircraft:   {len(result.aircraft)}")

    if result.buildings:
        print(f"\n  Building addresses (first 5):")
        for obj in result.buildings[:5]:
            print(f"    0x{obj.address:08X}")

    if result.units:
        print(f"\n  Unit addresses (first 5):")
        for obj in result.units[:5]:
            print(f"    0x{obj.address:08X}")


def cmd_stats(reader: GameReader) -> None:
    """Show per-type unit/building counts for all active houses."""
    state = reader.read_game_state()
    from ..display import format_faction_state
    for house in state.active_houses:
        print(format_faction_state(house, show_breakdown=True))
        print()


def main() -> None:
    reader = GameReader()

    if not reader.attach():
        sys.exit(1)

    try:
        if len(sys.argv) > 1:
            mode = sys.argv[1].lower()
            if mode == "probe":
                cmd_probe(reader)
            elif mode == "monitor":
                cmd_monitor(reader)
            elif mode == "objects":
                cmd_objects(reader)
            elif mode == "stats":
                cmd_stats(reader)
            else:
                print(f"Unknown mode: {mode}")
                print("Usage: python -m ra2_agent [probe|monitor|objects|stats]")
        else:
            print_state(reader)
    finally:
        reader.detach()


if __name__ == "__main__":
    main()
