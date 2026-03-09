// swift-tools-version:5.8
import PackageDescription

let package = Package(
    name: "SEOCrawlerApp",
    platforms: [.macOS(.v13)],
    products: [
        .executable(name: "SEOCrawlerApp", targets: ["SEOCrawlerApp"])
    ],
    dependencies: [
        // local library dependency
        .package(path: "../"),
    ],
    targets: [
        .executableTarget(
            name: "SEOCrawlerApp",
            dependencies: [.product(name: "SEOCrawlerLib", package: "swift")],
            path: "Sources/SEOCrawlerApp"
        ),
        .testTarget(
            name: "SEOCrawlerAppTests",
            dependencies: ["SEOCrawlerApp"],
            path: "Tests/SEOCrawlerAppTests"
        ),
        .testTarget(
            name: "SEOCrawlerUITests",
            dependencies: ["SEOCrawlerApp"],
            path: "Tests/SEOCrawlerUITests"
        )
    ]
)
