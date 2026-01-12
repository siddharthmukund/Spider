import XCTest
@testable import SEOCrawlerLib

final class HTMLParserTests: XCTestCase {
    func testParseTitleAndLinksAndWordCount() throws {
        let html = """
            <html>
              <head><title>Test Page</title></head>
              <body>
                <p>Hello world!</p>
                <a href="/foo">Foo</a>
                <a href="https://example.com/bar">Bar</a>
              </body>
            </html>
            """
        let parser = HTMLParser()
        let base = URL(string: "https://example.com")!
        let res = try parser.parse(html: html, baseURL: base)
        XCTAssertEqual(res.title, "Test Page")
        XCTAssertTrue(res.links.contains(URL(string: "https://example.com/foo")!))
        XCTAssertTrue(res.links.contains(URL(string: "https://example.com/bar")!))
        // Body text includes "Hello world!" and link texts (Foo, Bar) => 4 words
        XCTAssertEqual(res.wordCount, 4)
    }
}
