import XCTest

final class SEOCrawlerUITests: XCTestCase {
    var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = false
        app = XCUIApplication()
        app.launchEnvironment["UI_TESTING"] = "1"
        app.launch()
    }

    override func tearDownWithError() throws {
        app.terminate()
        app = nil
    }

    func testStartStopShowsStopAndGeneratesMetrics() throws {
        let baseURL = app.textFields["Base URL"]
        XCTAssertTrue(baseURL.waitForExistence(timeout: 2))
        baseURL.click()
        baseURL.typeText("https://example.com")

        let startButton = app.buttons["Start crawler"]
        XCTAssertTrue(startButton.waitForExistence(timeout: 2))
        startButton.click()

        let stopButton = app.buttons["Stop crawler"]
        XCTAssertTrue(stopButton.waitForExistence(timeout: 2))

        // Wait for at least one METRIC log line to appear
        let metricPredicate = NSPredicate(format: "label CONTAINS 'METRIC:'")
        let metricQuery = app.staticTexts.matching(metricPredicate)
        let firstMetric = metricQuery.element(boundBy: 0)
        XCTAssertTrue(firstMetric.waitForExistence(timeout: 6))

        // Verify progress value updates
        let progress = app.progressIndicators["Progress"]
        XCTAssertTrue(progress.waitForExistence(timeout: 2))
        let progressValue = progress.value as? String
        XCTAssertNotEqual(progressValue, "0 percent")

        // Stop and ensure Start reappears
        stopButton.click()
        XCTAssertTrue(startButton.waitForExistence(timeout: 2))
    }

    func testPPSAndCacheLabelsUpdate() throws {
        let startButton = app.buttons["Start crawler"]
        XCTAssertTrue(startButton.waitForExistence(timeout: 2))
        startButton.click()

        let ppsLabel = app.staticTexts["Pages per second"]
        XCTAssertTrue(ppsLabel.waitForExistence(timeout: 2))

        // Wait until PPS displays something other than 0.00
        let initialLabel = ppsLabel.label
        let predicate = NSPredicate(format: "label != %@", initialLabel)
        expectation(for: predicate, evaluatedWith: ppsLabel, handler: nil)
        waitForExpectations(timeout: 6)

        let cacheLabel = app.staticTexts["Cache hits and misses"]
        XCTAssertTrue(cacheLabel.waitForExistence(timeout: 2))

        // stop
        let stopButton = app.buttons["Stop crawler"]
        if stopButton.waitForExistence(timeout: 2) { stopButton.click() }
    }
}
