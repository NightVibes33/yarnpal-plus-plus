#!/usr/bin/env python3
import argparse
import plistlib
import shutil
import struct
import tempfile
import zipfile
from pathlib import Path

LC_SEGMENT_64 = 0x19
LC_LOAD_DYLIB = 0xC
DYLIB_PATH = b"@executable_path/Frameworks/TSTOOffline.dylib\0"
MH_MAGIC_64_LE = b"\xcf\xfa\xed\xfe"


def align8(n: int) -> int:
    return (n + 7) & ~7


def first_section_fileoff(blob: bytes, ncmds: int) -> int:
    off = 32
    result = None
    for _ in range(ncmds):
        cmd, cmdsize = struct.unpack_from("<II", blob, off)
        if cmdsize < 8:
            raise RuntimeError("invalid Mach-O load command size")
        if cmd == LC_SEGMENT_64:
            nsects = struct.unpack_from("<I", blob, off + 64)[0]
            sec = off + 72
            for _ in range(nsects):
                fileoff = struct.unpack_from("<I", blob, sec + 48)[0]
                if fileoff and (result is None or fileoff < result):
                    result = fileoff
                sec += 80
        off += cmdsize
    if result is None:
        raise RuntimeError("could not determine first Mach-O section file offset")
    return result


def has_dylib(blob: bytes, ncmds: int, path: bytes) -> bool:
    off = 32
    needle = path.rstrip(b"\0")
    for _ in range(ncmds):
        cmd, cmdsize = struct.unpack_from("<II", blob, off)
        if cmd in {0xC, 0x18, 0x1F, 0x80000018, 0x8000001C, 0x8000001F, 0x20, 0x80000020} and cmdsize >= 24:
            nameoff = struct.unpack_from("<I", blob, off + 8)[0]
            if 0 < nameoff < cmdsize:
                raw = blob[off + nameoff:off + cmdsize].split(b"\0", 1)[0]
                if raw == needle:
                    return True
        off += cmdsize
    return False


def inject(binary: Path) -> None:
    blob = bytearray(binary.read_bytes())
    if blob[:4] != MH_MAGIC_64_LE:
        raise RuntimeError("expected thin little-endian Mach-O 64 executable")

    ncmds = struct.unpack_from("<I", blob, 16)[0]
    sizeofcmds = struct.unpack_from("<I", blob, 20)[0]
    if has_dylib(blob, ncmds, DYLIB_PATH):
        print("TSTOOffline.dylib load command already present")
        return

    cmdsize = align8(24 + len(DYLIB_PATH))
    command = struct.pack("<IIIIII", LC_LOAD_DYLIB, cmdsize, 24, 0, 0, 0)
    command += DYLIB_PATH
    command += b"\0" * (cmdsize - len(command))

    insert_at = 32 + sizeofcmds
    first_section = first_section_fileoff(blob, ncmds)
    if insert_at + cmdsize > first_section:
        raise RuntimeError(
            f"not enough Mach-O header padding: need {cmdsize}, have {first_section - insert_at}"
        )
    existing = bytes(blob[insert_at:insert_at + cmdsize])
    if any(existing):
        raise RuntimeError("Mach-O header padding is not zero; refusing to overwrite")

    blob[insert_at:insert_at + cmdsize] = command
    struct.pack_into("<I", blob, 16, ncmds + 1)
    struct.pack_into("<I", blob, 20, sizeofcmds + cmdsize)
    binary.write_bytes(blob)

    print(f"injected LC_LOAD_DYLIB: {DYLIB_PATH.rstrip(bytes([0])).decode()}")
    print(f"load commands: {ncmds} -> {ncmds + 1}")
    print(f"sizeofcmds: {sizeofcmds} -> {sizeofcmds + cmdsize}")
    print(f"header padding remaining: {first_section - (insert_at + cmdsize)} bytes")


def repack(root: Path, dst: Path) -> None:
    # DLC package ZIPs are already compressed. ZIP_STORED avoids wasting CI CPU
    # recompressing gigabytes that will not shrink materially.
    with zipfile.ZipFile(dst, "w", allowZip64=True) as zf:
        for p in sorted(root.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(root).as_posix()
            compression = zipfile.ZIP_STORED if "/OfflineDLC/" in f"/{rel}" else zipfile.ZIP_DEFLATED
            zf.write(p, rel, compress_type=compression, compresslevel=9 if compression == zipfile.ZIP_DEFLATED else None)


def copy_dlc_tree(source: Path, app: Path) -> tuple[int, int]:
    if not source.is_dir():
        raise RuntimeError(f"DLC directory does not exist: {source}")
    target = app / "OfflineDLC"
    target.mkdir(parents=True, exist_ok=True)
    count = 0
    total = 0
    for src in sorted(source.rglob("*")):
        if not src.is_file():
            continue
        rel = src.relative_to(source)
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        count += 1
        total += src.stat().st_size
    if count == 0:
        raise RuntimeError("DLC directory is empty")
    return count, total


def main() -> None:
    ap = argparse.ArgumentParser(description="Inject the embedded TSTOOffline ARM64 dylib into Tapped Out 4.69.5")
    ap.add_argument("input_ipa")
    ap.add_argument("offline_dylib")
    ap.add_argument("output_ipa")
    ap.add_argument("--client-config")
    ap.add_argument("--gameplay-config")
    ap.add_argument("--dlc-dir", help="Verified iPhone DLC closure to bundle as OfflineDLC/")
    ap.add_argument("--dlc-manifest", help="JSON closure manifest to embed for auditing")
    args = ap.parse_args()

    src = Path(args.input_ipa)
    dylib = Path(args.offline_dylib)
    dst = Path(args.output_ipa)

    with tempfile.TemporaryDirectory(prefix="tsto-inject-") as td:
        root = Path(td)
        with zipfile.ZipFile(src, "r") as zf:
            zf.extractall(root)

        apps = list((root / "Payload").glob("*.app"))
        if len(apps) != 1:
            raise SystemExit(f"expected one app, found {len(apps)}")
        app = apps[0]
        info_path = app / "Info.plist"
        info = plistlib.loads(info_path.read_bytes())
        version = str(info.get("CFBundleShortVersionString") or info.get("CFBundleVersion") or "")
        if version != "4.69.5":
            raise SystemExit(f"expected 4.69.5, got {version!r}")

        frameworks = app / "Frameworks"
        frameworks.mkdir(exist_ok=True)
        target = frameworks / "TSTOOffline.dylib"
        shutil.copy2(dylib, target)
        target.chmod(0o755)

        if args.client_config:
            shutil.copy2(args.client_config, app / "OfflineClientConfig.pb")
        if args.gameplay_config:
            shutil.copy2(args.gameplay_config, app / "OfflineGameplayConfig.pb")

        if args.dlc_dir:
            count, total = copy_dlc_tree(Path(args.dlc_dir), app)
            info["NVOfflineDLCBundled"] = True
            info["NVOfflineDLCBundledFiles"] = count
            info["NVOfflineDLCBundledBytes"] = total
            print(f"bundled OfflineDLC: {count} files, {total} bytes")
        else:
            info["NVOfflineDLCBundled"] = False

        if args.dlc_manifest:
            shutil.copy2(args.dlc_manifest, app / "OfflineDLCManifest.json")
            info["NVOfflineDLCManifest"] = "OfflineDLCManifest.json"

        plistlib.dump(info, info_path.open("wb"), fmt=plistlib.FMT_BINARY, sort_keys=False)

        exe = app / info["CFBundleExecutable"]
        inject(exe)
        repack(root, dst)

    print(f"wrote {dst}")


if __name__ == "__main__":
    main()
