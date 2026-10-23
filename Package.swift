// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "SunDogPort",
    platforms: [.macOS(.v14)],
    products: [
        .library(name: "AppleIIVideo", targets: ["AppleIIVideo"]),
        .library(name: "SunDogCore", targets: ["SunDogCore"]),
        .executable(name: "SunDogInspect", targets: ["SunDogInspect"]),
        .executable(name: "SunDogMac", targets: ["SunDogMac"])
    ],
    targets: [
        .target(name: "AppleIIVideo"),
        .target(name: "SunDogCore", dependencies: ["AppleIIVideo"]),
        .executableTarget(name: "SunDogInspect", dependencies: ["SunDogCore", "AppleIIVideo"]),
        .executableTarget(name: "SunDogMac", dependencies: ["SunDogCore", "AppleIIVideo"]),
        .testTarget(name: "VideoTests", dependencies: ["AppleIIVideo", "SunDogCore"], path: "tests/VideoTests")
    ]
)
