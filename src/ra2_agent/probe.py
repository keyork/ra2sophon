"""Memory probe for discovering HouseClass member offsets.

Reads a chunk of memory from a HouseClass instance and helps identify
where credits, power, and other fields are located by:

1. Hex dumping the memory region
2. Scanning for known int32 values (e.g. current credits)
3. Comparing two dumps to find changed fields
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from .reader import GameReader

logger = logging.getLogger(__name__)

# How much memory to dump from a HouseClass instance
# HouseClass is large (~0x2000 bytes estimated), dump a generous range
PROBE_SIZE = 0x2000


def hex_dump(data: bytes, base_addr: int, width: int = 16) -> str:
    """Format bytes as a hex dump with address column."""
    lines = []
    for offset in range(0, len(data), width):
        chunk = data[offset:offset + width]
        hex_part = " ".join(f"{b:02X}" for b in chunk)
        ascii_part = "".join(
            chr(b) if 0x20 <= b < 0x7F else "." for b in chunk
        )
        lines.append(f"  0x{base_addr + offset:08X}  {hex_part:<{width * 3}}  {ascii_part}")
    return "\n".join(lines)


def scan_for_int32(data: bytes, target: int, base_addr: int) -> list[int]:
    """Scan a byte buffer for a little-endian int32 value.
    Returns list of offsets where the value was found."""
    import struct
    target_bytes = struct.pack("<i", target)
    offsets = []
    pos = 0
    while pos <= len(data) - 4:
        idx = data.find(target_bytes, pos)
        if idx < 0:
            break
        offsets.append(base_addr + idx)
        pos = idx + 1
    return offsets


def scan_for_uint32(data: bytes, target: int, base_addr: int) -> list[int]:
    """Scan for unsigned int32."""
    import struct
    target_bytes = struct.pack("<I", target)
    offsets = []
    pos = 0
    while pos <= len(data) - 4:
        idx = data.find(target_bytes, pos)
        if idx < 0:
            break
        offsets.append(base_addr + idx)
        pos = idx + 1
    return offsets


class MemoryProbe:
    """Interactive probe for discovering HouseClass field offsets."""

    def __init__(self, reader: GameReader) -> None:
        self.reader = reader
        self._baseline: Optional[bytes] = None
        self._baseline_addr: int = 0

    def dump_houseclass(self, address: int, size: int = PROBE_SIZE) -> bytes:
        """Dump raw bytes from a HouseClass instance."""
        return self.reader.read_bytes(address, size)

    def scan_credits(self, house_addr: int, credits_value: int) -> list[int]:
        """Search for a credits value within a HouseClass instance.

        Usage: Look at your credits in-game, pass the number here,
        and we'll tell you which offsets match.
        """
        data = self.dump_houseclass(house_addr)
        signed_hits = scan_for_int32(data, credits_value, house_addr)
        unsigned_hits = scan_for_uint32(data, credits_value, house_addr)
        # Deduplicate (positive values match both signed and unsigned)
        all_hits = sorted(set(signed_hits + unsigned_hits))
        return all_hits

    def snapshot(self, house_addr: int) -> None:
        """Take a baseline snapshot for diff comparison."""
        self._baseline = self.dump_houseclass(house_addr)
        self._baseline_addr = house_addr
        logger.info("Snapshot taken at 0x%X (%d bytes)", house_addr, len(self._baseline))

    def diff(self, house_addr: int) -> list[tuple[int, int, int]]:
        """Compare current memory against baseline snapshot.

        Returns list of (offset, old_value, new_value) for changed int32 fields.
        Only reports fields that changed as int32 values.
        """
        if not self._baseline:
            logger.error("No baseline snapshot. Call snapshot() first.")
            return []

        import struct
        current = self.dump_houseclass(house_addr)
        changes = []

        min_len = min(len(self._baseline), len(current))
        for offset in range(0, min_len - 3, 4):
            old_val = struct.unpack("<i", self._baseline[offset:offset + 4])[0]
            new_val = struct.unpack("<i", current[offset:offset + 4])[0]
            if old_val != new_val:
                changes.append((self._baseline_addr + offset, old_val, new_val))

        return changes

    def interactive_scan(self, house_addr: int) -> None:
        """Interactive CLI for scanning offsets.

        First pass: enter a known value (like credits), find candidates.
        Second pass: change the value in-game, re-scan to narrow down.
        """
        print(f"\n{'='*60}")
        print(f" Memory Probe — HouseClass @ 0x{house_addr:08X}")
        print(f"{'='*60}")

        candidates: list[int] = []

        while True:
            print(f"\nCommands:")
            print(f"  s <value>  — Scan for int32 value (narrow candidates)")
            print(f"  d          — Dump first 0x200 bytes as hex")
            print(f"  d <offset> — Dump 0x80 bytes starting at offset")
            print(f"  snap       — Take baseline snapshot")
            print(f"  diff       — Compare against snapshot")
            print(f"  reset      — Reset candidates (start over)")
            print(f"  r <addr>   — Read int32 at absolute address")
            print(f"  q          — Quit probe")
            print(f"  Candidates: {len(candidates)}")

            try:
                cmd = input("\n> ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not cmd:
                continue

            parts = cmd.split()
            action = parts[0].lower()

            if action == "q":
                break

            elif action == "s" and len(parts) >= 2:
                try:
                    target = int(parts[1])
                except ValueError:
                    print("Invalid number.")
                    continue

                data = self.dump_houseclass(house_addr)

                if candidates:
                    # Narrow existing candidates
                    new_hits = scan_for_int32(data, target, house_addr)
                    new_hits += scan_for_uint32(data, target, house_addr)
                    new_hits = sorted(set(new_hits))
                    candidates = [c for c in candidates if c in new_hits]
                else:
                    candidates = self.scan_credits(house_addr, target)

                print(f"\nFound {len(candidates)} candidate(s):")
                for addr in candidates:
                    offset = addr - house_addr
                    print(f"  HouseClass + 0x{offset:03X}  (abs: 0x{addr:08X})")

            elif action == "d":
                try:
                    start_offset = int(parts[1], 0) if len(parts) >= 2 else 0
                except ValueError:
                    start_offset = 0
                size = 0x80
                data = self.dump_houseclass(house_addr)
                start_offset = min(start_offset, len(data) - size)
                chunk = data[start_offset:start_offset + size]
                print(hex_dump(chunk, house_addr + start_offset))

            elif action == "snap":
                self.snapshot(house_addr)
                print("Baseline snapshot saved.")

            elif action == "diff":
                changes = self.diff(house_addr)
                if not changes:
                    print("No changes detected.")
                else:
                    print(f"\n{len(changes)} changed int32 field(s):")
                    for addr, old, new in changes:
                        offset = addr - house_addr
                        print(f"  +0x{offset:03X}  (0x{addr:08X}):  {old} → {new}")

            elif action == "reset":
                candidates = []
                print("Candidates reset.")

            elif action == "r" and len(parts) >= 2:
                try:
                    addr = int(parts[1], 0)
                    val = self.reader.read_int(addr)
                    print(f"  [0x{addr:08X}] = {val} (0x{val & 0xFFFFFFFF:08X})")
                except Exception as e:
                    print(f"  Error: {e}")
