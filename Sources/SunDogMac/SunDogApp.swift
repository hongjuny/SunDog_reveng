import SwiftUI
import AppKit
import AppleIIVideo
import SunDogCore
import SunDogLogic

@MainActor final class NativeModel: ObservableObject {
    @Published var text = "SUNDOG: FROZEN LEGACY\n\nNATIVE MACOS PORT\n\nAPPLE II GLYPH RENDERING\n\nSPACE / RETURN OR CLICK"
    @Published var frame: VideoFrame?
    @Published var message = "Open the original font exported from your Utility disk."
    @Published var presses = [0, 0]
    private var font: [UInt8]?
    private var buttons = HostButtonBridge()

    init() {
        let args = CommandLine.arguments
        if let i = args.firstIndex(of: "--font"), i + 1 < args.count {
            load(URL(fileURLWithPath: args[i + 1]))
        } else if let url = Bundle.main.url(forResource: "sundog-font", withExtension: "bin") {
            load(url)
        }
    }
    func load(_ url: URL) {
        do {
            let candidate = [UInt8](try Data(contentsOf: url))
            _ = try NativeTextPage.compose(text: "", font: candidate)
            font = candidate
            render()
        } catch { message = error.localizedDescription }
    }
    func render() {
        guard let font else { return }
        do {
            frame = try HGRDecoder.decode(page: NativeTextPage.compose(text: text, font: font))
            message = "Original glyph compositor · 280 × 192 · \(HGRDecoder.preset)"
        } catch { message = error.localizedDescription }
    }
    func openFont() {
        let panel = NSOpenPanel()
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = false
        panel.prompt = "Open Font"
        if panel.runModal() == .OK, let url = panel.url { load(url) }
    }
    func input(channel: Int, down: Bool) {
        guard (0..<2).contains(channel) else { return }
        guard let edges = try? buttons.set(channel: channel, down: down) else { return }
        for index in 0..<2 where edges[index] { presses[index] += 1 }
    }
}

@main @MainActor struct SunDogApp: App {
    @StateObject private var model = NativeModel()
    var body: some Scene {
        WindowGroup("SunDog — Native Port Preview") {
            VStack(spacing: 12) {
                HStack {
                    Button("Open Original Font…") { model.openFont() }
                    Spacer()
                    Text("Rendering & input milestone").foregroundStyle(.secondary)
                }
                ZStack {
                    Color.black
                    if let frame = model.frame { NativeScreen(frame: frame) }
                    else { Text("SunDog").font(.largeTitle).foregroundStyle(.white) }
                    InputSurface { channel, down in model.input(channel: channel, down: down) }
                }
                .aspectRatio(4.0/3.0, contentMode: .fit)
                .accessibilityLabel("Native SunDog glyph canvas. Click to focus; Space and Return are input channels.")
                TextField("Character codes 0–127", text: $model.text, axis: .vertical)
                    .lineLimit(2...5).font(.system(.body, design: .monospaced))
                    .onChange(of: model.text) { _, _ in model.render() }
                HStack {
                    Text("Input 1: \(model.presses[0])    Input 2: \(model.presses[1])")
                    Spacer()
                    Text("Gameplay reconstruction in progress").foregroundStyle(.secondary)
                }.font(.caption)
                Text(model.message).font(.caption).textSelection(.enabled)
            }.padding().frame(minWidth: 680, minHeight: 620)
            .onReceive(NotificationCenter.default.publisher(for: NSApplication.didResignActiveNotification)) { _ in
                model.input(channel: 0, down: false)
                model.input(channel: 1, down: false)
            }
        }.defaultSize(width: 880, height: 820)
        .commands {
            CommandGroup(replacing: .newItem) {
                Button("Open Original Font…") { model.openFont() }.keyboardShortcut("o")
            }
        }
    }
}

@MainActor struct InputSurface: NSViewRepresentable {
    var input: (Int, Bool) -> Void
    func makeNSView(context: Context) -> Surface {
        let view = Surface(); view.input = input; return view
    }
    func updateNSView(_ view: Surface, context: Context) { view.input = input }
    final class Surface: NSView {
        var input: ((Int, Bool) -> Void)?
        override var acceptsFirstResponder: Bool { true }
        override func mouseDown(with event: NSEvent) { window?.makeFirstResponder(self); input?(0, true) }
        override func mouseUp(with event: NSEvent) { input?(0, false) }
        override func rightMouseDown(with event: NSEvent) { window?.makeFirstResponder(self); input?(1, true) }
        override func rightMouseUp(with event: NSEvent) { input?(1, false) }
        override func keyDown(with event: NSEvent) {
            guard !event.isARepeat else { return }
            if event.keyCode == 49 { input?(0, true) }
            else if event.keyCode == 36 { input?(1, true) }
        }
        override func keyUp(with event: NSEvent) {
            if event.keyCode == 49 { input?(0, false) }
            else if event.keyCode == 36 { input?(1, false) }
        }
        override func resignFirstResponder() -> Bool { input?(0, false); input?(1, false); return true }
    }
}
