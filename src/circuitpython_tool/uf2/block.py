"""UF2 block parsing and unparsing.

Based on specification at https://github.com/microsoft/uf2
"""

from collections.abc import Iterator
from dataclasses import dataclass, fields
from enum import IntFlag
from struct import Struct
from typing import Any, TypeAlias

import rich.repr

Buffer: TypeAlias = bytes | bytearray | memoryview


@dataclass
class Block:
    MAGIC_START_0 = 0x0A324655
    MAGIC_START_1 = 0x9E5D5157
    MAGIC_END = 0x0AB16F30

    class Flags(IntFlag):
        NOT_MAIN_FLASH = 0x00000001
        FILE_CONTAINER = 0x00001000
        HAS_FAMILY_ID = 0x00002000
        HAS_MD5_CHECKSUM = 0x00004000
        HAS_EXTENSIONS = 0x00008000

    flags: Flags
    address: int
    block_number: int
    total_block_count: int
    family_id: int
    payload: bytes

    def __rich_repr__(self) -> rich.repr.Result:
        for field in fields(self):
            value: Any = getattr(self, field.name)
            if field.type == int:
                value = HexInt(value)
            elif field.type == bytes:
                value = HexBytes(value)
            yield field.name, value

    @staticmethod
    def from_bytes(raw: Buffer) -> "Block":
        """Parse 512-byte raw blob into a Block."""
        if (size := len(raw)) != 512:
            raise ValueError(f"Expected UF2 block size of 512, got: {size}")
        (
            magic_start_0,
            magic_start_1,
            flags,
            address,
            payload_size,
            block_number,
            total_block_count,
            family_id,
            payload,
            magic_end,
        ) = struct.unpack(raw)

        magic = (magic_start_0, magic_start_1, magic_end)
        expected_magic = (Block.MAGIC_START_0, Block.MAGIC_START_1, Block.MAGIC_END)
        if magic != expected_magic:
            raise ValueError(
                "Expected magic numbers "
                "(two 32-bit integers at start and one 32-bit integer at end) are "
                f"{expected_magic}, got: {magic}",
            )

        return Block(
            flags=Block.Flags(flags),
            address=address,
            block_number=block_number,
            total_block_count=total_block_count,
            family_id=family_id,
            payload=payload[:payload_size],
        )

    @staticmethod
    def from_bytes_multi(raw: Buffer) -> Iterator["Block"]:
        """Iterate over UF2 blocks in a buffer."""
        if (size := len(raw)) % 512 != 0:
            raise ValueError(f"Provided buffer's size is not a multiple of 512: {size}")
        for offset in range(0, size, 512):
            yield Block.from_bytes(raw[offset : offset + 512])

    def to_bytes(self) -> bytes:
        """Unparse Block into a 512-byte raw blob."""
        return struct.pack(
            Block.MAGIC_START_0,
            Block.MAGIC_START_1,
            self.flags,
            self.address,
            len(self.payload),
            self.block_number,
            self.total_block_count,
            self.family_id,
            self.payload,
            self.MAGIC_END,
        )


class HexInt(int):
    """int subclass with hex output in its __repr__."""

    def __repr__(self) -> str:
        return f"<0x{self:X} ({self:d})>"


class HexBytes(bytes):
    """bytes subclass with alternative __repr__ implementation"""

    def __repr__(self) -> str:
        return f"<{len(self)} bytes: {self.hex(' ', 2)}>"


struct = Struct("< 8I 476s I")
assert struct.size == 512
