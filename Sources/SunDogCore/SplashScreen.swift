import Foundation
import CryptoKit
import AppleIIVideo

/// Original disk bitmap decoded directly; no saved screenshot or machine runtime.
public struct SplashScreen: Sendable {
    public let frame: VideoFrame
    public let page: [UInt8]
    public let assetSHA256: String
    private struct Manifest: Decodable { let length: Int; let sha256: String }
    public enum Failure: Error, LocalizedError {
        case invalidAsset, digestMismatch
        public var errorDescription: String? {
            switch self {
            case .invalidAsset: "The original splash resource must contain exactly 8,192 bytes."
            case .digestMismatch: "The splash resource does not match its verified disk extraction."
            }
        }
    }
    public static func load(pageURL: URL, manifestURL: URL) throws -> SplashScreen {
        let metadata = try JSONDecoder().decode(Manifest.self, from: Data(contentsOf: manifestURL))
        let data = try Data(contentsOf: pageURL)
        guard data.count == 8192, metadata.length == 8192 else { throw Failure.invalidAsset }
        let digest = SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
        guard digest == metadata.sha256 else { throw Failure.digestMismatch }
        return SplashScreen(frame: try HGRDecoder.decode(page: Array(data)), page: Array(data), assetSHA256: digest)
    }
}
