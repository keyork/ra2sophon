"""Terminal display formatting for RA2:YR game state.

Consolidates all formatting functions for game state display.
"""

from __future__ import annotations

from ..memory.types import TypeCount, HouseInfo, GameState


def format_breakdown(entries: list[TypeCount], indent: str = "    ") -> str:
    """Format a list of TypeCount as a compact line with Chinese names."""
    if not entries:
        return f"{indent}(none)"
    parts = [f"{e.name_cn or e.name} x{e.count}" for e in entries]
    return indent + "  ".join(parts)


def format_faction_state(house: HouseInfo, show_breakdown: bool = True) -> str:
    """Format a single house's state for display."""
    lines = []

    tag = "(YOU)" if house.is_current_player else ""
    defeated_tag = " [DEFEATED]" if house.is_defeated else ""
    name = house.house_type_name or f"House#{house.array_index}"
    lines.append(f"  -- {name} {tag}{defeated_tag} --")

    surplus = house.power_surplus
    pwr_status = "OK" if surplus >= 0 else "LOW!"
    lines.append(
        f"    Money: ${house.credits or 0:>6}   "
        f"Power: {house.power_produced or 0}/{house.power_drained or 0} "
        f"(+{surplus}) [{pwr_status}]"
    )

    lines.append(
        f"    Bldg: {house.building_total}   "
        f"Inf: {house.infantry_total}   "
        f"Veh: {house.vehicle_total}   "
        f"Nav: {house.naval_total}   "
        f"Air: {house.aircraft_total}"
    )

    if not show_breakdown:
        return "\n".join(lines)

    if house.buildings:
        lines.append(f"    Buildings: {format_breakdown(house.buildings)}")
    if house.infantry:
        lines.append(f"    Infantry:  {format_breakdown(house.infantry)}")
    if house.vehicles:
        lines.append(f"    Vehicles:  {format_breakdown(house.vehicles)}")
    if house.naval:
        lines.append(f"    Naval:     {format_breakdown(house.naval)}")
    if house.aircraft:
        lines.append(f"    Aircraft:  {format_breakdown(house.aircraft)}")

    return "\n".join(lines)


def format_monitor(state: GameState) -> str:
    """Format the full game state for terminal display."""
    lines = []
    lines.append("=" * 70)
    lines.append("  RA2:YR State Monitor  (Ctrl+C to stop)")
    lines.append("=" * 70)

    active = state.active_houses

    if not active:
        if state.player_ptr == 0:
            lines.append("  (Not in battle - in menu or lobby)")
        else:
            lines.append(f"  PlayerPtr: 0x{state.player_ptr:08X}")
            lines.append("  (No active houses - game may be loading)")
        lines.append("=" * 70)
        return "\n".join(lines)

    for house in active:
        lines.append(format_faction_state(house, show_breakdown=True))
        lines.append("")

    if len(active) >= 2:
        lines.append("-" * 70)
        for house in active:
            name = house.house_type_name or f"P{house.array_index}"
            tag = " *" if house.is_current_player else ""
            lines.append(
                f"  {name}{tag}: "
                f"${house.credits or 0}  "
                f"Pwr {house.power_surplus:+d}  "
                f"Bldg:{house.building_total} "
                f"Inf:{house.infantry_total} "
                f"Veh:{house.vehicle_total} "
                f"Nav:{house.naval_total} "
                f"Air:{house.aircraft_total}"
            )

    lines.append("=" * 70)
    return "\n".join(lines)
