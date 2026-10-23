import Foundation
import CryptoKit
import AppleIIVideo
import SunDogCore

@main struct Inspect {
    static func main() {
        do { try run() } catch {
            FileHandle.standardError.write(Data((error.localizedDescription + "\n").utf8))
            Foundation.exit(1)
        }
    }
    static func run() throws {
        let args = Array(CommandLine.arguments.dropFirst())
        func value(_ key: String) -> String? {
            guard let i = args.firstIndex(of: key), i + 1 < args.count else { return nil }
            return args[i + 1]
        }
        guard let directory = value("--capture"), let label = value("--label") else {
            throw CaptureError.invalid("Usage: SunDogInspect --capture DIRECTORY --label LABEL [--rgba-out FILE] [--compare FILE]")
        }
        let capture = try ReferenceCapture.load(directory: URL(fileURLWithPath: directory), label: label)
        let data = Data(capture.frame.rgba)
        var report: [String: Any] = ["width": capture.frame.width, "height": capture.frame.height,
            "preset": capture.frame.preset, "page": capture.pageAddress,
            "sha256": SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()]
        if let output = value("--rgba-out") { try data.write(to: URL(fileURLWithPath: output)) }
        if let comparison = value("--compare") {
            let expected = [UInt8](try Data(contentsOf: URL(fileURLWithPath: comparison)))
            guard expected.count == data.count else { throw CaptureError.invalid("Reference frame has a different size.") }
            let actual = capture.frame.rgba
            let differing = stride(from: 0, to: actual.count, by: 4).filter {
                actual[$0..<$0+4] != expected[$0..<$0+4]
            }.count
            report["different_pixels"] = differing
            report["matches_reference"] = differing == 0
        }
        if args.contains("--verify-metal") {
            do {
                let pixels = try MetalFrameRenderer.offscreen(frame: capture.frame)
                report["metal_matches_cpu"] = pixels == capture.frame.rgba
            } catch { report["metal_error"] = error.localizedDescription }
        }
        let encoded = try JSONSerialization.data(withJSONObject: report, options: [.sortedKeys])
        print(String(decoding: encoded, as: UTF8.self))
        if report["matches_reference"] as? Bool == false || report["metal_matches_cpu"] as? Bool == false { Foundation.exit(2) }
        if report["metal_error"] != nil { Foundation.exit(3) }
    }
}
