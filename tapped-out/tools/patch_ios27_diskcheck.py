#!/usr/bin/env python3
import argparse
import tempfile
import zipfile
from pathlib import Path

# Tapped Out 4.69.5 ARM64, function at VA 0x100018190.
# The function calls the legacy free-space routine, compares the result to
# 0x400000 bytes and presents GEN_DiskFullHeader / GEN_DiskFullMessage when
# the reported value is lower. On modern iOS the legacy routine can report a
# bogus low value. Replace the function entry with `mov w0,#1; ret` so this
# obsolete guard always reports sufficient space.
FILE_OFFSET = 0x18190
EXPECTED = bytes.fromhex("f85fbca9f65701a9")
PATCH = bytes.fromhex("20008052c0035fd6")  # mov w0,#1 ; ret


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_ipa")
    ap.add_argument("output_ipa")
    args = ap.parse_args()

    src = Path(args.input_ipa)
    dst = Path(args.output_ipa)

    with tempfile.TemporaryDirectory(prefix="tsto-diskfix-") as td:
        root = Path(td)
        with zipfile.ZipFile(src, "r") as zf:
            zf.extractall(root)

        apps = list((root / "Payload").glob("*.app"))
        if len(apps) != 1:
            raise SystemExit(f"expected one app, found {len(apps)}")
        app = apps[0]

        import plistlib
        info = plistlib.loads((app / "Info.plist").read_bytes())
        exe = app / info["CFBundleExecutable"]
        blob = bytearray(exe.read_bytes())

        got = bytes(blob[FILE_OFFSET:FILE_OFFSET + len(EXPECTED)])
        if got == PATCH:
            print("iOS 27 disk-space guard already patched")
        elif got != EXPECTED:
            raise SystemExit(
                f"refusing unsafe patch at 0x{FILE_OFFSET:x}: "
                f"expected {EXPECTED.hex()}, got {got.hex()}"
            )
        else:
            blob[FILE_OFFSET:FILE_OFFSET + len(PATCH)] = PATCH
            exe.write_bytes(blob)
            print(f"patched legacy disk-space guard at file offset 0x{FILE_OFFSET:x}")

        with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for p in sorted(root.rglob("*")):
                if p.is_file():
                    zf.write(p, p.relative_to(root).as_posix())

    print(f"wrote {dst}")


if __name__ == "__main__":
    main()
