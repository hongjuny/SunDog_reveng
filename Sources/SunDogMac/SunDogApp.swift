import SwiftUI
import AppKit
import CryptoKit
import AppleIIVideo
import SunDogCore
import SunDogLogic

@MainActor final class SplashModel: ObservableObject {
    @Published var splash: SplashScreen?
    @Published var frame: VideoFrame?
    @Published var error: String?
    private var reveal: SplashReveal?
    private var timeline: SplashTimeline?
    private var logoResource: TitleLogoResource?
    private var title: TitleLogo?
    var titleStepCount: Int { title?.appliedStepCount ?? 0 }
    var titleComplete: Bool {
        guard let title else { return false }
        return title.appliedStepCount == title.steps.count
    }
    var appliedWriteCount: Int { reveal?.appliedWriteCount ?? 0 }
    var pageSHA256: String {
        guard let page = title?.page ?? reveal?.page else { return "" }
        return SHA256.hash(data: Data(page)).map { String(format: "%02x", $0) }.joined()
    }
    init() { load() }
    func load() {
        let args = CommandLine.arguments
        let directory: URL
        if let i = args.firstIndex(of: "--assets"), i + 1 < args.count {
            directory = URL(fileURLWithPath: args[i + 1], isDirectory: true)
        } else if let resources = Bundle.main.resourceURL {
            directory = resources
        } else {
            error = "Original splash resources are missing."
            return
        }
        do {
            splash = try SplashScreen.load(pageURL: directory.appendingPathComponent("sundog-splash.hgr"),
                                           manifestURL: directory.appendingPathComponent("sundog-splash.json"))
            timeline = try SplashTimeline.load(url: directory.appendingPathComponent("sundog-splash-timing.json"))
            logoResource = try TitleLogoResource.load(directory: directory)
            reveal = try SplashReveal(source: splash!.page)
            frame = try HGRDecoder.decode(page: reveal!.page)
            error = nil
        } catch {
            splash = nil
            frame = nil
            self.error = error.localizedDescription
        }
    }
    func seek(toCycle cycle: Int) throws {
        title = nil
        guard let timeline, var state = reveal else { return }
        state.reset()
        try state.advance(to: timeline.writeCount(atCycle: cycle))
        reveal = state
        frame = try HGRDecoder.decode(page: state.page)
    }
    func finishTitle() throws {
        guard let splash, let logoResource else { return }
        var state = try TitleLogo(background: splash.page, glyphs: logoResource.bytes)
        try state.advance(to: state.steps.count)
        title = state
        frame = try HGRDecoder.decode(page: state.page)
    }
    func play() async {
        guard let timeline else { return }
        let clock = ContinuousClock()
        do {
            try seek(toCycle: 0)
            let start = clock.now
            while !Task.isCancelled {
                let duration = start.duration(to: clock.now).components
                let elapsed = Double(duration.seconds) + Double(duration.attoseconds) / 1e18
                if var state = reveal {
                    try state.advance(to: timeline.writeCount(at: elapsed))
                    reveal = state
                    frame = try HGRDecoder.decode(page: state.page)
                    if state.appliedWriteCount == state.writes.count { break }
                }
                try await Task.sleep(for: .milliseconds(8))
            }
            guard !Task.isCancelled, let splash, let logoResource else { return }
            var state = try TitleLogo(background: splash.page, glyphs: logoResource.bytes)
            // Original P16 visual steps, with declared host pacing. Native sound
            // duration and original Pascal instruction timing are not yet modeled.
            for count in 1...state.steps.count {
                try Task.checkCancellation()
                try state.advance(to: count)
                title = state
                frame = try HGRDecoder.decode(page: state.page)
                try await Task.sleep(for: .milliseconds(16))
            }
        } catch is CancellationError { }
        catch { self.error = error.localizedDescription }
    }
}

@main @MainActor enum SunDogEntry {
    static func main() {
        if CommandLine.arguments.contains("--diagnose") {
            let model = SplashModel()
            let args = CommandLine.arguments
            let cycle: Int
            if let i = args.firstIndex(of: "--at-cycle"), i + 1 < args.count, let value = Int(args[i + 1]) {
                cycle = value
            } else { cycle = 515593 }
            do { try model.seek(toCycle: cycle) } catch { model.error = error.localizedDescription }
            let backgroundOnly = args.contains("--background-only")
            if !backgroundOnly { do { try model.finishTitle() } catch { model.error = error.localizedDescription } }
            var report: [String: Any] = ["screen": backgroundOnly ? "boot-background" : "original-title", "gameplay_available": false,
                                         "gui_verified": false, "error": model.error ?? "",
                                         "applied_writes": model.appliedWriteCount, "page_sha256": model.pageSHA256,
                                         "title_steps": model.titleStepCount, "title_complete": model.titleComplete]
            if let splash = model.splash {
                let frame = model.frame ?? splash.frame
                let visible = stride(from: 0, to: frame.rgba.count, by: 4).filter {
                    frame.rgba[$0] != 0 || frame.rgba[$0 + 1] != 0 || frame.rgba[$0 + 2] != 0
                }.count
                report.merge(["frame_width": frame.width, "frame_height": frame.height,
                              "reveal_cycle": cycle,
                              "visible_pixels": visible, "asset_sha256": splash.assetSHA256,
                              "rgba_sha256": SHA256.hash(data: Data(frame.rgba)).map { String(format: "%02x", $0) }.joined()]) { _, new in new }
                if let i = args.firstIndex(of: "--export-startup"), i + 1 < args.count {
                    do {
                        let image = NSBitmapImageRep(cgImage: try frame.cgImage())
                        guard let png = image.representation(using: .png, properties: [:]) else {
                            throw SplashScreen.Failure.invalidAsset
                        }
                        try png.write(to: URL(fileURLWithPath: args[i + 1]))
                    } catch { report["error"] = error.localizedDescription }
                }
            }
            if let data = try? JSONSerialization.data(withJSONObject: report, options: [.sortedKeys]) {
                print(String(decoding: data, as: UTF8.self))
            }
            exit(model.splash != nil && (report["error"] as? String) == "" ? 0 : 1)
        }
        SunDogApp.main()
    }
}

@MainActor final class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApplication.shared.setActivationPolicy(.regular)
        NSApplication.shared.activate(ignoringOtherApps: true)
    }
}

@MainActor struct SunDogApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var delegate
    @StateObject private var model = SplashModel()
    var body: some Scene {
        WindowGroup("SunDog: Frozen Legacy") {
            ZStack {
                Color.black
                if let frame = model.frame {
                    NativeScreen(frame: frame)
                        .aspectRatio(4.0 / 3.0, contentMode: .fit)
                        .accessibilityLabel("Original SunDog title screen: spaceship and planet")
                } else {
                    VStack(spacing: 16) {
                        Text("SunDog").font(.title)
                        Text(model.error ?? "Unable to load the original splash screen.")
                            .multilineTextAlignment(.center).textSelection(.enabled)
                        Button("Retry") { model.load() }
                    }.padding().foregroundStyle(.white)
                }
            }.frame(minWidth: 560, minHeight: 420)
            .task { await model.play() }
        }.defaultSize(width: 840, height: 630)
        .commands {
            CommandGroup(replacing: .appInfo) {
                Button("About SunDog") {
                    let alert = NSAlert()
                    alert.messageText = "SunDog: Frozen Legacy — Native Port"
                    alert.informativeText = "The original Apple II title bitmap is displayed by native macOS code. Gameplay and the transition after the title are not implemented yet."
                    alert.runModal()
                }
            }
            CommandGroup(replacing: .newItem) { }
        }
    }
}
