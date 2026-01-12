// swift-tools-version:5.7
import PackageDescription

let package = Package(
    name: "SEOCrawler",
    platforms: [.macOS(.v13)],
    products: [
        .library(name: "SEOCrawlerLib", targets: ["SEOCrawlerLib"]),
        .executable(name: "seocrawler-cli", targets: ["seocrawler-cli"]),
    ],
    dependencies: [
        .package(url: "https://github.com/scinfu/SwiftSoup.git", from: "2.5.3"),
        .package(url: "https://github.com/apple/swift-log.git", from: "1.4.0"),
    ],
    targets: [
        .target(
            name: "SEOCrawlerLib",
            dependencies: [
                .product(name: "SwiftSoup", package: "SwiftSoup"),
                .product(name: "Logging", package: "swift-log"),
            ],
            path: "Sources/SEOCrawlerLib"
        ),
        .executableTarget(
            name: "seocrawler-cli",
            dependencies: ["SEOCrawlerLib"],
            path: "Sources/seocrawler-cli"
        ),
        .testTarget(
            name: "SEOCrawlerLibTests",
            dependencies: ["SEOCrawlerLib"],
            path: "Tests/SEOCrawlerLibTests"
        )
    ]
)
