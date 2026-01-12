import Foundation
import SEOCrawlerLib

@main
struct CLI {
    static func main() async {
        let args = CommandLine.arguments
        guard args.count > 1, let url = URL(string: args[1]) else {
            print("Usage: seocrawler-cli <url>")
            return
        }

        let fetcher = HTTPFetcher()
        let parser = HTMLParser()

        do {
            let (data, status, elapsed) = try await fetcher.fetch(url)
            let body = String(data: data, encoding: .utf8) ?? ""
            let result = try parser.parse(html: body, baseURL: url)
            let page = PageData(url: url, statusCode: status, responseTime: elapsed, title: result.title, words: result.wordCount)
            let enc = JSONEncoder()
            enc.outputFormatting = .prettyPrinted
            enc.dateEncodingStrategy = .iso8601
            let out = try enc.encode(page)
            print(String(data: out, encoding: .utf8)!)
        } catch {
            print("Error:", error)
        }
    }
}
