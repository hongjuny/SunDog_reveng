import Foundation
import CryptoKit
import AppleIIVideo

public enum CaptureError: Error, LocalizedError {
    case invalid(String)
    public var errorDescription: String? { if case .invalid(let text) = self { return text }; return nil }
}

/// Captured original execution input for the first renderer milestone.
/// This is not a game VM and does not manufacture missing machine state.
public struct ReferenceCapture: Sendable {
    public let frame: VideoFrame
    public let label: String
    public let source: URL
    public let pageAddress: Int

    public static func load(directory: URL, label: String) throws -> ReferenceCapture {
        guard !label.isEmpty, label.allSatisfy({ $0.isASCII && ($0.isLetter || $0.isNumber || $0 == "-") }) else {
            throw CaptureError.invalid("Invalid capture label.")
        }
        let manifest = try JSONSerialization.jsonObject(with: Data(contentsOf: directory.appendingPathComponent("manifest.json")))
        guard let root = manifest as? [String: Any] else { throw CaptureError.invalid("Invalid capture manifest.") }
        let records = (root["checkpoints"] as? [[String: Any]]) ?? (root["events"] as? [[String: Any]]) ?? []
        guard let record = records.first(where: { row in
            row["label"] as? String == label || (row["frame"] as? [String: Any])?["pixels"] as? String == label + ".rgba"
        }), let switches = record["softswitches"] as? String else {
            throw CaptureError.invalid("Capture label is absent from the manifest.")
        }
        let fields = Dictionary(switches.split(separator: " ").compactMap { token -> (String, String)? in
            let parts = token.split(separator: "=", maxSplits: 1)
            return parts.count == 2 ? (String(parts[0]), String(parts[1])) : nil
        }, uniquingKeysWith: { _, new in new })
        guard fields["TEXT"] == "0", fields["HIRES"] == "1", fields["MIXED"] == "0",
              fields["COL80"] == "0", fields["80STORE"] == "0",
              ["0", "1"].contains(fields["PAGE2"] ?? "") else {
            throw VideoError.unsupportedMode("the captured text/mixed/auxiliary mode")
        }
        let page = fields["PAGE2"] == "1" ? 0x4000 : 0x2000
        let source = directory.appendingPathComponent(label + "-main.bin")
        let memory = [UInt8](try Data(contentsOf: source))
        guard memory.count == 65536 else { throw CaptureError.invalid("Expected a complete 64 KiB main-memory capture.") }
        let digest = SHA256.hash(data: Data(memory)).map { String(format: "%02x", $0) }.joined()
        guard let expected = record["main_sha256"] as? String, digest == expected else {
            throw CaptureError.invalid("The captured memory hash does not match its manifest.")
        }
        let frame = try HGRDecoder.decode(page: Array(memory[page..<page + 8192]))
        return ReferenceCapture(frame: frame, label: label, source: source, pageAddress: page)
    }
}
