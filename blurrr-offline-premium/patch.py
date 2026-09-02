#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

EXPECTED_IPA_SHA256 = "968a5b3dba2c70773ffe3f552740207cf23248141f790b2cb216bf1588e1869b"
TRUE = bytes.fromhex("20008052c0035fd6")   # mov w0,#1 ; ret
FALSE = bytes.fromhex("00008052c0035fd6")  # mov w0,#0 ; ret

PATCHES = [
    ("MSUserDefaultHelper.isVip", 0x661A84, TRUE),
    ("MSUserDefaultHelper.monthlySVIPIsOpen", 0x665390, TRUE),
    ("MSCheckIAPReceiptModel.isTrialPeriod", 0x31F55C, FALSE),
    ("MSCheckIAPReceiptModel.appleVip", 0x31F60C, TRUE),
    ("MSCheckIAPReceiptModel.operationVip", 0x31F62C, TRUE),
    ("MSCheckIAPReceiptModel.giftVip", 0x31F64C, TRUE),
    ("PSAutoSubscribeModel.isValid", 0x367B4B8, TRUE),
    ("PSAutoSubscribeModel.isTrialPeriod", 0x367C45C, FALSE),
    ("PSAutoSubscribeModel.appleVip", 0x367C46C, TRUE),
    ("PSAutoSubscribeModel.giftVip", 0x367C47C, TRUE),
    ("PSAutoSubscribeModel.operationVip", 0x367C48C, TRUE),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def patch_binary(binary: Path) -> None:
    data = bytearray(binary.read_bytes())
    for name, offset, replacement in PATCHES:
        old = bytes(data[offset:offset + len(replacement)])
        if len(old) != len(replacement):
            raise RuntimeError(f"{name}: offset is outside binary")
        data[offset:offset + len(replacement)] = replacement
        print(f"{name}: {offset:#x} {old.hex()} -> {replacement.hex()}")
    binary.write_bytes(data)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch.py /path/to/Payload/Aries.app/Aries")
    patch_binary(Path(sys.argv[1]))
