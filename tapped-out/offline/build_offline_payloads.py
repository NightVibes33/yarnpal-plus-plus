#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def varint(value: int) -> bytes:
    if value < 0:
        value &= (1 << 64) - 1
    out = bytearray()
    while value >= 0x80:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    out.append(value)
    return bytes(out)


def key(field: int, wire: int) -> bytes:
    return varint((field << 3) | wire)


def field_varint(field: int, value: int) -> bytes:
    return key(field, 0) + varint(value)


def field_bytes(field: int, value: bytes) -> bytes:
    return key(field, 2) + varint(len(value)) + value


def field_string(field: int, value: str) -> bytes:
    return field_bytes(field, value.encode("utf-8"))


def build_client_config(obj: dict) -> bytes:
    # ClientConfigResponse { repeated ClientConfigItem items = 2 }
    out = bytearray()
    for item in obj.get("items", []):
        msg = bytearray()
        if "clientConfigId" in item:
            msg += field_varint(1, int(item["clientConfigId"]))
        msg += field_string(2, str(item.get("name", "")))
        value = str(item.get("value", ""))
        # Keep the client pinned to the final preserved build and prevent
        # external update/telemetry behavior in offline mode.
        name = str(item.get("name", ""))
        if name in {"MinimumVersion.ios", "CurrentVersion.ios"}:
            value = "4.69.5"
        elif name in {"TelemetryEnabled.ios", "CrashReportingIOSOn", "EnableBGDownloadIos"}:
            value = "0"
        msg += field_string(3, value)
        out += field_bytes(2, bytes(msg))
    return bytes(out)


def build_gameplay_config(obj: dict) -> bytes:
    # GameplayConfigResponse { repeated NameValue item = 1 }
    # NameValue { optional string name = 1; optional string value = 2 }
    out = bytearray()
    items = obj.get("item", obj.get("items", []))
    for item in items:
        msg = field_string(1, str(item.get("name", ""))) + field_string(2, str(item.get("value", "")))
        out += field_bytes(1, msg)
    return bytes(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("client_config")
    ap.add_argument("gameplay_config")
    ap.add_argument("output_dir")
    args = ap.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    client = json.loads(Path(args.client_config).read_text(encoding="utf-8"))
    gameplay = json.loads(Path(args.gameplay_config).read_text(encoding="utf-8"))

    client_pb = build_client_config(client)
    gameplay_pb = build_gameplay_config(gameplay)

    (out / "OfflineClientConfig.pb").write_bytes(client_pb)
    (out / "OfflineGameplayConfig.pb").write_bytes(gameplay_pb)
    print(f"OfflineClientConfig.pb: {len(client_pb)} bytes")
    print(f"OfflineGameplayConfig.pb: {len(gameplay_pb)} bytes")


if __name__ == "__main__":
    main()
