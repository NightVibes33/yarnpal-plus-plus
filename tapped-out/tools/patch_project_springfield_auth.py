#!/usr/bin/env python3
import argparse
import plistlib
import tempfile
import zipfile
from pathlib import Path

TARGET_VERSION = "4.69.5"
NEW_HOST = b"https://test.pjtsto.com"
OLD_HOSTS = (
    b"https://auth.tnt-ea.com",
    b"https://nucleus.tnt-ea.com",
)


def fixed_c_string(old: bytes, new: bytes) -> bytes:
    if len(new) > len(old):
        raise ValueError(f"replacement is too long: {len(new)} > {len(old)}")
    # Zero padding is valid for these embedded C strings and ensures bytes left
    # from a longer old hostname are never interpreted as part of the new URL.
    return new + (b"\0" * (len(old) - len(new)))


def main():
    ap = argparse.ArgumentParser(description="Patch TSTO 4.69.5 TNT/Nucleus auth hosts to Project Springfield")
    ap.add_argument("input_ipa")
    ap.add_argument("output_ipa")
    args = ap.parse_args()

    src = Path(args.input_ipa)
    dst = Path(args.output_ipa)

    with tempfile.TemporaryDirectory(prefix="tsto-authfix-") as td:
        root = Path(td)
        with zipfile.ZipFile(src, "r") as zf:
            zf.extractall(root)

        apps = list((root / "Payload").glob("*.app"))
        if len(apps) != 1:
            raise SystemExit(f"expected exactly one app, found {len(apps)}")
        app = apps[0]
        info = plistlib.loads((app / "Info.plist").read_bytes())
        version = str(info.get("CFBundleShortVersionString") or info.get("CFBundleVersion") or "")
        if version != TARGET_VERSION:
            raise SystemExit(f"refusing to patch version {version!r}; expected {TARGET_VERSION}")

        exe = app / info["CFBundleExecutable"]
        blob = bytearray(exe.read_bytes())

        total = 0
        for old in OLD_HOSTS:
            count = blob.count(old)
            print(f"{old.decode()}: {count} occurrence(s)")
            if count < 1:
                # It may already have been patched; accept that only when the
                # Project Springfield hostname is present in the executable.
                continue
            blob = blob.replace(old, fixed_c_string(old, NEW_HOST))
            total += count

        if total == 0 and NEW_HOST not in blob:
            raise SystemExit("no known auth hosts found and Project Springfield host is absent")

        for old in OLD_HOSTS:
            if old in blob:
                raise SystemExit(f"dead EA auth host still present after patch: {old.decode()}")

        if NEW_HOST not in blob:
            raise SystemExit("Project Springfield auth host missing after patch")

        exe.write_bytes(blob)
        print(f"patched {total} dead EA auth-host occurrence(s) -> {NEW_HOST.decode()}")

        with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for p in sorted(root.rglob("*")):
                if p.is_file():
                    zf.write(p, p.relative_to(root).as_posix())

    print(f"wrote {dst}")


if __name__ == "__main__":
    main()
