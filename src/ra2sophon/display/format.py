"""Terminal display formatting for RA2:YR game state.

Consolidates all formatting functions for game state display.
"""

from __future__ import annotations

from ..memory.types import TypeCount


def format_breakdown(entries: list[TypeCount], indent: str = "    ") -> str:
    """Format a list of TypeCount as a compact line."""
    if not entries:
        return f"{indent}(none)"
    parts = [f"{e.name} x{e.count}" for e in entries]
    return indent + "  ".join(parts)


def format_faction_state(house, show_breakdown: bool = True) -> str:
    """Format a single house's state for display."""
    lines = []

    tag = "(YOU)" if house.is_current_player else ""
    name = house.house_type_name or f"House#{house.array_index}"
    lines.append(f"  -- {name} {tag} --")

    surplus = house.power_surplus
    pwr_status = "OK" if surplus >= 0 else "LOW!"
    lines.append(
        f"    Money: ${house.credits or 0:>6}   "
        f"Power: {house.power_produced or 0}/{house.power_drained or 0} "
        f"(+{surplus}) [{pwr_status}]"
    )

    lines.append(
        f"    Buildings: {house.building_total}   "
        f"Units: {house.vehicle_total}"
    )

    if not show_breakdown:
        return "\n".join(lines)

    if house.buildings:
        lines.append(f"    Buildings: {format_breakdown(house.buildings)}")
    if house.vehicles:
        lines.append(f"    Units:     {format_breakdown(house.vehicles)}")

    return "\n".join(lines)


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
