// swift-tools-version: 6.1
import PackageDescription

let package = Package(
    name: "Jikan",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .executable(name: "Jikan", targets: ["Jikan"])
    ],
    targets: [
        .executableTarget(
            name: "Jikan"
        ),
        .testTarget(
            name: "JikanTests",
            dependencies: ["Jikan"]
        ),
    ]
)
