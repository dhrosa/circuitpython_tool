"""UF2 block parsing and unparsing.

Based on specification at https://github.com/microsoft/uf2
"""

from dataclasses import dataclass
from enum import IntFlag
from struct import Struct


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

    @staticmethod
    def from_bytes(raw: bytes | bytearray | memoryview) -> "Block":
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
            self.payload.ljust(475, b"\0"),
            self.MAGIC_END,
        )


struct = Struct("< 8I 476s I")
assert struct.size == 512
