#!/bin/bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p vixo-device/output vixo-device/build/Payload
APP="$ROOT/vixo-device/build/Payload/VixoQA.app"
mkdir -p "$APP"
SDK="$(xcrun --sdk iphoneos --show-sdk-path)"
echo "Building iPhoneOS app with $(xcodebuild -version | tr '\n' ' ')"
xcrun --sdk iphoneos swiftc \
  -parse-as-library -sdk "$SDK" -target "arm64-apple-ios15.6" \
  -module-name VixoQA -O \
  vixo-device/DeviceQA.swift -o "$APP/VixoQA"
cat > "$APP/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleIdentifier</key><string>dev.nightvibes33.vixo.qa</string>
<key>CFBundleExecutable</key><string>VixoQA</string>
<key>CFBundleDisplayName</key><string>VIXO QA</string>
<key>CFBundleName</key><string>VIXO QA</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleVersion</key><string>1</string>
<key>CFBundleShortVersionString</key><string>1.0</string>
<key>MinimumOSVersion</key><string>15.6</string>
<key>UIDeviceFamily</key><array><integer>1</integer></array>
<key>UILaunchScreen</key><dict/>
</dict></plist>
PLIST
# Ad-hoc signature for artifact integrity only. Re-sign with your own iOS
# certificate + provisioning profile before physical-device installation.
codesign --force --sign - "$APP"
xcrun vtool -show-build "$APP/VixoQA"
python3 - <<'PY'
import pathlib,struct,plistlib
exe=pathlib.Path("vixo-device/build/Payload/VixoQA.app/VixoQA").read_bytes()
magic,cpu,_,typ,n,_,_,_=struct.unpack_from("<8I",exe)
assert magic==0xfeedfacf and cpu==0x0100000c and typ==2,(magic,cpu,typ)
p=32;platform=None
for _ in range(n):
  cmd,size=struct.unpack_from("<II",exe,p)
  if cmd==0x32: platform=struct.unpack_from("<I",exe,p+8)[0]
  assert size>0
  p+=size
assert platform==2,f"Wrong Mach-O platform (expected iPhoneOS=2, got {platform})"
info=plistlib.loads(pathlib.Path("vixo-device/build/Payload/VixoQA.app/Info.plist").read_bytes())
assert info["CFBundleIdentifier"]=="dev.nightvibes33.vixo.qa"
print("PASS: iPhoneOS arm64 Mach-O, correct bundle ID, ad-hoc signed.")
PY
cd "$ROOT/vixo-device/build"
zip -q -r "$ROOT/vixo-device/output/Vixo-QA-iPhoneOS-UNSIGNED.ipa" Payload
unzip -tq "$ROOT/vixo-device/output/Vixo-QA-iPhoneOS-UNSIGNED.ipa"
ls -lh "$ROOT/vixo-device/output/Vixo-QA-iPhoneOS-UNSIGNED.ipa"
