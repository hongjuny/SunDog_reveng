import XCTest
import SunDogCore
import AppleIIVideo

final class NativeTextPageTests: XCTestCase {
    func testTwoHostChannelsReleaseWithoutStaleLatches() throws {
        var input = HostButtonBridge()
        XCTAssertEqual(try input.set(channel: 0, down: true), [true, false])
        XCTAssertEqual(try input.set(channel: 1, down: true), [false, true])
        XCTAssertEqual(try input.set(channel: 0, down: false), [false, false])
        XCTAssertEqual(try input.set(channel: 0, down: true), [true, false])
        XCTAssertEqual(try input.set(channel: 0, down: true), [false, false])
        XCTAssertThrowsError(try input.set(channel: 2, down: true))
    }
    func testOriginalRowOrderAndHostLinePlacement() throws {
        var font = [UInt8](repeating: 0, count: 1024)
        font[65 * 8 + 7] = 1
        font[65 * 8] = 2
        let page = try NativeTextPage.compose(text: "A\\A", font: font)
        XCTAssertEqual(page[HGRDecoder.rowOffset(8) + 1], 1)
        XCTAssertEqual(page[HGRDecoder.rowOffset(15) + 1], 2)
        XCTAssertEqual(page[HGRDecoder.rowOffset(16) + 1], 1)
        XCTAssertEqual(page[HGRDecoder.rowOffset(23) + 1], 2)
    }
    func testInvalidAssetsAndUnicodeFailExplicitly() {
        XCTAssertThrowsError(try NativeTextPage.compose(text: "A", font: []))
        XCTAssertThrowsError(try NativeTextPage.compose(text: "한글", font: [UInt8](repeating: 0, count: 1024)))
    }
    func testOriginalStringCapacityIsNotSilentlyTruncated() {
        let font = [UInt8](repeating: 0x3f, count: 1024)
        XCTAssertThrowsError(try NativeTextPage.compose(text: String(repeating: "A", count: 81), font: font))
    }
    func testOriginalLeadingSpaceAndForcedSpaceReachRaster() throws {
        var font = [UInt8](repeating: 0, count: 1024)
        font[65 * 8 + 7] = 1
        let ordinary = try NativeTextPage.compose(text: "A", font: font)
        XCTAssertEqual(try NativeTextPage.compose(text: "  \\A", font: font), ordinary)
        let forced = try NativeTextPage.compose(text: "|A", font: font)
        XCTAssertEqual(forced[HGRDecoder.rowOffset(8) + 1], 64)
        XCTAssertNotEqual(forced, ordinary)
    }
}
