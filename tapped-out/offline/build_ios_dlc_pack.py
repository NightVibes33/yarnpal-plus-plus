#!/usr/bin/env python3
"""Build a deterministic TSTO 4.69.5 iPhone DLC closure.

Project Springfield's published master index still references many historical
sub-index ZIPs that are no longer mirrored. The final 4.69 index is reachable
and cumulative for the final client. In --current-only mode we therefore use
only the master entries for v4_69, synthesize a local master that points only
to those reachable current indexes, then verify every selected package itself.
"""
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
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

DEFAULT_SOURCE = "https://cdn.projectspringfield.com/static/"
DEFAULT_LANGUAGES = ("all", "en")
DEFAULT_TIERS = ("all", "100", "retina", "iphone", "caf")
ALL_LANGUAGES = ("all", "en", "fr", "it", "de", "es", "ko", "zh", "cn", "pt", "ru", "tc", "da", "sv", "no", "nl", "tr", "th")
ALL_TIERS = ("all", "25", "50", "100", "retina", "iphone", "ipad", "ipad3", "mp3", "caf", "wav")


def human(n: int) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    value = float(n)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.2f} {unit}"
        value /= 1024
    return str(n)


def normalize_base(url: str) -> str:
    return url if url.endswith("/") else url + "/"


def fetch(url: str, retries: int = 4, timeout: int = 45) -> bytes:
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "TSTO-iOS27-preservation-builder/1.2",
                "Accept": "*/*",
            })
            with urllib.request.urlopen(req, timeout=timeout) as response:
                status = getattr(response, "status", 200)
                if status not in (200, 206):
                    raise RuntimeError(f"HTTP {status}")
                return response.read()
        except Exception as exc:
            last = exc
            if attempt + 1 < retries:
                time.sleep(1.25 * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url}: {last}")


def unzip_first(data: bytes, label: str) -> tuple[str, bytes]:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            files = [item for item in zf.infolist() if not item.is_dir()]
            if not files:
                raise RuntimeError("ZIP contains no files")
            item = files[0]
            return item.filename, zf.read(item)
    except zipfile.BadZipFile as exc:
        raise RuntimeError(f"{label}: invalid ZIP") from exc


def zip_single(name: str, data: bytes) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zf.writestr(name, data)
    return out.getvalue()


def child_value(package: ET.Element, name: str, attr: str) -> str:
    node = package.find(name)
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
    packages: list[Package] = []
    for package in root.iter("Package"):
        tier = (package.get("tier") or "").strip().lower()
        language = child_value(package, "Language", "val").strip().lower()
        if not language:
            language = child_value(package, "Language", "name").strip().lower()
        file_name = child_value(package, "FileName", "val").strip()
        if not file_name:
            continue
        rel = file_name.replace(":", "/")
        try:
            size = int(child_value(package, "FileSize", "val") or 0)
        except ValueError:
            size = 0
        try:
            uncompressed = int(child_value(package, "UncompressedFileSize", "val") or 0)
        except ValueError:
            uncompressed = 0
        packages.append(Package(
            file_name=file_name,
            path=rel,
            tier=tier,
            language=language,
            file_size=size,
            uncompressed_size=uncompressed,
            version=child_value(package, "Version", "val"),
            local_dir=child_value(package, "LocalDir", "name"),
            index_crc=child_value(package, "IndexFileCRC", "val"),
            index_sig=child_value(package, "IndexFileSig", "val"),
            source_index=source_index,
            url=base + rel,
        ))
    return packages


def unique_by_url(packages: Iterable[Package]) -> list[Package]:
    seen: dict[str, Package] = {}
    for package in packages:
        prior = seen.get(package.url)
        if prior is None:
            seen[package.url] = package
        elif prior.file_size and package.file_size and prior.file_size != package.file_size:
            raise RuntimeError(f"conflicting sizes for {package.url}: {prior.file_size} vs {package.file_size}")
    return list(seen.values())


