import SwiftUI
import AppKit
import CryptoKit
import AppleIIVideo
import SunDogCore
import SunDogLogic

@MainActor final class SplashModel: ObservableObject {
    enum Screen: String { case title, awaitingBegin, choices, playDisk, ship }
    @Published private(set) var screen: Screen = .title
    @Published var notice: String?
    @Published var splash: SplashScreen?
    @Published var frame: VideoFrame?
    @Published var error: String?
    private var reveal: SplashReveal?
    private var timeline: SplashTimeline?
    private var logoResource: TitleLogoResource?
    private var title: TitleLogo?
    private var startupResources: StartupResources?
    private var startup: StartupFlow?
    private var shipInteraction: ShipInteraction?
    private var shipTicker: Task<Void,Never>?
    private var presentedPage: [UInt8]?
    private var samples: [UInt8] = [0,0]
    private var diskButtons = ButtonInput()
    private(set) var history = ["title"]
    var playerName: String { startupResources?.name ?? "" }
    var originalGameState: UInt16 { startupResources?.profile.state ?? 0 }
    var titleStepCount: Int { title?.appliedStepCount ?? 0 }
    var titleComplete: Bool {
        guard let title else { return false }
        return title.appliedStepCount == title.steps.count
    }
    var appliedWriteCount: Int { reveal?.appliedWriteCount ?? 0 }
    var pageSHA256: String {
        guard let page = presentedPage ?? title?.page ?? reveal?.page else { return "" }
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
            startupResources = try StartupResources.load(directory: directory)
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
        presentedPage = nil
        title = nil
        guard let timeline, var state = reveal else { return }
        state.reset()
        try state.advance(to: timeline.writeCount(atCycle: cycle))
        reveal = state
        frame = try HGRDecoder.decode(page: state.page)
    }
    func finishTitle() throws {
        presentedPage = nil
        guard let splash, let logoResource else { return }
        var state = try TitleLogo(background: splash.page, glyphs: logoResource.bytes)
        try state.advance(to: state.steps.count)
        title = state
        frame = try HGRDecoder.decode(page: state.page)
    }
    private func setScreen(_ value: Screen) {
        screen = value
        if history.last != value.rawValue { history.append(value.rawValue) }
    }
    private func present(_ page: [UInt8]) throws {
        presentedPage = page
        frame = try HGRDecoder.decode(page: page)
    }
    func beginStartup() throws {
        guard let resources = startupResources, let title else { return }
        startup = StartupFlow(mode: resources.mode, profile: resources.profile)
        if startup?.stage == .awaitingBegin {
            try present(StartupTextScreen.compose(background: title.page, font: resources.font,
                messages: resources.gateMessages))
            setScreen(.awaitingBegin)
        } else { notice = "The original warm-start route is not connected to a scene yet." }
    }
    private func showChoices() throws {
        guard let resources = startupResources, let title, let startup else { return }
        let labels=resources.labels.filter { label in startup.choices.contains(where: {$0.rawValue==label.id}) }
        try present(StartupTextScreen.composeChoices(background:title.page,font:resources.font,
            messages:resources.greetingMessages(),labels:labels.map(\.bytes)))
        setScreen(.choices)
    }
    func selectChoice(_ choice: StartupFlow.Choice) throws {
        guard screen == .choices, var state=startup, let resources=startupResources, let title else { return }
        guard choice == .play else {
            notice = choice == .demo ? "The original demo is not ported yet." : "The original utility program is not ported yet."
            return
        }
        let route=try state.select(choice)
        startup=state
        guard route.destination == .play else { return }
        // Original code changes a boot directory and reboots. The native port
        // expresses that route without writing either supplied disk image.
        try present(StartupTextScreen.compose(background:title.page,font:resources.font,
            messages:resources.playFlipMessages))
        diskButtons=ButtonInput()
        setScreen(.playDisk)
    }
    func input(channel: Int, down: Bool) {
        guard (0..<2).contains(channel) else { return }
        samples[channel] = down ? 0x80 : 0
        do {
            if screen == .ship, channel==0, var ship=shipInteraction {
                let action=ship.button(down:down)
                shipInteraction=ship
                if let action {
                    notice = action==1 ? "조종석을 선택했습니다. 조종석 화면과 계기 조작은 아직 포팅 중입니다."
                        : "이 장소를 선택했습니다. 이 장소의 화면과 동작은 아직 포팅 중입니다."
                }
            } else if screen == .ship, channel==1, down {
                cancelShipInput()
                notice="원본 두 번째 버튼의 메뉴·저장 기능은 아직 포팅 중입니다."
            } else if screen == .awaitingBegin { try pollBegin() }
            else if screen == .playDisk, let resources=startupResources {
                diskButtons.latch(first:samples[0],second:samples[1])
                let a=try diskButtons.poll(selector:0,sample:samples[0]).value
                let b=try diskButtons.poll(selector:1,sample:samples[1]).value
                if a || b {
                    guard try PlayDiskGate.check(block:resources.playBoot) == .accepted else {
                        notice="The bundled disk does not pass the original PLAY-side check."
                        return
                    }
                    let saved=resources.shipState
                    shipInteraction=try ShipInteraction(background:resources.initialShip,font:resources.font,
                        actor:.init(saved.x,saved.y),word38:saved.word38,word39:saved.word39,pointerGlyph:saved.pointerGlyph)
                    try present(shipInteraction!.page())
                    setScreen(.ship)
                    startShipTicker()
                }
            }
        } catch { self.error=error.localizedDescription; notice=error.localizedDescription }
    }
    func movePointer(x: Double, y: Double) {
        guard screen == .ship, var ship=shipInteraction else { return }
        ship.movePointer(x:x,y:y);shipInteraction=ship
        do { try present(ship.page()) } catch { self.error=error.localizedDescription }
    }
    func cancelShipInput() {
        samples=[0,0];shipInteraction?.cancel()
    }
    private func startShipTicker() {
        shipTicker?.cancel()
        shipTicker=Task { [weak self] in
            while !Task.isCancelled {
                do { try await Task.sleep(for:.milliseconds(33)) } catch { return }
                guard let self, self.screen == .ship else { return }
                self.advanceShip()
            }
        }
    }
    func advanceShip() {
        guard var ship=shipInteraction,ship.held else { return }
        // Declared host pacing: two movement stages, approximately30Hz.
        // Original Apple II loop timing/world simulation is not reconstructed.
        ship.step();ship.step();shipInteraction=ship
        do { try present(ship.page()) } catch { self.error=error.localizedDescription }
    }
    var shipActor: ShipInteraction.Point? { shipInteraction?.actor }
    var shipPointer: ShipInteraction.Point? { shipInteraction?.pointer }
    var shipHeld: Bool { shipInteraction?.held ?? false }
    var shipAction: Int { shipInteraction?.lastAction ?? 0 }
    private func pollBegin() throws {
        guard var state=startup, state.stage == .awaitingBegin else { return }
        let finished=try state.poll(first:samples[0],second:samples[1])
        startup=state
        if finished { try showChoices() }
    }
    func click(x: Double, y: Double) {
        guard screen == .choices, let state=startup else { return }
        for (index,choice) in state.choices.enumerated() {
            let top=137+15*index
            if (139...266).contains(x), Double(top)<=y, y<=Double(top+14) {
                do { try selectChoice(choice) } catch { notice=error.localizedDescription }
                return
            }
        }
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
            try beginStartup()
            // Original gate has a logical 11,400-iteration limit. This nominal
            // 1,000 polls/sec is host policy, not a measured Pascal loop duration.
            let gateStart=clock.now
            while screen == .awaitingBegin && !Task.isCancelled {
                let duration=gateStart.duration(to:clock.now).components
                let elapsed=Double(duration.seconds)+Double(duration.attoseconds)/1e18
                let target=min(11400,Int(elapsed*1000))
                while screen == .awaitingBegin, let remaining=startup?.remainingIterations,
                      11400-Int(remaining)<target { try pollBegin() }
                try await Task.sleep(for:.milliseconds(16))
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
            var startupScreen: String?
            if let i=args.firstIndex(of:"--startup-screen"), i+1<args.count {
                startupScreen=args[i+1]
                do {
                    try model.beginStartup()
                    if startupScreen != "gate" {
                        model.input(channel:0,down:true);model.input(channel:0,down:false)
                    }
                    if startupScreen == "play-disk" || startupScreen == "ship" { try model.selectChoice(.play) }
                    if startupScreen == "ship" {
                        model.input(channel:1,down:true);model.input(channel:1,down:false)
                    }
                } catch { model.error=error.localizedDescription }
            }
            if args.contains("--ship-mouse-check"), model.screen == .ship {
                model.movePointer(x:80,y:100);model.input(channel:0,down:true)
                for _ in 0..<12 { model.advanceShip() }
                model.input(channel:0,down:false)
                model.advanceShip()
            }
            if args.contains("--ship-action-check"), model.screen == .ship {
                model.movePointer(x:45,y:100);model.input(channel:0,down:true)
                model.advanceShip();model.input(channel:0,down:false)
            }
            var report: [String: Any] = ["screen": backgroundOnly ? "boot-background" : "original-title", "gameplay_available": false,
                                         "gui_verified": false, "error": model.error ?? "",
                                         "applied_writes": model.appliedWriteCount, "page_sha256": model.pageSHA256,
                                         "title_steps": model.titleStepCount, "title_complete": model.titleComplete]
            if let actor=model.shipActor, let pointer=model.shipPointer {
                report["actor"]=[actor.x,actor.y];report["pointer"]=[pointer.x,pointer.y]
                report["left_held"]=model.shipHeld
                report["selected_action"]=model.shipAction
                report["notice"]=model.notice ?? ""
                report["ship_mouse_control"]=true
            }
            if startupScreen != nil {
                report["screen"]=model.screen.rawValue
                report["history"]=model.history
                report["player"]=model.playerName
                report["original_state"]=model.originalGameState
            }
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
                        .overlay(GameInputSurface(
                            button: { channel,down,x,y in
                                let choosing=model.screen == .choices
                                model.input(channel:channel,down:down)
                                if choosing && down { model.click(x:x,y:y) }
                            }, pointer: { x,y in model.movePointer(x:x,y:y) },
                            cancel: { model.cancelShipInput() }, activate: {
                                if model.screen == .choices {
                                    do { try model.selectChoice(.play) } catch { model.notice=error.localizedDescription }
                                } else { model.input(channel:0,down:true) }
                            }, choice: { value in
                                if let choice=StartupFlow.Choice(rawValue:value) {
                                    do { try model.selectChoice(choice) } catch { model.notice=error.localizedDescription }
                                }
                            }))
                        .aspectRatio(4.0 / 3.0, contentMode: .fit)
                        .accessibilityLabel("SunDog game display")
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
            .onReceive(NotificationCenter.default.publisher(for:NSApplication.didResignActiveNotification)) { _ in
                model.cancelShipInput()
            }
            .alert("SunDog",isPresented:Binding(get:{model.notice != nil},set:{if !$0 {model.notice=nil}})) {
                Button("OK") { model.notice=nil }
            } message: { Text(model.notice ?? "") }
        }.defaultSize(width: 840, height: 630)
        .commands {
            CommandGroup(replacing: .appInfo) {
                Button("About SunDog") {
                    let alert = NSAlert()
                    alert.messageText = "SunDog: Frozen Legacy — Native Port"
                    alert.informativeText = "Title, original begin prompt, startup choices, PLAY-side validation and the initial SHIP graphics are reconstructed in native code. Click or press Space/Return to advance. Move the mouse to aim, hold the left button to walk, and release to select at the actor position. Facility screens, world simulation and utility/demo programs are not implemented yet."
                    alert.runModal()
                }
            }
            CommandGroup(replacing: .newItem) { }
        }
    }
}
