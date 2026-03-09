import SwiftUI
import SEOCrawlerLib

@main
struct SEOCrawlerApp: App {
    @StateObject private var vm = CrawlerViewModel()

    var body: some Scene {
        WindowGroup("SEO Crawler") {
            ContentView().environmentObject(vm)
                .frame(minWidth: 600, minHeight: 400)
        }
    }
}
