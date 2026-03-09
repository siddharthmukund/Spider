import Foundation
import Combine
import SEOCrawlerLib

@MainActor
class PageRow: Identifiable {
    let id = UUID()
    let url: String
    let responseTime: Double
    let status: Int
    init(url: String, responseTime: Double, status: Int) {
        self.url = url
        self.responseTime = responseTime
        self.status = status
    }
}

@MainActor
class CrawlerViewModel: ObservableObject {
    @Published var baseURL: String = "https://example.com"
    @Published var maxPages: Int = 100
    @Published var isRunning: Bool = false
    @Published var pps: Double = 0.0
    @Published var cacheHits: Int = 0
    @Published var cacheMisses: Int = 0
    @Published var logLines: [String] = []

    @Published var responseTimes: [Double] = []
    @Published var pages: [PageRow] = []
    @Published var progressFraction: Double = 0.0
    @Published var avgResponse: Double = 0.0
    @Published var fastest: Double = 0.0

    // Adapter protocol to hide concrete implementations (real/fake) behind a single interface
    private protocol CrawlerAdapter: AnyObject {
        var onMetric: ((String, Double, Int) -> Void)? { get set }
        var onCacheStats: ((Int, Int) -> Void)? { get set }
        var onProgress: ((Int, Int) -> Void)? { get set }
        func start()
        func stop()
    }

    // Minimal real adapter that performs a single-page fetch using HTTPFetcher
    private final class RealCrawlerAdapter: CrawlerAdapter {
        var onMetric: ((String, Double, Int) -> Void)?
        var onCacheStats: ((Int, Int) -> Void)?
        var onProgress: ((Int, Int) -> Void)?

        private let baseURL: String
        private let maxPages: Int
        private var task: Task<Void, Never>?

        init(baseURL: String, maxPages: Int) {
            self.baseURL = baseURL
            self.maxPages = maxPages
        }

        func start() {
            task = Task {
                guard let url = URL(string: baseURL) else {
                    onProgress?(0, 0)
                    return
                }
                do {
                    let fetcher = HTTPFetcher()
                    let (data, status, elapsed) = try await fetcher.fetch(url)
                    onMetric?(baseURL, elapsed, status)
                    onCacheStats?(0, 0)
                    onProgress?(1, 1)
                } catch {
                    onProgress?(1, 1)
                }
            }
        }

        func stop() {
            task?.cancel()
            task = nil
        }
    }

    // Fake crawler for UI tests which emits synthetic metrics
    private final class FakeCrawlerAdapter: CrawlerAdapter {
        var onMetric: ((String, Double, Int) -> Void)?
        var onCacheStats: ((Int, Int) -> Void)?
        var onProgress: ((Int, Int) -> Void)?

        private var timer: Timer?
        private var total = 20
        private var completed = 0
        private var hits = 0
        private var misses = 0

        func start() {
            completed = 0
            hits = 0
            misses = 0
            onProgress?(completed, total)
            timer = Timer.scheduledTimer(withTimeInterval: 0.2, repeats: true) { [weak self] t in
                guard let self else { return }
                self.completed += 1
                let rt = Double.random(in: 0.05...0.5)
                let status = (self.completed % 10 == 0) ? 500 : 200
                if status == 200 { self.hits += 1 } else { self.misses += 1 }
                self.onMetric?("https://example.com/page/\(self.completed)", rt, status)
                self.onCacheStats?(self.hits, self.misses)
                self.onProgress?(self.completed, self.total)
                if self.completed >= self.total {
                    t.invalidate()
                    self.timer = nil
                }
            }
            // ensure it runs on runloop common modes
            RunLoop.current.add(timer!, forMode: .common)
        }

        func stop() {
            timer?.invalidate()
            timer = nil
        }
    }

    private var crawler: CrawlerAdapter?
    private var cancellables: Set<AnyCancellable> = []
    private var sampleCount: Int = 0

    func start() {
        guard !isRunning else { return }
        isRunning = true
        log("Starting crawler for \(baseURL)")
        // reset some state
        responseTimes.removeAll()
        pages.removeAll()
        progressFraction = 0
        sampleCount = 0
        avgResponse = 0
        fastest = Double.greatestFiniteMagnitude

        // If running under UI tests, use the FakeCrawlerAdapter
        if ProcessInfo.processInfo.environment["UI_TESTING"] == "1" {
            crawler = FakeCrawlerAdapter()
        } else {
            crawler = RealCrawlerAdapter(baseURL: baseURL, maxPages: maxPages)
        }

        crawler?.onMetric = { [weak self] url, rt, status in
            Task { @MainActor in
                guard let self else { return }
                self.log("METRIC: \(url) \(String(format: "%.2f", rt))s status=\(status)")
                self.responseTimes.append(rt)
                if self.responseTimes.count > 200 { self.responseTimes.removeFirst(self.responseTimes.count - 200) }
                self.pages.insert(PageRow(url: url, responseTime: rt, status: status), at: 0)
                if self.pages.count > 200 { self.pages.removeLast() }
                self.sampleCount += 1
                self.avgResponse = ((self.avgResponse * Double(max(0, self.sampleCount - 1))) + rt) / Double(self.sampleCount)
                self.fastest = min(self.fastest, rt)
                self.pps = Double(self.sampleCount) / max(1.0, Double(self.sampleCount) * 0.01)
            }
        }
        crawler?.onCacheStats = { [weak self] hits, misses in
            Task { @MainActor in
                self?.cacheHits = hits
                self?.cacheMisses = misses
            }
        }
        crawler?.onProgress = { [weak self] completed, total in
            Task { @MainActor in
                guard let self else { return }
                self.progressFraction = total > 0 ? Double(completed) / Double(total) : 0
            }
        }
        crawler?.start()
    }

    func stop() {
        crawler?.stop()
        isRunning = false
        log("Stop requested")
    }

    func log(_ text: String) {
        logLines.append(text)
        if logLines.count > 1000 { logLines.removeFirst(logLines.count - 1000) }
    }
}
