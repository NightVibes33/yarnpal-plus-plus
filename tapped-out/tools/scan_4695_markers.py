#!/usr/bin/env python3
import argparse
import json
import plistlib
import re
import zipfile
from pathlib import PurePosixPath

TARGET_VERSION = "4.69.5"

MARKERS = {
    "cached_user": [
        b"CachedUserData",
        b"cachedUser",
        b"/cachedUser",
    ],
    "anonymous_login": [
        b"anonymous",
        b"AnonymousUserData",
        b"isAnonymous",
    ],
    "premium_currency": [
        b"premiumCurrency",
        b"premium",
        b"realPremium",
        b"donuts",
        b"Donuts",
    ],
    "currency_handlers": [
        b"CurrencyData",
        b"CurrencySaveData",
        b"CurrencyResponseMessage",
        b"updatedCurrency",
        b"currencyAwarded",
        b"spend",
        b"award",
        b"collect",
    ],
}


def printable_context(blob: bytes, start: int, end: int, radius: int = 80) -> str:
    lo = max(0, start - radius)
    hi = min(len(blob), end + radius)
    chunk = blob[lo:hi]
    text = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
    return text


def main():
    ap = argparse.ArgumentParser(description="Scan a Tapped Out 4.69.5 IPA for offline/profile/currency markers")
    ap.add_argument("ipa")
    ap.add_argument("--json", dest="json_out", help="write machine-readable results")
    args = ap.parse_args()

    findings = {
        "targetVersion": TARGET_VERSION,
        "reportedVersion": None,
        "bundleId": None,
        "matches": [],
    }

    with zipfile.ZipFile(args.ipa, "r") as zf:
        info_names = [
            n for n in zf.namelist()
            if n.startswith("Payload/") and n.count("/") == 2 and n.endswith(".app/Info.plist")
        ]
        if not info_names:
            raise SystemExit("No Payload/*.app/Info.plist found")

        info = plistlib.loads(zf.read(info_names[0]))
        findings["reportedVersion"] = str(
            info.get("CFBundleShortVersionString") or info.get("CFBundleVersion") or ""
        )
        findings["bundleId"] = info.get("CFBundleIdentifier")

        if findings["reportedVersion"] != TARGET_VERSION:
            print(f"WARNING: expected {TARGET_VERSION}; IPA reports {findings['reportedVersion'] or 'unknown'}")

        for name in zf.namelist():
            if name.endswith("/"):
                continue
            try:
                blob = zf.read(name)
            except Exception:
                continue
            if not blob:
                continue

            for category, needles in MARKERS.items():
                for needle in needles:
                    start = 0
                    while True:
                        idx = blob.find(needle, start)
                        if idx < 0:
                            break
                        findings["matches"].append({
                            "category": category,
                            "marker": needle.decode("ascii", errors="replace"),
                            "file": name,
                            "offset": idx,
                            "context": printable_context(blob, idx, idx + len(needle)),
                        })
                        start = idx + len(needle)

    grouped = {}
    for row in findings["matches"]:
        grouped.setdefault(row["category"], []).append(row)

    print(f"Bundle ID: {findings['bundleId']}")
    print(f"Version: {findings['reportedVersion']}")
    for category in MARKERS:
        rows = grouped.get(category, [])
        print(f"{category}: {len(rows)} hit(s)")
        for row in rows[:20]:
            print(f"  {row['marker']} -> {row['file']} @ 0x{row['offset']:x}")
        if len(rows) > 20:
            print(f"  ... {len(rows) - 20} more")

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(findings, f, indent=2)
        print(f"Wrote: {args.json_out}")


if __name__ == "__main__":
    main()
