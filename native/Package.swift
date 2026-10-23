// swift-tools-version: 6.0
import PackageDescription
let package = Package(
    name: "SunDogLogic",
    platforms: [.macOS(.v14)],
    products: [.library(name: "SunDogLogic", targets: ["SunDogLogic"])],
    targets: [.target(name: "SunDogLogic", path: "SunDogLogic")]
)
