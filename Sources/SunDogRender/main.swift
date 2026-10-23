import Foundation
import AppKit
import AppleIIVideo
import SunDogCore

/// Offline rendering through the same native code used by the app.
@main struct Render {
    static func main() throws {
        let args = Array(CommandLine.arguments.dropFirst())
        guard args.count == 2 || args.count == 3 else {
            throw NSError(domain: "SunDogRender", code: 1, userInfo: [NSLocalizedDescriptionKey:
                "Usage: SunDogRender FONT.bin OUTPUT.png [ASCII text]"])
        }
        let font = [UInt8](try Data(contentsOf: URL(fileURLWithPath: args[0])))
        let text = args.count == 3 ? args[2] : "SUNDOG: FROZEN LEGACY\\NATIVE MACOS PORT"
        let page = try NativeTextPage.compose(text: text, font: font)
        let frame = try HGRDecoder.decode(page: page)
        let bitmap = NSBitmapImageRep(cgImage: try frame.cgImage())
        guard let png = bitmap.representation(using: .png, properties: [:]) else {
            throw NSError(domain: "SunDogRender", code: 2)
        }
        try png.write(to: URL(fileURLWithPath: args[1]))
        print("Rendered \(frame.width) × \(frame.height) using \(frame.preset)")
    }
}
