import Foundation
import Metal

public enum MetalFrameError: Error, LocalizedError {
    case unavailable(String)
    public var errorDescription: String? { if case .unavailable(let s) = self { return s }; return nil }
}

public final class MetalFrameRenderer {
    public let device: MTLDevice
    private let pipeline: MTLRenderPipelineState
    private static let shader = """
    #include <metal_stdlib>
    using namespace metal;
    struct Varying { float4 position [[position]]; float2 uv; };
    vertex Varying vertex_screen(uint id [[vertex_id]]) {
        const float2 p[6] = { {-1,-1},{1,-1},{-1,1},{-1,1},{1,-1},{1,1} };
        Varying v; v.position=float4(p[id],0,1);
        v.uv=float2((p[id].x+1)*0.5,(1-p[id].y)*0.5); return v;
    }
    fragment float4 fragment_screen(Varying v [[stage_in]], texture2d<float> image [[texture(0)]]) {
        constexpr sampler nearest_filter(coord::normalized, address::clamp_to_edge, filter::nearest);
        return image.sample(nearest_filter,v.uv);
    }
    """

    public init(device: MTLDevice, pixelFormat: MTLPixelFormat) throws {
        self.device = device
        let library = try device.makeLibrary(source: Self.shader, options: nil)
        let descriptor = MTLRenderPipelineDescriptor()
        descriptor.vertexFunction = library.makeFunction(name: "vertex_screen")
        descriptor.fragmentFunction = library.makeFunction(name: "fragment_screen")
        descriptor.colorAttachments[0].pixelFormat = pixelFormat
        pipeline = try device.makeRenderPipelineState(descriptor: descriptor)
    }

    public func encode(frame: VideoFrame, pass: MTLRenderPassDescriptor, command: MTLCommandBuffer) throws {
        let descriptor = MTLTextureDescriptor.texture2DDescriptor(pixelFormat: .rgba8Unorm,
            width: frame.width, height: frame.height, mipmapped: false)
        descriptor.usage = .shaderRead
        descriptor.storageMode = .shared
        guard let texture = device.makeTexture(descriptor: descriptor) else {
            throw MetalFrameError.unavailable("Could not allocate the screen texture.")
        }
        frame.rgba.withUnsafeBytes {
            texture.replace(region: MTLRegionMake2D(0, 0, frame.width, frame.height), mipmapLevel: 0,
                withBytes: $0.baseAddress!, bytesPerRow: frame.width * 4)
        }
        guard let encoder = command.makeRenderCommandEncoder(descriptor: pass) else {
            throw MetalFrameError.unavailable("Could not create the screen encoder.")
        }
        encoder.setRenderPipelineState(pipeline)
        encoder.setFragmentTexture(texture, index: 0)
        encoder.drawPrimitives(type: .triangle, vertexStart: 0, vertexCount: 6)
        encoder.endEncoding()
    }

    public static func offscreen(frame: VideoFrame) throws -> [UInt8] {
        guard let device = MTLCreateSystemDefaultDevice(), let queue = device.makeCommandQueue(),
              let command = queue.makeCommandBuffer() else {
            throw MetalFrameError.unavailable("Metal is unavailable.")
        }
        let descriptor = MTLTextureDescriptor.texture2DDescriptor(pixelFormat: .rgba8Unorm,
            width: frame.width, height: frame.height, mipmapped: false)
        descriptor.usage = .renderTarget
        descriptor.storageMode = .shared
        guard let output = device.makeTexture(descriptor: descriptor) else {
            throw MetalFrameError.unavailable("Could not allocate the comparison texture.")
        }
        let renderer = try MetalFrameRenderer(device: device, pixelFormat: .rgba8Unorm)
        let pass = MTLRenderPassDescriptor()
        pass.colorAttachments[0].texture = output
        pass.colorAttachments[0].loadAction = .clear
        pass.colorAttachments[0].storeAction = .store
        try renderer.encode(frame: frame, pass: pass, command: command)
        command.commit(); command.waitUntilCompleted()
        guard command.status == .completed else {
            throw MetalFrameError.unavailable(command.error?.localizedDescription ?? "Metal comparison failed.")
        }
        var rgba = [UInt8](repeating: 0, count: frame.rgba.count)
        rgba.withUnsafeMutableBytes {
            output.getBytes($0.baseAddress!, bytesPerRow: frame.width * 4,
                from: MTLRegionMake2D(0, 0, frame.width, frame.height), mipmapLevel: 0)
        }
        return rgba
    }
}