def write_file(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_bytes(data)
    temp.replace(path)


def fetch_index(rel: str, base: str, retries: int) -> tuple[str, bytes, list[Package]]:
    archive = fetch(base + rel, retries=retries)
    _, xml = unzip_first(archive, rel)
    return rel, archive, parse_packages(xml, rel, base)


def filtered_master(master_zip: bytes, keep_paths: set[str]) -> bytes:
    internal_name, master_xml = unzip_first(master_zip, "dlc/DLCIndex.zip")
    root = ET.fromstring(master_xml)
    removed = 0
    kept = 0
    for node in list(root.findall("./IndexFile")):
        raw = node.get("index") or ""
        rel = raw.replace(":", "/")
        if rel in keep_paths:
            kept += 1
        else:
            root.remove(node)
            removed += 1
    if kept == 0:
        raise RuntimeError("filtered master would contain no IndexFile entries")
    xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    print(f"local master filter: kept {kept}, removed {removed} historical index entries")
    return zip_single(internal_name, xml)


def download_one(package: Package, root: Path, retries: int) -> dict:
    destination = root / package.path
    if destination.exists() and (package.file_size <= 0 or destination.stat().st_size == package.file_size):
        return {
            "path": package.path,
            "bytes": destination.stat().st_size,
            "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
            "cached": True,
        }
    data = fetch(package.url, retries=retries, timeout=120)
    if package.file_size and len(data) != package.file_size:
        raise RuntimeError(f"size mismatch: got {len(data)}, expected {package.file_size}")
    write_file(destination, data)
    return {
        "path": package.path,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "cached": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-base", default=os.environ.get("TSTO_DLC_SOURCE_BASE", DEFAULT_SOURCE))
    parser.add_argument("--output-dir", default="build/ios-dlc")
    parser.add_argument("--manifest", default="ios-dlc-manifest.json")
    parser.add_argument("--report", default="ios-dlc-report.txt")
    parser.add_argument("--languages", default=",".join(DEFAULT_LANGUAGES))
    parser.add_argument("--tiers", default=",".join(DEFAULT_TIERS))
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--max-bytes", type=int, default=0)
    parser.add_argument("--current-only", action="store_true",
                        help="Use only current v4_69 index(es) and synthesize a local master without dead historical refs")
    parser.add_argument("--current-index-prefix", default="dlc/DLCIndex-v4_69_")
    args = parser.parse_args()

    base = normalize_base(args.source_base)
    languages = {value.strip().lower() for value in args.languages.split(",") if value.strip()}
    tiers = {value.strip().lower() for value in args.tiers.split(",") if value.strip()}
    output_root = Path(args.output_dir)
    workers = max(1, args.workers)

    print(f"source: {base}")
    print(f"languages: {sorted(languages)}")
    print(f"tiers: {sorted(tiers)}")

    master_rel = "dlc/DLCIndex.zip"
    master_zip = fetch(base + master_rel, retries=args.retries)
    _, master_xml = unzip_first(master_zip, master_rel)
    master_root = ET.fromstring(master_xml)
    all_index_paths = list(dict.fromkeys(
        node.get("index").replace(":", "/")
        for node in master_root.findall("./IndexFile") if node.get("index")
    ))
    if not all_index_paths:
        raise SystemExit("master DLCIndex contains no IndexFile entries")

    if args.current_only:
        index_paths = [path for path in all_index_paths if path.startswith(args.current_index_prefix)]
        if not index_paths:
            raise SystemExit(f"master contains no current index matching {args.current_index_prefix!r}")
        print(f"master index entries: {len(all_index_paths)}")
        print(f"current index candidates: {len(index_paths)}")
        print(f"historical index refs intentionally excluded: {len(all_index_paths) - len(index_paths)}")
    else:
        index_paths = all_index_paths
        print(f"sub-indexes: {len(index_paths)}")

    index_archives: dict[str, bytes] = {}
    all_packages: list[Package] = []
    failures: list[str] = []
    completed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(workers, max(1, len(index_paths)))) as pool:
        futures = {pool.submit(fetch_index, rel, base, args.retries): rel for rel in index_paths}
        for future in concurrent.futures.as_completed(futures):
            rel = futures[future]
            completed += 1
            try:
                got_rel, archive, packages = future.result()
                index_archives[got_rel] = archive
                all_packages.extend(packages)
                print(f"index {completed}/{len(index_paths)}: {got_rel} -> {len(packages)} package entries")
            except Exception as exc:
                failures.append(f"{rel}: {exc}")
                print(f"ERROR: {rel}: {exc}", file=sys.stderr)
    if failures:
        raise SystemExit("required current index closure incomplete:\n" + "\n".join(sorted(failures)))
    if not all_packages:
        raise SystemExit("current index contains no package entries")

    all_unique = unique_by_url(all_packages)
    selected = unique_by_url(
        package for package in all_packages
        if package.language in languages and package.tier in tiers
    )
    if not selected:
        raise SystemExit("tier/language filter selected zero packages")

    by_tier: dict[str, list[Package]] = defaultdict(list)
    by_language: dict[str, list[Package]] = defaultdict(list)
    for package in all_unique:
        by_tier[package.tier].append(package)
        by_language[package.language].append(package)

    def stats(items: list[Package]) -> tuple[int, int]:
        unique = unique_by_url(items)
        return len(unique), sum(max(0, item.file_size) for item in unique)

    selected_bytes = sum(max(0, package.file_size) for package in selected)
    current_bytes = sum(max(0, package.file_size) for package in all_unique)
    report = [
        "TSTO 4.69.5 current iPhone DLC closure report",
        f"source={base}",
        f"master_index_entries={len(all_index_paths)}",
        f"required_current_indexes={len(index_paths)}",
        f"historical_index_refs_excluded={len(all_index_paths) - len(index_paths) if args.current_only else 0}",
        f"current_unique_packages={len(all_unique)}",
        f"current_advertised_bytes={current_bytes} ({human(current_bytes)})",
        f"selected_languages={','.join(sorted(languages))}",
        f"selected_tiers={','.join(sorted(tiers))}",
        f"selected_unique_packages={len(selected)}",
        f"selected_advertised_bytes={selected_bytes} ({human(selected_bytes)})",
        "",
        "By tier in current 4.69 index:",
    ]
    for key in sorted(by_tier):
        count, size = stats(by_tier[key])
        report.append(f"  {key or '<blank>'}: {count} files, {size} bytes ({human(size)})")
    report.extend(["", "By language in current 4.69 index:"])
    for key in sorted(by_language):
        count, size = stats(by_language[key])
        report.append(f"  {key or '<blank>'}: {count} files, {size} bytes ({human(size)})")
    Path(args.report).write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))

    local_master = filtered_master(master_zip, set(index_paths)) if args.current_only else master_zip
    manifest = {
        "schema": 2,
        "target": {"game": "The Simpsons: Tapped Out", "version": "4.69.5", "platform": "ios", "deviceClass": "iphone"},
        "sourceBase": base,
        "languages": sorted(languages),
        "tiers": sorted(tiers),
        "masterIndex": master_rel,
        "originalMasterIndexEntries": len(all_index_paths),
        "localMasterIndexEntries": len(index_paths),
        "historicalIndexRefsExcluded": len(all_index_paths) - len(index_paths) if args.current_only else 0,
        "indexes": index_paths,
        "currentUniquePackages": len(all_unique),
        "currentAdvertisedBytes": current_bytes,
        "selectedUniquePackages": len(selected),
        "selectedAdvertisedBytes": selected_bytes,
        "selectedPackages": [asdict(package) for package in sorted(selected, key=lambda item: item.path)],
    }
    Path(args.manifest).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if not args.download:
        return 0
    if args.max_bytes and selected_bytes > args.max_bytes:
        raise SystemExit(f"selected closure {selected_bytes} exceeds max-bytes {args.max_bytes}")

    # The request path contains a filtered master, so the final client never
    # asks the local server for the 150 dead historical child-index URLs.
    write_file(output_root / master_rel, local_master)
    write_file(output_root / "dlc/DLCIndex.original.zip", master_zip)
    for rel, archive in index_archives.items():
        write_file(output_root / rel, archive)

    results: list[dict] = []
    errors: list[str] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(download_one, package, output_root, args.retries): package for package in selected}
        for number, future in enumerate(concurrent.futures.as_completed(futures), 1):
            package = futures[future]
            try:
                results.append(future.result())
                if number % 50 == 0 or number == len(futures):
                    completed_bytes = sum(item["bytes"] for item in results)
                    print(f"downloaded/verified {number}/{len(futures)} packages, {human(completed_bytes)}")
            except Exception as exc:
                errors.append(f"{package.path}: {exc}")
                print(f"ERROR: {package.path}: {exc}", file=sys.stderr)
    if errors:
        raise SystemExit("selected package closure incomplete:\n" + "\n".join(sorted(errors)))

    result_map = {item["path"]: item for item in results}
    missing = sorted({package.path for package in selected} - result_map.keys())
    if missing:
        raise SystemExit("closure verification missing files:\n" + "\n".join(missing))

    manifest["downloaded"] = True
    manifest["downloadedBytes"] = sum(item["bytes"] for item in results)
    manifest["files"] = [result_map[package.path] for package in sorted(selected, key=lambda item: item.path)]
    Path(args.manifest).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"closure materialized: {len(results)} packages, {human(manifest['downloadedBytes'])}")
    print("filtered local master gate: PASS")
    print("selected package URL/size closure gate: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
