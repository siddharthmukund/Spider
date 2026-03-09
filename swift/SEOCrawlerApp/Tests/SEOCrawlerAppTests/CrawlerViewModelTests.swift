import XCTest
@testable import SEOCrawlerApp

final class CrawlerViewModelTests: XCTestCase {
    func testLogTruncation() {
        let vm = CrawlerViewModel()
        for i in 0..<1200 {
            vm.log("line \(i)")
        }
        XCTAssertLessThanOrEqual(vm.logLines.count, 1000)
    }

    func testResponseTimesBuffering() {
        let vm = CrawlerViewModel()
        vm.responseTimes = []
        for i in 0..<250 {
            vm.responseTimes.append(Double(i) * 0.01)
            if vm.responseTimes.count > 200 { vm.responseTimes.removeFirst(vm.responseTimes.count - 200) }
        }
        XCTAssertEqual(vm.responseTimes.count, 200)
    }
}
