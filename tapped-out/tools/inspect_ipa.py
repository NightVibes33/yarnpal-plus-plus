#!/usr/bin/env python3
import argparse
import plistlib
import struct
import sys
import zipfile

CPU_NAMES = {
    7: "x86",
    0x01000007: "x86_64",
    12: "armv7/arm",
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


def parse_macho_arches(blob: bytes):
    magic = blob[:4]
    if magic in MH_MAGICS:
        endian, _bits = MH_MAGICS[magic]
        cputype = struct.unpack_from(endian + "I", blob, 4)[0]
        return [cpu_name(cputype)]

    if magic in FAT_MAGICS:
        endian, fatbits = FAT_MAGICS[magic]
        nfat = struct.unpack_from(endian + "I", blob, 4)[0]
        arches = []
        offset = 8
        entry_size = 20 if fatbits == 32 else 32
        for _ in range(nfat):
            cputype = struct.unpack_from(endian + "I", blob, offset)[0]
            arches.append(cpu_name(cputype))
            offset += entry_size
        return arches

    return ["unknown/non-Mach-O"]


def main():
    parser = argparse.ArgumentParser(description="Inspect iOS IPA metadata and CPU slices.")
    parser.add_argument("ipa")
    args = parser.parse_args()

    with zipfile.ZipFile(args.ipa) as archive:
        infos = [
            name
            for name in archive.namelist()
            if name.startswith("Payload/")
            and name.count("/") == 2
            and name.endswith(".app/Info.plist")
        ]
        if not infos:
            raise SystemExit("No Payload/*.app/Info.plist found")

        info_name = infos[0]
        app_prefix = info_name[: -len("Info.plist")]
        info = plistlib.loads(archive.read(info_name))
        executable = info.get("CFBundleExecutable")
        if not executable:
            raise SystemExit("CFBundleExecutable missing")

        macho = archive.read(app_prefix + executable)
        arches = parse_macho_arches(macho)

    print(f"Bundle ID: {info.get('CFBundleIdentifier')}")
    print(f"Version: {info.get('CFBundleVersion')}")
    print(f"Minimum iOS: {info.get('MinimumOSVersion')}")
    print(f"SDK: {info.get('DTSDKName')}")
    print(f"Executable: {executable}")
    print("Architectures: " + ", ".join(arches))

    if "arm64" in arches:
        print("Modern arm64 iOS compatibility gate: PASS")
        return 0

    print("Modern arm64 iOS compatibility gate: FAIL")
    print(
        "This binary cannot be made runnable on arm64/arm64e by re-signing or Info.plist edits; "
        "an arm64 executable slice or a source rebuild is required."
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
