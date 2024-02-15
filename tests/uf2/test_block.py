from pytest import raises

from circuitpython_tool.uf2 import Block

Flags = Block.Flags


def raw_block(
    magic_start_0: int = Block.MAGIC_START_0,
    magic_start_1: int = Block.MAGIC_START_1,
    magic_end: int = Block.MAGIC_END,
) -> bytearray:
    """A UF2 raw block with the magic numbers as specified, and all other bytes cleared."""

    def to_bytes(x: int) -> bytes:
        return x.to_bytes(4, "little")

    block = bytearray([0] * 512)
    block[0:4] = to_bytes(magic_start_0)
    block[4:8] = to_bytes(magic_start_1)
    block[-4:] = to_bytes(magic_end)
    return block


def test_incorrect_block_size() -> None:
    with raises(ValueError, match="123"):
        Block.from_bytes(bytes([0] * 123))


def test_invalid_magic_start0() -> None:
    with raises(ValueError):
        Block.from_bytes(raw_block(magic_start_0=0))


def test_invalid_magic_start1() -> None:
    with raises(ValueError):
        Block.from_bytes(raw_block(magic_start_1=0))


def test_invalid_magic_end() -> None:
    with raises(ValueError):
        Block.from_bytes(raw_block(magic_end=0))


def test_empty_block() -> None:
    assert Block.from_bytes(raw_block()) == Block(
        flags=Flags(0),
        address=0,
        block_number=0,
        total_block_count=0,
        family_id=0,
        payload=b"",
    )


def test_fields() -> None:
    raw = raw_block()
    raw[8:12] = bytes([0, 0xA0, 0, 0])  # flags
    raw[12:16] = bytes([1, 0, 0, 0])  # address
    raw[16:20] = bytes([2, 0, 0, 0])  # payload size
    raw[20:24] = bytes([3, 0, 0, 0])  # block number
    raw[24:28] = bytes([4, 0, 0, 0])  # total block count
    raw[28:32] = bytes([5, 0, 0, 0])  # family
    raw[32:34] = b"ab"  # payload

    assert Block.from_bytes(raw) == Block(
        flags=Flags.HAS_FAMILY_ID | Flags.HAS_EXTENSIONS,
        address=1,
        block_number=3,
        total_block_count=4,
        family_id=5,
        payload=b"ab",
    )


def test_round_trip() -> None:
    """Test that bytes<->Block conversion round-trips."""
    raw = raw_block()
    for i in range(12, 508):
        raw[i] = i % 256
    # Set payload size to full range, as we don't preserve the padded payload bytes.
    raw[16:20] = (476).to_bytes(4, "little")
    assert Block.from_bytes(raw).to_bytes() == raw
