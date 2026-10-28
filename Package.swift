// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "SunDogPort",
    platforms: [.macOS(.v14)],
    products: [
        .library(name: "AppleIIVideo", targets: ["AppleIIVideo"]),
        .library(name: "SunDogCore", targets: ["SunDogCore"]),
        .library(name: "SunDogLogic", targets: ["SunDogLogic"]),
        .executable(name: "SunDogReference", targets: ["SunDogReference"]),
        .executable(name: "SunDogRender", targets: ["SunDogRender"]),
        .executable(name: "SunDogInspect", targets: ["SunDogInspect"]),
        .executable(name: "SunDogMac", targets: ["SunDogMac"])
    ],
    targets: [
        .target(name: "AppleIIVideo"),
        .target(name: "SunDogLogic", path: "native/SunDogLogic"),
        .target(name: "SunDogCore", dependencies: ["AppleIIVideo", "SunDogLogic"]),
        .executableTarget(name: "SunDogReference", dependencies: ["SunDogCore", "AppleIIVideo"]),
        .executableTarget(name: "SunDogRender", dependencies: ["SunDogCore", "AppleIIVideo"]),
        .executableTarget(name: "SunDogInspect", dependencies: ["SunDogCore", "AppleIIVideo"]),
        .executableTarget(name: "SunDogMac", dependencies: ["SunDogCore", "AppleIIVideo", "SunDogLogic"]),
        .testTarget(name: "VideoTests", dependencies: ["AppleIIVideo", "SunDogCore", "SunDogLogic"], path: "tests/VideoTests")
    ]
)
