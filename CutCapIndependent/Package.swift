// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "CutCapIndependentCore",
    platforms: [.iOS(.v17)],
    products: [
        .library(name: "CutCapIndependentCore", targets: ["CutCapIndependentCore"])
    ],
    targets: [
        .target(
            name: "CutCapIndependentCore",
            path: "Sources/CutCapIndependentCore"
        )
    ]
)
