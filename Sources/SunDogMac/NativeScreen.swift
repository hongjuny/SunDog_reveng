import SwiftUI
import AppKit
import MetalKit
import AppleIIVideo

struct NativeScreen: View {
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
