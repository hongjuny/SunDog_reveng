import XCTest
import Foundation
import CryptoKit
import SunDogCore

final class SplashScreenTests: XCTestCase {
    private func fixture(page: Data, declaredHash: String? = nil, length: Int = 8192,
                         check: (URL, URL) throws -> Void) throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }
        let source = directory.appendingPathComponent("splash.hgr")
        let manifest = directory.appendingPathComponent("splash.json")
        try page.write(to: source)
        let digest = declaredHash ?? SHA256.hash(data: page).map { String(format: "%02x", $0) }.joined()
        try JSONSerialization.data(withJSONObject: ["sha256": digest, "length": length]).write(to: manifest)
        try check(source, manifest)
    }
    func testDiskPageBecomesImageWithoutCaptureOrFont() throws {
        var page = Data(repeating: 0, count: 8192)
        page[0] = 0x7f
        try fixture(page: page) { source, manifest in
            let splash = try SplashScreen.load(pageURL: source, manifestURL: manifest)
            XCTAssertEqual(splash.frame.width, 560)
            XCTAssertEqual(splash.frame.height, 192)
            XCTAssertTrue(splash.frame.rgba.prefix(3).contains(where: { $0 != 0 }))
        }
    }
    func testTamperedAssetAndTruncationFail() throws {
        try fixture(page: Data(repeating: 0, count: 8192), declaredHash: "wrong") { source, manifest in
            XCTAssertThrowsError(try SplashScreen.load(pageURL: source, manifestURL: manifest))
        }
        try fixture(page: Data(repeating: 0, count: 8191)) { source, manifest in
            XCTAssertThrowsError(try SplashScreen.load(pageURL: source, manifestURL: manifest))
        }
    }
}
