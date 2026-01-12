import Foundation
import SwiftSoup

public struct ParseResult {
    public let title: String?
    public let links: [URL]
    public let wordCount: Int

    public init(title: String?, links: [URL], wordCount: Int) {
        self.title = title
        self.links = links
        self.wordCount = wordCount
    }
}

public final class HTMLParser {
    public init() {}

    public func parse(html: String, baseURL: URL) throws -> ParseResult {
        let doc = try SwiftSoup.parse(html, baseURL.absoluteString)
        let title = try doc.title()
        let linkElements = try doc.select("a[href]")
        var links = [URL]()
        for el in linkElements.array() {
            let href = try el.attr("href")
            if let resolved = URL(string: href, relativeTo: baseURL)?.absoluteURL {
                links.append(resolved)
            }
        }
        let bodyText = try doc.body()?.text() ?? ""
        let words = bodyText.split{ $0 == " " || $0 == "\n" || $0 == "\t" || $0 == "\r" }.count
        return ParseResult(title: title.isEmpty ? nil : title, links: links, wordCount: words)
    }
}
