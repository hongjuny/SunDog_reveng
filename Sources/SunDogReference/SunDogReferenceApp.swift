import SwiftUI
import AppKit
import MetalKit
import AppleIIVideo
import SunDogCore

@MainActor final class ScreenModel: ObservableObject {
    @Published var capture: ReferenceCapture?
    @Published var message = "Open an original execution capture to view its Apple II screen."
    @Published var aspect = "4:3"
    @Published var label = "after-720-frames"

    init() {
        let args = CommandLine.arguments
        if let i = args.firstIndex(of: "--label"), i+1 < args.count { label = args[i+1] }
        if let i = args.firstIndex(of: "--capture"), i+1 < args.count {
            load(URL(fileURLWithPath: args[i+1]))
        }
    }
    func load(_ directory: URL) {
        do {
            capture = try ReferenceCapture.load(directory: directory, label: label)
            message = "Captured Apple II screen · \(label) · \(HGRDecoder.preset)"
        } catch { message = error.localizedDescription }
    }
    func open() {
        let panel = NSOpenPanel()
        panel.canChooseDirectories = true; panel.canChooseFiles = false
        panel.prompt = "Open Capture"
        if panel.runModal() == .OK, let url = panel.url { load(url) }
    }
}

@main @MainActor struct SunDogApp: App {
    @StateObject private var model = ScreenModel()
    var body: some Scene {
        WindowGroup("SunDog — Apple II Graphics Reference") {
            VStack(spacing: 12) {
                HStack {
                    Button("Open Capture…") { model.open() }
                    TextField("Checkpoint", text: $model.label).frame(width: 180)
                    Picker("Display", selection: $model.aspect) {
                        Text("4:3").tag("4:3")
                        Text("280:192").tag("280:192")
                        Text("Raw 560:192").tag("Raw")
                    }.frame(width: 220)
                    Spacer()
                }
                if let frame = model.capture?.frame {
                    ReferenceScreen(frame: frame)
                        .aspectRatio(model.aspect == "4:3" ? 4.0/3.0 : model.aspect == "Raw" ? 560.0/192.0 : 280.0/192.0, contentMode: .fit)
                        .background(.black)
                        .accessibilityLabel("Original SunDog Apple II reference screen")
                } else {
                    Color.black.overlay(Text("SunDog reference screen").foregroundStyle(.white))
                        .aspectRatio(4.0/3.0, contentMode: .fit)
                }
                HStack {
                    Text(model.message).font(.caption).textSelection(.enabled)
                    Spacer()
                    Text("Reference viewer · gameplay not connected").font(.caption).foregroundStyle(.secondary)
                }
            }.padding().frame(minWidth: 720, minHeight: 540)
        }.defaultSize(width: 900, height: 720)
        .commands { CommandGroup(replacing: .newItem) {
            Button("Open Reference Capture…") { model.open() }.keyboardShortcut("o")
        }}
    }
}

struct ReferenceScreen: View {
    let frame: VideoFrame
    var body: some View {
        if MTLCreateSystemDefaultDevice() != nil {
            MetalScreen(frame: frame)
        } else if let image = try? frame.cgImage() {
            Image(decorative: image, scale: 1).resizable().interpolation(.none)
        } else { Text("Could not create the reference image.") }
    }
}

struct MetalScreen: NSViewRepresentable {
    let frame: VideoFrame
    func makeCoordinator() -> Coordinator { Coordinator() }
    func makeNSView(context: Context) -> MTKView {
        let view = MTKView(frame: .zero, device: MTLCreateSystemDefaultDevice())
        view.colorPixelFormat = .bgra8Unorm
        view.colorspace = CGColorSpace(name: CGColorSpace.sRGB)
        view.clearColor = MTLClearColorMake(0, 0, 0, 1)
        view.isPaused = true; view.enableSetNeedsDisplay = true
        view.delegate = context.coordinator
        context.coordinator.frame = frame
        context.coordinator.configure(view)
        return view
    }
    func updateNSView(_ view: MTKView, context: Context) {
        context.coordinator.frame = frame
        view.setNeedsDisplay(view.bounds)
    }
    @MainActor final class Coordinator: NSObject, MTKViewDelegate {
        var frame: VideoFrame?
        var renderer: MetalFrameRenderer?
        var queue: MTLCommandQueue?
        func configure(_ view: MTKView) {
            do {
                guard let device = view.device else { throw MetalFrameError.unavailable("Metal device is unavailable.") }
                renderer = try MetalFrameRenderer(device: device, pixelFormat: view.colorPixelFormat)
                queue = device.makeCommandQueue()
            } catch { NSLog("SunDog renderer: %@", error.localizedDescription) }
        }
        func mtkView(_ view: MTKView, drawableSizeWillChange size: CGSize) {}
        func draw(in view: MTKView) {
            guard let frame, let renderer, let pass = view.currentRenderPassDescriptor,
                  let drawable = view.currentDrawable, let command = queue?.makeCommandBuffer() else { return }
            do {
                try renderer.encode(frame: frame, pass: pass, command: command)
                command.present(drawable); command.commit()
            } catch { NSLog("SunDog draw: %@", error.localizedDescription) }
        }
    }
}
