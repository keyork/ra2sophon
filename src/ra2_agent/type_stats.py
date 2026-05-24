"""Unit/building type statistics for RA2:YR.

Maps type indices to type names and reads per-type counts from HouseClass counters.
"""

from __future__ import annotations

from .reader import TypeCount


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
