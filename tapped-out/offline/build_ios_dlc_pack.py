#!/usr/bin/env python3
"""Build and verify the 4.69.5 iPhone DLC closure from published TSTO indexes."""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import io
import json
import os
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

DEFAULT_SOURCE = "https://cdn.projectspringfield.com/static/"
DEFAULT_LANGUAGES = ("all", "en")
DEFAULT_TIERS = ("all", "100", "retina", "iphone", "caf")


def human(n: int) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    v = float(n)
    for unit in units:
        if v < 1024 or unit == units[-1]:
            return f"{v:.2f} {unit}"
        v /= 1024
    return str(n)


def normalize_base(url: str) -> str:
    return url if url.endswith("/") else url + "/"


def fetch(url: str, retries: int = 4, timeout: int = 45) -> bytes:
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "TSTO-iOS27-preservation-builder/1.1",
                "Accept": "*/*",
            })
            with urllib.request.urlopen(req, timeout=timeout) as r:
                status = getattr(r, "status", 200)
                if status not in (200, 206):
                    raise RuntimeError(f"HTTP {status}")
                return r.read()
        except Exception as exc:
            last = exc
            if attempt + 1 < retries:
                time.sleep(1.25 * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url}: {last}")


def unzip_first(data: bytes, label: str) -> bytes:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            files = [i for i in zf.infolist() if not i.is_dir()]
            if not files:
                raise RuntimeError("ZIP contains no files")
            return zf.read(files[0])
    except zipfile.BadZipFile as exc:
        raise RuntimeError(f"{label}: invalid ZIP") from exc


def child_value(pkg: ET.Element, name: str, attr: str) -> str:
    node = pkg.find(name)
    return "" if node is None else node.get(attr, "")


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
    out = []
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
            raise RuntimeError(f"conflicting sizes for {p.url}: {old.file_size} vs {p.file_size}")
    return list(seen.values())


