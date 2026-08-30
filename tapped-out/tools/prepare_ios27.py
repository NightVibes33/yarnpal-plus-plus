#!/usr/bin/env python3
"""Prepare a 64-bit iOS IPA for iPhone 16 / modern iOS signing.

This does not translate 32-bit ARM code. It validates that every Mach-O in the
bundle has an arm64 slice, removes stale signing material, and repackages the
app as an unsigned IPA for re-signing with the owner's certificate/profile.
"""
from __future__ import annotations

import argparse
import os
import plistlib
import shutil
import struct
import sys
import tempfile
import zipfile
from pathlib import Path

CPU_TYPE_ARM64 = 0x0100000C
THIN_MAGICS = {
    b"\xce\xfa\xed\xfe": ("<", 32),
    b"\xfe\xed\xfa\xce": (">", 32),
    b"\xcf\xfa\xed\xfe": ("<", 64),
    b"\xfe\xed\xfa\xcf": (">", 64),
}
FAT_MAGICS = {
    b"\xca\xfe\xba\xbe": (">", 32),
    b"\xbe\xba\xfe\xca": ("<", 32),
    b"\xca\xfe\xba\xbf": (">", 64),
    b"\xbf\xba\xfe\xca": ("<", 64),
}


def macho_cputypes(path: Path):
    try:
        data = path.read_bytes()
    except Exception:
        return None
    if len(data) < 8:
        return None
    magic = data[:4]
    if magic in THIN_MAGICS:
        endian, _ = THIN_MAGICS[magic]
        return [struct.unpack_from(endian + "I", data, 4)[0]]
    if magic in FAT_MAGICS:
        endian, bits = FAT_MAGICS[magic]
        nfat = struct.unpack_from(endian + "I", data, 4)[0]
        entry_size = 20 if bits == 32 else 32
        off = 8
        result = []
        for _ in range(nfat):
            if off + entry_size > len(data):
                break
            result.append(struct.unpack_from(endian + "I", data, off)[0])
            off += entry_size
        return result
    return None


def contains_arm64(path: Path) -> bool:
    types = macho_cputypes(path)
    return types is not None and CPU_TYPE_ARM64 in types


def find_app(payload: Path) -> Path:
    apps = sorted(p for p in payload.glob("*.app") if p.is_dir())
    if len(apps) != 1:
        raise RuntimeError(f"Expected one Payload/*.app, found {len(apps)}")
    return apps[0]


def remove_signing_material(root: Path):
    for sig in list(root.rglob("_CodeSignature")):
        if sig.is_dir():
            shutil.rmtree(sig)
    for provision in root.rglob("embedded.mobileprovision"):
        provision.unlink(missing_ok=True)


def zip_payload(work: Path, output: Path):
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        payload = work / "Payload"
        for path in sorted(payload.rglob("*")):
            if path.is_file() or path.is_symlink():
                zf.write(path, path.relative_to(work))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input_ipa", type=Path)
    ap.add_argument("output_ipa", type=Path)
    args = ap.parse_args()

    with tempfile.TemporaryDirectory(prefix="tsto-ios27-") as td:
        work = Path(td)
        with zipfile.ZipFile(args.input_ipa) as zf:
            zf.extractall(work)

        app = find_app(work / "Payload")
        info_path = app / "Info.plist"
        info = plistlib.load(info_path.open("rb"))
        executable_name = info.get("CFBundleExecutable")
        if not executable_name:
            raise RuntimeError("CFBundleExecutable is missing")
        main_exe = app / executable_name

        if not contains_arm64(main_exe):
            print(f"FAIL: main executable is not arm64-capable: {main_exe.name}")
            print("The IPA must be replaced with a 64-bit client; ARMv7 cannot be header-patched into ARM64.")
            return 2

        bad = []
        checked = []
        for p in app.rglob("*"):
            if not p.is_file():
                continue
            cputypes = macho_cputypes(p)
            if cputypes is None:
                continue
            checked.append(p.relative_to(app))
            if CPU_TYPE_ARM64 not in cputypes:
                bad.append(p.relative_to(app))

        if bad:
            print("FAIL: embedded Mach-O files without arm64 slices:")
            for p in bad:
                print(f"  - {p}")
            return 3

        remove_signing_material(app)
        zip_payload(work, args.output_ipa)

        print(f"PASS: {info.get('CFBundleIdentifier', '<unknown bundle>')}")
        print(f"Version: {info.get('CFBundleShortVersionString') or info.get('CFBundleVersion', '<unknown>')}")
        print(f"Validated Mach-O files: {len(checked)}")
        print(f"Unsigned iPhone 16/iOS 27-ready package: {args.output_ipa}")
        print("Next step: sign the output IPA with a valid iOS development/distribution identity and provisioning profile.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
