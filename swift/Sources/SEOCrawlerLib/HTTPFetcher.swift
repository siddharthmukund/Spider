import Foundation

public enum FetchError: Error {
    case network(Error)
    case badResponse
    case nonHTTP
}

public final class HTTPFetcher {
    private let session: URLSession

    public init(configuration: URLSessionConfiguration = .ephemeral) {
        self.session = URLSession(configuration: configuration)
    }

    public func fetch(_ url: URL, timeout: TimeInterval = 15.0) async throws -> (Data, Int, TimeInterval) {
        var req = URLRequest(url: url)
        req.timeoutInterval = timeout
        let start = Date()
        do {
            let (data, resp) = try await session.data(for: req)
            let elapsed = Date().timeIntervalSince(start)
            guard let http = resp as? HTTPURLResponse else { throw FetchError.nonHTTP }
            return (data, http.statusCode, elapsed)
        } catch {
            throw FetchError.network(error)
        }
    }
}
