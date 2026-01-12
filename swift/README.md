# SEOCrawler (Swift rewrite prototype)

This folder contains an initial Swift Package prototype for the SEO crawler core.

Targets:
- `SEOCrawlerLib` - library implementing a simple HTTP fetcher and HTML parser (using SwiftSoup)
- `seocrawler-cli` - a minimal CLI demonstrating fetching a single page and printing PageData JSON

Run tests:
- swift test

Notes:
- This is an initial prototype (fetcher + parser). Next steps: implement concurrency, politeness, URL queue, and reporting.
