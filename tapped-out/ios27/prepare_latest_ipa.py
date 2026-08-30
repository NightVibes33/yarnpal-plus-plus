#!/usr/bin/env python3
import argparse
import io
import os
import plistlib
import shutil
import stat
import struct
import sys
import tempfile
import zipfile
from pathlib import Path

TARGET_VERSION = "4.69.5"
ARM64 = 0x0100000C

MH_MAGICS = {
    b"\xce\xfa\xed\xfe": ("<", False),
    b"\xfe\xed\xfa\xce": (">", False),
    b"\xcf\xfa\xed\xfe": ("<", True),
    b"\xfe\xed\xfa\xcf": (">", True),
}
FAT_MAGICS = {
    b"\xca\xfe\xba\xbe": (">", False),
    b"\xbe\xba\xfe\xca": ("<", False),
    b"\xca\xfe\xba\xbf": (">", True),
    b"\xbf\xba\xfe\xca": ("<", True),
}


def macho_cputypes(blob: bytes):
    magic = blob[:4]
    if magic in MH_MAGICS:
        endian, _is64 = MH_MAGICS[magic]
        return [struct.unpack_from(endian + "I", blob, 4)[0]]
    if magic in FAT_MAGICS:
        endian, fat64 = FAT_MAGICS[magic]
        nfat = struct.unpack_from(endian + "I", blob, 4)[0]
        offset = 8
        entry_size = 32 if fat64 else 20
        out = []
        for _ in range(nfat):
            out.append(struct.unpack_from(endian + "I", blob, offset)[0])
            offset += entry_size
        return out
    return []


def is_macho(path: Path):
    try:
        with path.open("rb") as f:
            return f.read(4) in set(MH_MAGICS) | set(FAT_MAGICS)
    except OSError:
        return False


def find_app(root: Path):
    payload = root / "Payload"
    apps = list(payload.glob("*.app"))
    if len(apps) != 1:
        raise RuntimeError(f"Expected exactly one app in Payload, found {len(apps)}")
    return apps[0]


def validate_arm64(app: Path, executable: str):
    main = app / executable
    if not main.exists():
        raise RuntimeError(f"Main executable missing: {main}")
    main_types = macho_cputypes(main.read_bytes())
    if ARM64 not in main_types:
        raise RuntimeError("Main executable has no arm64 slice; cannot run on iPhone 16/iOS 27")

    incompatible = []
    for path in app.rglob("*"):
        if not path.is_file() or not is_macho(path):
            continue
        types = macho_cputypes(path.read_bytes())
        if types and ARM64 not in types:
            incompatible.append(str(path.relative_to(app)))
    if incompatible:
        raise RuntimeError(
            "Embedded Mach-O files without arm64:\n  - " + "\n  - ".join(incompatible)
        )


def strip_signatures(app: Path):
    for sigdir in app.rglob("_CodeSignature"):
        if sigdir.is_dir():
            shutil.rmtree(sigdir)
    for name in ("embedded.mobileprovision", "CodeResources"):
        for p in app.rglob(name):
            if p.is_file():
                p.unlink()


def normalize_info(app: Path):
    info_path = app / "Info.plist"
    info = plistlib.loads(info_path.read_bytes())
    executable = info.get("CFBundleExecutable")
    if not executable:
        raise RuntimeError("CFBundleExecutable missing")

    version = str(info.get("CFBundleShortVersionString") or info.get("CFBundleVersion") or "")
    if version != TARGET_VERSION:
        print(f"WARNING: expected {TARGET_VERSION}, input reports {version or 'unknown'}", file=sys.stderr)

    caps = info.get("UIRequiredDeviceCapabilities")
    if isinstance(caps, list):
        caps = [c for c in caps if c not in ("armv7", "armv7s")]
        if "arm64" not in caps:
            caps.append("arm64")
        info["UIRequiredDeviceCapabilities"] = caps
    elif isinstance(caps, dict):
        caps.pop("armv7", None)
        caps.pop("armv7s", None)
        caps["arm64"] = True
        info["UIRequiredDeviceCapabilities"] = caps

    plistlib.dump(info, info_path.open("wb"), fmt=plistlib.FMT_BINARY, sort_keys=False)
    return info, executable


def repack(root: Path, output: Path):
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(root.rglob("*")):
            if path.is_dir():
                continue
            arc = path.relative_to(root).as_posix()
            zf.write(path, arc)


def main():
    ap = argparse.ArgumentParser(description="Prepare Tapped Out 4.69.5 for modern iOS re-signing")
    ap.add_argument("input_ipa")
    ap.add_argument("output_ipa")
    args = ap.parse_args()

    src = Path(args.input_ipa).resolve()
    dst = Path(args.output_ipa).resolve()

    with tempfile.TemporaryDirectory(prefix="tsto-ios27-") as td:
        root = Path(td)
        with zipfile.ZipFile(src, "r") as zf:
            zf.extractall(root)

        app = find_app(root)
        info, executable = normalize_info(app)
        validate_arm64(app, executable)
        strip_signatures(app)
        repack(root, dst)

    print(f"Prepared unsigned IPA: {dst}")
    print(f"Bundle: {info.get('CFBundleIdentifier')}")
    print(f"Version: {info.get('CFBundleShortVersionString') or info.get('CFBundleVersion')}")
    print("Architecture gate: PASS (arm64)")
    print("Target: iPhone 16 / iOS 27")
    print("Next step: sign the output IPA with your normal iOS signing workflow.")


if __name__ == "__main__":
    main()
