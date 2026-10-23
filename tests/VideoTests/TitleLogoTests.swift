import XCTest
import Foundation
import CryptoKit
import SunDogCore
import SunDogLogic

final class TitleLogoTests: XCTestCase {
    func testRealTitleCompositionAddsTheMissingLetterArea() throws {
        var glyphs = [UInt8](repeating: 0, count: 6144)
        // A declared synthetic bit in the final frame of the first letter.
        glyphs[7 * 128] = 1
        let page = try TitleLogo.compose(background: [UInt8](repeating: 0, count: 8192), glyphs: glyphs)
        let row44 = (44 & 7) * 1024 + ((44 >> 3) & 7) * 128 + (44 >> 6) * 40
        XCTAssertEqual(page[row44], 0x81)
        XCTAssertThrowsError(try TitleLogo(background: [], glyphs: glyphs))
        XCTAssertThrowsError(try TitleLogo(background: page, glyphs: []))
    }
    func testLogoResourceRejectsTruncationInsteadOfSilentlyShowingBackground() throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }
        let bytes = Data(repeating: 0, count: 6143)
        try bytes.write(to: directory.appendingPathComponent("sundog-title-logo.bin"))
        let digest = SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined()
        try JSONSerialization.data(withJSONObject: ["length": 6144, "sha256": digest])
            .write(to: directory.appendingPathComponent("sundog-title-logo.json"))
        XCTAssertThrowsError(try TitleLogoResource.load(directory: directory))
    }
}
