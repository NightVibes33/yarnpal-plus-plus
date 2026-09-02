#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

REFERENCE_IPA_SHA256 = "968a5b3dba2c70773ffe3f552740207cf23248141f790b2cb216bf1588e1869b"
TRUE = bytes.fromhex("20008052c0035fd6")   # mov w0,#1 ; ret
FALSE = bytes.fromhex("00008052c0035fd6")  # mov w0,#0 ; ret

# 999999 (0x0F423F) returned as signed 64-bit value in x0:
#   movz x0, #0x423f
#   movk x0, #0x000f, lsl #16
#   ret
JUICE_999999 = bytes.fromhex("e04788d2e001a0f2c0035fd6")

# Expected instruction windows were read directly from Blurrr 2.3.56 / 2356.
# IMPORTANT: the Juice patch deliberately does NOT modify
# MSUserDefaultHelper.balanceJuice / juiceFromServer. Those values participate
# in account/server synchronization and caused remote templates to stop loading.
PATCHES = [
    ("MSUserDefaultHelper.isVip",              0x661A84, bytes.fromhex("f44fbea9fd7b01a9"), TRUE),
    ("MSUserDefaultHelper.monthlySVIPIsOpen",  0x665390, bytes.fromhex("f44fbea9fd7b01a9"), TRUE),
    ("MSCheckIAPReceiptModel.isTrialPeriod",   0x31F55C, bytes.fromhex("687a02f008cd47f9"), FALSE),
    ("MSCheckIAPReceiptModel.appleVip",        0x31F60C, bytes.fromhex("687a02f008e547f9"), TRUE),
    ("MSCheckIAPReceiptModel.operationVip",    0x31F62C, bytes.fromhex("687a02f008e947f9"), TRUE),
    ("MSCheckIAPReceiptModel.giftVip",         0x31F64C, bytes.fromhex("687a02f008ed47f9"), TRUE),
    ("PSAutoSubscribeModel.isValid",           0x367B4B8, bytes.fromhex("002c40fd0820601e"), TRUE),
    ("PSAutoSubscribeModel.isTrialPeriod",     0x367C45C, bytes.fromhex("00204039c0035fd6"), FALSE),
    ("PSAutoSubscribeModel.appleVip",          0x367C46C, bytes.fromhex("00244039c0035fd6"), TRUE),
    ("PSAutoSubscribeModel.giftVip",           0x367C47C, bytes.fromhex("00284039c0035fd6"), TRUE),
    ("PSAutoSubscribeModel.operationVip",      0x367C48C, bytes.fromhex("002c4039c0035fd6"), TRUE),

    # Local spend UI balance routine used by ExpendJuiceView before confirming
    # a Juice-consuming action. Forcing THIS internal balance source avoids
    # poisoning the account/server balance fields used by template APIs.
    ("ExpendJuiceView.localSpendableBalance",  0xC03BD4, bytes.fromhex("fa67bba9f85f01a9f65702a9"), JUICE_999999),
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def patch_binary(binary: Path) -> None:
    data = bytearray(binary.read_bytes())
    print(f"Executable SHA-256 before patch: {sha256(binary)}")

    for name, offset, expected, replacement in PATCHES:
        current = bytes(data[offset:offset + len(replacement)])
        if len(current) != len(replacement):
            raise RuntimeError(f"{name}: offset {offset:#x} is outside binary")

        if current == replacement:
            print(f"{name}: {offset:#x} already patched ({current.hex()})")
            continue

        if current != expected:
            raise RuntimeError(
                f"{name}: unexpected bytes at {offset:#x}: "
                f"got {current.hex()}, expected original {expected.hex()} "
                f"or patched {replacement.hex()}"
            )

        data[offset:offset + len(replacement)] = replacement
        print(f"{name}: {offset:#x} {current.hex()} -> {replacement.hex()}")

    binary.write_bytes(data)

    verify = binary.read_bytes()
    for name, offset, _expected, replacement in PATCHES:
        actual = verify[offset:offset + len(replacement)]
        if actual != replacement:
            raise RuntimeError(
                f"{name}: post-write verification failed at {offset:#x}: "
                f"got {actual.hex()}, expected {replacement.hex()}"
            )
        print(f"verified {name}: {offset:#x} = {actual.hex()}")

    print(f"Executable SHA-256 after patch: {sha256(binary)}")
    print(f"Verified {len(PATCHES)} runtime gates (premium + local spendable Juice=999999)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch.py /path/to/Payload/Aries.app/Aries")
    patch_binary(Path(sys.argv[1]))
