#!/usr/bin/env python3
import argparse
import plistlib
import tempfile
import zipfile
from pathlib import Path

BASE = "http://127.0.0.1:31337"
DLC = BASE + "/dlc/"

# Strings used by the 4.69.5 client before server-discovery takes over.
# Replacements are fixed-size, NUL padded C strings; no Mach-O offsets move.
ROUTES = {
    "http://oct2018-4-35-0-uam5h44a.tstodlc.eamobile.com/netstorage/gameasset/direct/simpsons/": DLC,
    "http://cdn.skum.eamobile.com/skumasset/gameasset/": DLC,
    "https://syn-dir.sn.eamobile.com": BASE,
    "https://director.sn.eamobile.com": BASE,
    "https://auth.tnt-ea.com": BASE,
    "https://nucleus.tnt-ea.com": BASE,
    "https://accounts.ea.com/": BASE,
    "https://gateway.ea.com/": BASE,
    "https://user.sn.eamobile.com": BASE,
    "https://drm.sn.eamobile.com": BASE,
    "https://product.sn.eamobile.com": BASE,
    "https://ipsp.sn.eamobile.com": BASE,
    "https://ping1.tnt-ea.com": BASE,
    "https://geoip.tnt-ea.com": BASE,
    "https://m2u.sn.eamobile.com": BASE,
    "https://m2upns-game.sn.eamobile.com": BASE,
    "https://mars.tnt-ea.com": BASE,
    "https://recommendations.tnt-ea.com": BASE,
    "https://friends.gs.ea.com:443": BASE,
    "https://friends.gs.ea.com": BASE,
    "https://m.friends.dm.origin.com": BASE,
    "https://rtm.tnt-ea.com": BASE,
    "https://inbox.tnt-ea.com": BASE,
    "https://emapi.prm.data.ea.com": BASE,
    "https://pin-em.data.ea.com": BASE,
    "https://pin-river.data.ea.com": BASE,
    "https://pn.tnt-ea.com/rest/v1": BASE,
    "https://oms.origin.com/api/": BASE,
}

CRITICAL = {
    "https://syn-dir.sn.eamobile.com",
    "https://auth.tnt-ea.com",
    "https://nucleus.tnt-ea.com",
}


def fixed_replace(blob: bytes, old: str, new: str):
    old_b = old.encode("utf-8")
    new_b = new.encode("utf-8")
    count = blob.count(old_b)
    if count == 0:
        return blob, 0
    if len(new_b) > len(old_b):
        raise RuntimeError(f"replacement too long: {new!r} ({len(new_b)}) > {old!r} ({len(old_b)})")
    padded = new_b + b"\0" * (len(old_b) - len(new_b))
    return blob.replace(old_b, padded), count


def repack(root: Path, dst: Path):
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in sorted(root.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(root).as_posix())


def main():
    ap = argparse.ArgumentParser(description="Redirect Tapped Out 4.69.5 networking to the embedded localhost server")
    ap.add_argument("input_ipa")
    ap.add_argument("output_ipa")
    args = ap.parse_args()

    src = Path(args.input_ipa)
    dst = Path(args.output_ipa)

    with tempfile.TemporaryDirectory(prefix="tsto-localhost-") as td:
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
            raise SystemExit(f"refusing version {version!r}; expected 4.69.5")

        exe_name = info.get("CFBundleExecutable")
        if not exe_name:
            raise SystemExit("CFBundleExecutable missing")
        exe = app / exe_name
        blob = exe.read_bytes()

        counts = {}
        for old, new in ROUTES.items():
            try:
                blob, count = fixed_replace(blob, old, new)
            except RuntimeError as exc:
                print(f"SKIP: {exc}")
                count = 0
            counts[old] = count
            if count:
                print(f"patched {count} x {old} -> {new}")

        missing_critical = [s for s in CRITICAL if counts.get(s, 0) == 0 and s.encode() in exe.read_bytes()]
        if missing_critical:
            raise SystemExit("critical route(s) were not patched: " + ", ".join(missing_critical))

        # Preserve the public patcher's known 4.69.5 IndexFileSig bypass. This
        # lets locally-served DLC be consumed after the endpoint redirect.
        sig_off = 9623264
        if len(blob) <= sig_off + 4:
            raise SystemExit("4.69.5 executable is unexpectedly too small for IndexFileSig patch")
        blob = bytearray(blob)
        blob[sig_off:sig_off + 4] = b"\x01\x00\x00\x14"
        exe.write_bytes(blob)

        info["MayhemServerURL"] = BASE
        info["DLCLocation"] = DLC
        ats = info.get("NSAppTransportSecurity")
        if not isinstance(ats, dict):
            ats = {}
        ats["NSAllowsArbitraryLoads"] = True
        ats["NSAllowsLocalNetworking"] = True
        info["NSAppTransportSecurity"] = ats
        info["NVOfflineServerURL"] = BASE
        info["NVOfflineDLCURL"] = DLC
        plistlib.dump(info, info_path.open("wb"), fmt=plistlib.FMT_BINARY, sort_keys=False)

        repack(root, dst)

    print(f"wrote {dst}")
    print(f"embedded server base: {BASE}")
    print(f"embedded DLC base: {DLC}")


if __name__ == "__main__":
    main()
