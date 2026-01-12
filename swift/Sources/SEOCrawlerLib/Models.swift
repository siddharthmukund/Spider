import Foundation

public struct PageData: Codable, Hashable {
    public let url: URL
    public let statusCode: Int
    public let responseTime: TimeInterval
    public let title: String?
    public let words: Int?
    public let fetchedAt: Date

    public init(url: URL, statusCode: Int, responseTime: TimeInterval, title: String?, words: Int?, fetchedAt: Date = Date()) {
        self.url = url
        self.statusCode = statusCode
        self.responseTime = responseTime
        self.title = title
        self.words = words
        self.fetchedAt = fetchedAt
    }
}
