#!/usr/bin/env python3
"""Build a deterministic iPhone/iOS TSTO DLC closure from the published indexes.

The tool can run in report-only mode (index metadata only) or materialize the
selected packages into a local DLC tree. It preserves the server path layout,
keeps the master/sub-index ZIPs, deduplicates package URLs, verifies advertised
sizes, and writes a JSON manifest that CI can audit.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import io
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

DEFAULT_SOURCE = "https://cdn.projectspringfield.com/static/"
DEFAULT_LANGUAGES = ("all", "en")
# Conservative final-client iPhone closure. 'all' is platform-neutral, '100'
# is full-res, 'retina'/'iphone' are Apple-device tiers, and CAF is the native
# iOS audio tier used by the legacy client asset pipeline.
DEFAULT_TIERS = ("all", "100", "retina", "iphone", "caf")


def human(n: int) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    value = float(n)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{n} B"


def normalize_base(url: str) -> str:
    return url if url.endswith("/") else url + "/"


def fetch(url: str, retries: int = 4, timeout: int = 60) -> bytes:
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "TSTO-iOS27-preservation-builder/1.0",
                    "Accept": "*/*",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as r:
                if getattr(r, "status", 200) not in (200, 206):
                    raise RuntimeError(f"HTTP {r.status} for {url}")
                return r.read()
        except Exception as exc:
            last = exc
            if attempt + 1 == retries:
                break
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url}: {last}")


def unzip_first(data: bytes, label: str) -> bytes:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            files = [i for i in zf.infolist() if not i.is_dir()]
            if not files:
                raise RuntimeError(f"{label}: ZIP contains no file")
            return zf.read(files[0])
    except zipfile.BadZipFile as exc:
        raise RuntimeError(f"{label}: invalid ZIP") from exc


def child_value(pkg: ET.Element, name: str, attr: str) -> str:
    node = pkg.find(name)
    if node is None:
        return ""
    return node.get(attr, "")


@dataclass(frozen=True)
class Package:
    file_name: str
    path: str
    tier: str
    language: str
    file_size: int
    uncompressed_size: int
    version: str
    local_dir: str
    index_crc: str
    index_sig: str
    source_index: str
    url: str


def parse_packages(xml_bytes: bytes, source_index: str, base: str) -> list[Package]:
    root = ET.fromstring(xml_bytes)
    out: list[Package] = []
    for pkg in root.iter("Package"):
        tier = (pkg.get("tier") or "").strip().lower()
        language = child_value(pkg, "Language", "val").strip().lower()
        if not language:
            language = child_value(pkg, "Language", "name").strip().lower()
        file_name = child_value(pkg, "FileName", "val").strip()
        if not file_name:
            continue
        rel = file_name.replace(":", "/")
        try:
            size = int(child_value(pkg, "FileSize", "val") or 0)
        except ValueError:
            size = 0
        try:
            usize = int(child_value(pkg, "UncompressedFileSize", "val") or 0)
        except ValueError:
            usize = 0
        out.append(Package(
            file_name=file_name,
            path=rel,
            tier=tier,
            language=language,
            file_size=size,
            uncompressed_size=usize,
            version=child_value(pkg, "Version", "val"),
            local_dir=child_value(pkg, "LocalDir", "name"),
            index_crc=child_value(pkg, "IndexFileCRC", "val"),
            index_sig=child_value(pkg, "IndexFileSig", "val"),
            source_index=source_index,
            url=base + rel,
        ))
    return out


def unique_by_url(packages: Iterable[Package]) -> list[Package]:
    seen: dict[str, Package] = {}
    for p in packages:
        old = seen.get(p.url)
        if old is None:
            seen[p.url] = p
        elif old.file_size and p.file_size and old.file_size != p.file_size:
            raise RuntimeError(f"conflicting advertised sizes for {p.url}: {old.file_size} vs {p.file_size}")
    return list(seen.values())


def write_file(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


def download_one(p: Package, root: Path, retries: int) -> dict:
    dest = root / p.path
    if dest.exists() and (p.file_size <= 0 or dest.stat().st_size == p.file_size):
        data_size = dest.stat().st_size
        digest = hashlib.sha256(dest.read_bytes()).hexdigest()
        return {"path": p.path, "bytes": data_size, "sha256": digest, "cached": True}
    data = fetch(p.url, retries=retries, timeout=120)
    if p.file_size and len(data) != p.file_size:
        raise RuntimeError(f"size mismatch for {p.path}: got {len(data)}, expected {p.file_size}")
    write_file(dest, data)
    return {
        "path": p.path,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "cached": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-base", default=os.environ.get("TSTO_DLC_SOURCE_BASE", DEFAULT_SOURCE))
    ap.add_argument("--output-dir", default="build/ios-dlc")
    ap.add_argument("--manifest", default="ios-dlc-manifest.json")
    ap.add_argument("--report", default="ios-dlc-report.txt")
    ap.add_argument("--languages", default=",".join(DEFAULT_LANGUAGES))
    ap.add_argument("--tiers", default=",".join(DEFAULT_TIERS))
    ap.add_argument("--download", action="store_true")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--retries", type=int, default=4)
    ap.add_argument("--max-bytes", type=int, default=0,
                    help="Abort materialization when advertised selected bytes exceed this value; 0 disables")
    args = ap.parse_args()

    base = normalize_base(args.source_base)
    langs = {x.strip().lower() for x in args.languages.split(",") if x.strip()}
    tiers = {x.strip().lower() for x in args.tiers.split(",") if x.strip()}
    out_root = Path(args.output_dir)

    print(f"source: {base}")
    print(f"languages: {sorted(langs)}")
    print(f"tiers: {sorted(tiers)}")

    master_rel = "dlc/DLCIndex.zip"
    master_zip = fetch(base + master_rel, retries=args.retries)
    master_xml = unzip_first(master_zip, master_rel)
    master = ET.fromstring(master_xml)
    indexes = []
    for node in master.findall("./IndexFile"):
        raw = node.get("index")
        if raw:
            indexes.append(raw.replace(":", "/"))
    indexes = list(dict.fromkeys(indexes))
    if not indexes:
        raise SystemExit("master DLCIndex contains no IndexFile entries")
    print(f"sub-indexes: {len(indexes)}")

    index_archives: dict[str, bytes] = {master_rel: master_zip}
    all_packages: list[Package] = []
    failures: list[str] = []
    for i, rel in enumerate(indexes, 1):
        try:
            archive = fetch(base + rel, retries=args.retries)
            index_archives[rel] = archive
            xml = unzip_first(archive, rel)
            pkgs = parse_packages(xml, rel, base)
            all_packages.extend(pkgs)
            print(f"index {i}/{len(indexes)}: {rel} -> {len(pkgs)} package entries")
        except Exception as exc:
            failures.append(f"{rel}: {exc}")
            print(f"WARN: {rel}: {exc}", file=sys.stderr)

    if failures:
        raise SystemExit("index closure incomplete:\n" + "\n".join(failures))

    all_unique = unique_by_url(all_packages)
    selected_entries = [p for p in all_packages if p.language in langs and p.tier in tiers]
    selected = unique_by_url(selected_entries)

    by_tier_entries: dict[str, list[Package]] = defaultdict(list)
    by_lang_entries: dict[str, list[Package]] = defaultdict(list)
    for p in all_unique:
        by_tier_entries[p.tier].append(p)
        by_lang_entries[p.language].append(p)

    def stats(items: list[Package]) -> tuple[int, int]:
        u = unique_by_url(items)
        return len(u), sum(max(0, p.file_size) for p in u)

    selected_bytes = sum(max(0, p.file_size) for p in selected)
    all_bytes = sum(max(0, p.file_size) for p in all_unique)

    report_lines = [
        "TSTO 4.69.5 iPhone DLC closure report",
        f"source={base}",
        f"sub_indexes={len(indexes)}",
        f"all_unique_packages={len(all_unique)}",
        f"all_advertised_bytes={all_bytes} ({human(all_bytes)})",
        f"selected_languages={','.join(sorted(langs))}",
        f"selected_tiers={','.join(sorted(tiers))}",
        f"selected_unique_packages={len(selected)}",
        f"selected_advertised_bytes={selected_bytes} ({human(selected_bytes)})",
        "",
        "By tier (deduplicated within tier):",
    ]
    for key in sorted(by_tier_entries):
        n, b = stats(by_tier_entries[key])
        report_lines.append(f"  {key or '<blank>'}: {n} files, {b} bytes ({human(b)})")
    report_lines.append("")
    report_lines.append("By language (deduplicated within language):")
    for key in sorted(by_lang_entries):
        n, b = stats(by_lang_entries[key])
        report_lines.append(f"  {key or '<blank>'}: {n} files, {b} bytes ({human(b)})")

    Path(args.report).write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print("\n".join(report_lines))

    manifest = {
        "schema": 1,
        "target": {"game": "The Simpsons: Tapped Out", "version": "4.69.5", "platform": "ios", "deviceClass": "iphone"},
        "sourceBase": base,
        "languages": sorted(langs),
        "tiers": sorted(tiers),
        "masterIndex": master_rel,
        "indexes": indexes,
        "allUniquePackages": len(all_unique),
        "allAdvertisedBytes": all_bytes,
        "selectedUniquePackages": len(selected),
        "selectedAdvertisedBytes": selected_bytes,
        "selectedPackages": [asdict(p) for p in sorted(selected, key=lambda x: x.path)],
    }
    Path(args.manifest).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if not args.download:
        return 0
    if args.max_bytes and selected_bytes > args.max_bytes:
        raise SystemExit(f"selected closure {selected_bytes} exceeds max-bytes {args.max_bytes}")

    # Preserve the exact index layout the client asks for.
    for rel, archive in index_archives.items():
        write_file(out_root / rel, archive)

    results: list[dict] = []
    errors: list[str] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(download_one, p, out_root, args.retries): p for p in selected}
        for i, fut in enumerate(concurrent.futures.as_completed(futures), 1):
            p = futures[fut]
            try:
                result = fut.result()
                results.append(result)
                if i % 50 == 0 or i == len(futures):
                    done = sum(r["bytes"] for r in results)
                    print(f"downloaded/verified {i}/{len(futures)} packages, {human(done)}")
            except Exception as exc:
                errors.append(f"{p.path}: {exc}")
                print(f"ERROR: {p.path}: {exc}", file=sys.stderr)
    if errors:
        raise SystemExit("DLC materialization incomplete:\n" + "\n".join(errors))

    actual_paths = {r["path"] for r in results}
    missing = sorted({p.path for p in selected} - actual_paths)
    if missing:
        raise SystemExit("closure verification missing files:\n" + "\n".join(missing))

    result_map = {r["path"]: r for r in results}
    manifest["downloaded"] = True
    manifest["downloadedBytes"] = sum(r["bytes"] for r in results)
    manifest["files"] = [result_map[p.path] for p in sorted(selected, key=lambda x: x.path)]
    Path(args.manifest).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"closure materialized: {len(results)} packages, {human(manifest['downloadedBytes'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
