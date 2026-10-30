#!/bin/bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
mkdir -p vixo-simulator/build/VixoQA.app vixo-simulator/output
APP="$PWD/vixo-simulator/build/VixoQA.app"
SDK="$(xcrun --sdk iphonesimulator --show-sdk-path)"
ARCH="$(uname -m)"
xcodebuild -version
xcrun --sdk iphonesimulator swiftc -parse-as-library -sdk "$SDK" -target "$ARCH-apple-ios16.0-simulator" -module-name VixoQA \
  vixo-simulator/Runner.swift -o "$APP/VixoQA"
cat > "$APP/Info.plist" <<'XML'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleIdentifier</key><string>dev.nightvibes33.vixo.qa</string>
<key>CFBundleExecutable</key><string>VixoQA</string>
<key>CFBundleName</key><string>VIXO Simulator QA</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleVersion</key><string>1</string>
<key>CFBundleShortVersionString</key><string>1</string>
<key>MinimumOSVersion</key><string>16.0</string>
<key>NSAppTransportSecurity</key><dict><key>NSAllowsLocalNetworking</key><true/></dict>
<key>UILaunchScreen</key><dict/>
</dict></plist>
XML
codesign --force --sign - "$APP"
xcrun vtool -show-build "$APP/VixoQA"
node vixo-simulator/backend.cjs > vixo-simulator/output/backend.log 2>&1 &
PID=$!
DEVICE=""
cleanup(){ kill "$PID" 2>/dev/null || true; if [[ -n "$DEVICE" ]]; then xcrun simctl shutdown "$DEVICE" 2>/dev/null || true; fi; }
trap cleanup EXIT
for i in {1..20}; do if curl -fs http://127.0.0.1:18777/health >/dev/null; then break; fi; sleep 1; done
curl -fs http://127.0.0.1:18777/health
DEVICE="$(xcrun simctl list devices available -j | python3 -c 'import json,sys; d=json.load(sys.stdin)["devices"]; print(next(x["udid"] for v in d.values() for x in v if x.get("isAvailable") and x["name"].startswith("iPhone")))')"
echo "Selected simulator: $DEVICE"
xcrun simctl boot "$DEVICE"
xcrun simctl bootstatus "$DEVICE" -b
xcrun simctl install "$DEVICE" "$APP"
DATA="$(xcrun simctl get_app_container "$DEVICE" dev.nightvibes33.vixo.qa data)"
for run in 1 2; do
  rm -f "$DATA/Documents/result.json"
  xcrun simctl launch "$DEVICE" dev.nightvibes33.vixo.qa
  found=0
  for j in {1..75}; do if [[ -s "$DATA/Documents/result.json" ]]; then found=1; break; fi; sleep 1; done
  if [[ "$found" -ne 1 ]]; then
    xcrun simctl spawn "$DEVICE" log show --last 2m --style compact --predicate 'process == "VixoQA"' | tail -80 || true
    echo "Failed waiting for simulator app's output"; exit 1
  fi
  cp "$DATA/Documents/result.json" "vixo-simulator/output/launch-$run.json"
  cat "vixo-simulator/output/launch-$run.json"
  xcrun simctl terminate "$DEVICE" dev.nightvibes33.vixo.qa || true
  sleep 2
done
node vixo-simulator/check.cjs vixo-simulator/output/launch-1.json \
     vixo-simulator/output/launch-2.json vixo-simulator/output/ledger.json
