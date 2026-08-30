#!/usr/bin/env python3
import argparse
import plistlib
import struct
import sys
import zipfile

TARGET_VERSION = "4.69.5"
ARM64 = 0x0100000C

CPU_NAMES = {
    7: "x86",
    0x01000007: "x86_64",
    12: "arm",
    0x0100000C: "arm64",
}

MH_MAGICS = {
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


def cpu_name(cputype):
    return CPU_NAMES.get(cputype, f"cputype={cputype:#x}")


def parse_macho_cputypes(blob: bytes):
    magic = blob[:4]
    if magic in MH_MAGICS:
        endian, _bits = MH_MAGICS[magic]
        return [struct.unpack_from(endian + "I", blob, 4)[0]]

    if magic in FAT_MAGICS:
        endian, fatbits = FAT_MAGICS[magic]
        nfat = struct.unpack_from(endian + "I", blob, 4)[0]
        out = []
        offset = 8
        entry_size = 20 if fatbits == 32 else 32
        for _ in range(nfat):
            out.append(struct.unpack_from(endian + "I", blob, offset)[0])
            offset += entry_size
        return out

    return []


def main():
    parser = argparse.ArgumentParser(
        description="Verify a Tapped Out 4.69.5 IPA for iPhone 16 / iOS 27 arm64 compatibility."
    )
    parser.add_argument("ipa")
    args = parser.parse_args()

    with zipfile.ZipFile(args.ipa) as archive:
        infos = [
            name for name in archive.namelist()
            if name.startswith("Payload/")
            and name.count("/") == 2
            and name.endswith(".app/Info.plist")
        ]
        if not infos:
            raise SystemExit("No Payload/*.app/Info.plist found")

        info_name = infos[0]
        app_prefix = info_name[:-len("Info.plist")]
        info = plistlib.loads(archive.read(info_name))
        executable = info.get("CFBundleExecutable")
        if not executable:
            raise SystemExit("CFBundleExecutable missing")

        version = str(info.get("CFBundleShortVersionString") or info.get("CFBundleVersion") or "")
        main_path = app_prefix + executable
        main_types = parse_macho_cputypes(archive.read(main_path))

        macho_rows = []
        incompatible = []
        for name in archive.namelist():
            if not name.startswith(app_prefix) or name.endswith("/"):
                continue
            try:
                blob = archive.read(name)
            except Exception:
                continue
            cputypes = parse_macho_cputypes(blob)
            if not cputypes:
                continue
            arches = [cpu_name(c) for c in cputypes]
            macho_rows.append((name, arches))
            if ARM64 not in cputypes:
                incompatible.append((name, arches))

    print(f"Bundle ID: {info.get('CFBundleIdentifier')}")
    print(f"Version: {version}")
    print(f"Build: {info.get('CFBundleVersion')}")
    print(f"Minimum iOS: {info.get('MinimumOSVersion')}")
    print(f"SDK: {info.get('DTSDKName')}")
    print(f"Executable: {executable}")
    print("Main architectures: " + ", ".join(cpu_name(c) for c in main_types))
    print(f"Mach-O files checked: {len(macho_rows)}")

    ok = True
    if version != TARGET_VERSION:
        print(f"Version gate: FAIL (expected {TARGET_VERSION})")
        ok = False
    else:
        print("Version gate: PASS")

    if ARM64 not in main_types:
        print("Main arm64 gate: FAIL")
        ok = False
    else:
        print("Main arm64 gate: PASS")

    if incompatible:
        print("Embedded Mach-O arm64 gate: FAIL")
        for name, arches in incompatible:
            print(f"  {name}: {', '.join(arches)}")
        ok = False
    else:
        print("Embedded Mach-O arm64 gate: PASS")

    print("Target: iPhone 16 / iOS 27")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
