import Foundation
import CryptoKit

/// Six original letter records, each containing eight prerasterized frames.
public struct TitleLogoResource: Sendable {
    public let bytes: [UInt8]
    public let sha256: String
    private struct Manifest: Decodable { let length: Int; let sha256: String }
    public enum Failure: Error, LocalizedError {
        case invalidAsset
        public var errorDescription: String? { "The original title-logo resource is missing, truncated or changed." }
    }
    public static func load(directory: URL) throws -> TitleLogoResource {
        let metadata = try JSONDecoder().decode(Manifest.self,
            from: Data(contentsOf: directory.appendingPathComponent("sundog-title-logo.json")))
        let data = try Data(contentsOf: directory.appendingPathComponent("sundog-title-logo.bin"))
        let digest = SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
        guard data.count == 6144, metadata.length == 6144, digest == metadata.sha256 else {
            throw Failure.invalidAsset
        }
        return TitleLogoResource(bytes: Array(data), sha256: digest)
    }
}
