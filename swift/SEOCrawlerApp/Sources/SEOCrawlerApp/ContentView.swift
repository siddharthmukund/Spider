import SwiftUI
import Charts

struct ContentView: View {
    @EnvironmentObject var vm: CrawlerViewModel
    @Environment(\.colorScheme) var colorScheme

    var body: some View {
        VStack(alignment: .leading) {
            HStack {
                TextField("Base URL", text: $vm.baseURL)
                    .textFieldStyle(.roundedBorder)
                    .accessibilityLabel("Base URL")
                    .frame(minWidth: 300)

                Stepper(value: $vm.maxPages, in: 1...10000) {
                    Text("Max pages: \(vm.maxPages)")
                }
                .accessibilityLabel("Max pages")

                Button(action: { vm.isRunning ? vm.stop() : vm.start() }) {
                    Text(vm.isRunning ? "Stop" : "Start")
                }
                .keyboardShortcut("r", modifiers: [.command])
                .accessibilityLabel(vm.isRunning ? "Stop crawler" : "Start crawler")
                .padding(.leading)
            }
            .padding()

            HStack(alignment: .center) {
                ProgressView(value: vm.progressFraction)
                    .progressViewStyle(LinearProgressViewStyle())
                    .frame(height: 8)
                    .accessibilityLabel("Progress")
                    .accessibilityValue("\(Int(vm.progressFraction * 100)) percent")

                Spacer()

                VStack(alignment: .trailing) {
                    Text("PPS: \(String(format: "%.2f", vm.pps))")
                        .accessibilityLabel("Pages per second")
                    Text("Cache: \(vm.cacheHits)h/\(vm.cacheMisses)m")
                        .accessibilityLabel("Cache hits and misses")
                }
                .padding(.leading)
            }
            .padding([.leading, .trailing])

            HStack {
                // Sparkline using Charts
                if #available(macOS 13, *) {
                    Chart(vm.responseTimes.suffix(50).enumerated().map { x, y in
                        (index: x, value: y)
                    }, id: \.index) { item in
                        LineMark(
                            x: .value("Index", item.index),
                            y: .value("Response", item.value)
                        )
                        .interpolationMethod(.catmullRom)
                        .foregroundStyle(Color.accentColor)
                    }
                    .frame(height: 80)
                    .accessibilityHidden(false)
                    .accessibilityLabel("Response time sparkline")
                }

                Spacer()

                // quick stats
                VStack(alignment: .trailing) {
                    Text("Avg: \(String(format: "%.2f", vm.avgResponse))s")
                    Text("Fastest: \(String(format: "%.2f", vm.fastest))s")
                }
                .padding([.leading, .trailing])
            }
            .padding()

            Divider()

            // Per-page table
            VStack(alignment: .leading) {
                Text("Recent Pages")
                    .font(.headline)
                    .padding([.leading, .top])
                Table(vm.pages) {
                    TableColumn("URL") { item in
                        Text(item.url).lineLimit(1)
                    }
                    TableColumn("Response (s)") { item in
                        Text(String(format: "%.2f", item.responseTime))
                            .frame(minWidth: 80, alignment: .trailing)
                    }
                    TableColumn("Status") { item in
                        Text(String(item.status))
                    }
                }
                .frame(minHeight: 200)
                .accessibilityElement(children: .contain)
            }

            Divider()

            // Logs
            VStack(alignment: .leading) {
                Text("Logs")
                    .font(.subheadline)
                    .padding([.leading, .top])
                ScrollView {
                    LazyVStack(alignment: .leading) {
                        ForEach(vm.logLines, id: \.self) { line in
                            Text(line)
                                .font(.system(size: 12, design: .monospaced))
                                .foregroundColor(colorScheme == .dark ? .white : .black)
                        }
                    }
                    .padding()
                }
                .frame(minHeight: 180)
            }
        }
        .padding()
        .background(Color(NSColor.windowBackgroundColor))
        .onAppear {
            // example keyboard shortcut for stop
            // Cmd+T to stop
            #if os(macOS)
            // Additional mac-specific configuration if needed
            #endif
        }
    }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView().environmentObject(CrawlerViewModel())
    }
}