def write_file(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


def fetch_index(rel: str, base: str, retries: int) -> tuple[str, bytes, list[Package]]:
    archive = fetch(base + rel, retries=retries)
    xml = unzip_first(archive, rel)
    return rel, archive, parse_packages(xml, rel, base)


def download_one(p: Package, root: Path, retries: int) -> dict:
    dest = root / p.path
    if dest.exists() and (p.file_size <= 0 or dest.stat().st_size == p.file_size):
        return {
            "path": p.path,
            "bytes": dest.stat().st_size,
            "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
            "cached": True,
        }
    data = fetch(p.url, retries=retries, timeout=120)
    if p.file_size and len(data) != p.file_size:
        raise RuntimeError(f"size mismatch: got {len(data)}, expected {p.file_size}")
    write_file(dest, data)
    return {"path": p.path, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "cached": False}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-base", default=os.environ.get("TSTO_DLC_SOURCE_BASE", DEFAULT_SOURCE))
    ap.add_argument("--output-dir", default="build/ios-dlc")
    ap.add_argument("--manifest", default="ios-dlc-manifest.json")
    ap.add_argument("--report", default="ios-dlc-report.txt")
    ap.add_argument("--languages", default=",".join(DEFAULT_LANGUAGES))
    ap.add_argument("--tiers", default=",".join(DEFAULT_TIERS))
    ap.add_argument("--download", action="store_true")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--retries", type=int, default=4)
    ap.add_argument("--max-bytes", type=int, default=0)
    args = ap.parse_args()

    base = normalize_base(args.source_base)
    langs = {x.strip().lower() for x in args.languages.split(",") if x.strip()}
    tiers = {x.strip().lower() for x in args.tiers.split(",") if x.strip()}
    out_root = Path(args.output_dir)
    workers = max(1, args.workers)

    print(f"source: {base}")
    print(f"languages: {sorted(langs)}")
    print(f"tiers: {sorted(tiers)}")

    master_rel = "dlc/DLCIndex.zip"
    master_zip = fetch(base + master_rel, retries=args.retries)
    master = ET.fromstring(unzip_first(master_zip, master_rel))
    indexes = list(dict.fromkeys(
        node.get("index").replace(":", "/")
        for node in master.findall("./IndexFile") if node.get("index")
    ))
    if not indexes:
        raise SystemExit("master DLCIndex contains no IndexFile entries")
    print(f"sub-indexes: {len(indexes)}")

    index_archives: dict[str, bytes] = {master_rel: master_zip}
    all_packages: list[Package] = []
    failures: list[str] = []
    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        future_map = {pool.submit(fetch_index, rel, base, args.retries): rel for rel in indexes}
        for fut in concurrent.futures.as_completed(future_map):
            rel = future_map[fut]
            done += 1
            try:
                got_rel, archive, pkgs = fut.result()
                index_archives[got_rel] = archive
                all_packages.extend(pkgs)
                print(f"index {done}/{len(indexes)}: {got_rel} -> {len(pkgs)} package entries")
            except Exception as exc:
                failures.append(f"{rel}: {exc}")
                print(f"WARN: {rel}: {exc}", file=sys.stderr)
    if failures:
        raise SystemExit("index closure incomplete:\n" + "\n".join(sorted(failures)))

    all_unique = unique_by_url(all_packages)
    selected = unique_by_url(p for p in all_packages if p.language in langs and p.tier in tiers)

    by_tier: dict[str, list[Package]] = defaultdict(list)
    by_lang: dict[str, list[Package]] = defaultdict(list)
    for p in all_unique:
        by_tier[p.tier].append(p)
        by_lang[p.language].append(p)

    def stats(items: list[Package]) -> tuple[int, int]:
        u = unique_by_url(items)
        return len(u), sum(max(0, p.file_size) for p in u)

    selected_bytes = sum(max(0, p.file_size) for p in selected)
    all_bytes = sum(max(0, p.file_size) for p in all_unique)
    report = [
        "TSTO 4.69.5 iPhone DLC closure report",
        f"source={base}",
        f"sub_indexes={len(indexes)}",
        f"all_unique_packages={len(all_unique)}",
        f"all_advertised_bytes={all_bytes} ({human(all_bytes)})",
        f"selected_languages={','.join(sorted(langs))}",
        f"selected_tiers={','.join(sorted(tiers))}",
        f"selected_unique_packages={len(selected)}",
        f"selected_advertised_bytes={selected_bytes} ({human(selected_bytes)})",
        "", "By tier (deduplicated within tier):",
    ]
    for key in sorted(by_tier):
        n, b = stats(by_tier[key])
        report.append(f"  {key or '<blank>'}: {n} files, {b} bytes ({human(b)})")
    report += ["", "By language (deduplicated within language):"]
    for key in sorted(by_lang):
        n, b = stats(by_lang[key])
        report.append(f"  {key or '<blank>'}: {n} files, {b} bytes ({human(b)})")
    Path(args.report).write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))

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

    for rel, archive in index_archives.items():
        write_file(out_root / rel, archive)

    results, errors = [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        future_map = {pool.submit(download_one, p, out_root, args.retries): p for p in selected}
        for i, fut in enumerate(concurrent.futures.as_completed(future_map), 1):
            p = future_map[fut]
            try:
                results.append(fut.result())
                if i % 50 == 0 or i == len(future_map):
                    print(f"downloaded/verified {i}/{len(future_map)} packages, {human(sum(r['bytes'] for r in results))}")
            except Exception as exc:
                errors.append(f"{p.path}: {exc}")
                print(f"ERROR: {p.path}: {exc}", file=sys.stderr)
    if errors:
        raise SystemExit("DLC materialization incomplete:\n" + "\n".join(sorted(errors)))

    result_map = {r["path"]: r for r in results}
    missing = sorted({p.path for p in selected} - result_map.keys())
    if missing:
        raise SystemExit("closure verification missing files:\n" + "\n".join(missing))
    manifest["downloaded"] = True
    manifest["downloadedBytes"] = sum(r["bytes"] for r in results)
    manifest["files"] = [result_map[p.path] for p in sorted(selected, key=lambda x: x.path)]
    Path(args.manifest).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"closure materialized: {len(results)} packages, {human(manifest['downloadedBytes'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
