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
        let page = try NativeTextPage.compose(text: "A\nA", font: font)
        XCTAssertEqual(page[HGRDecoder.rowOffset(8) + 1], 1)
        XCTAssertEqual(page[HGRDecoder.rowOffset(15) + 1], 2)
        XCTAssertEqual(page[HGRDecoder.rowOffset(16) + 1], 1)
        XCTAssertEqual(page[HGRDecoder.rowOffset(23) + 1], 2)
    }
    func testInvalidAssetsAndUnicodeFailExplicitly() {
        XCTAssertThrowsError(try NativeTextPage.compose(text: "A", font: []))
        XCTAssertThrowsError(try NativeTextPage.compose(text: "한글", font: [UInt8](repeating: 0, count: 1024)))
    }
    func testBottomAndHorizontalOverflowAreBounded() throws {
        let font = [UInt8](repeating: 0x3f, count: 1024)
        let page = try NativeTextPage.compose(text: String(repeating: "A", count: 5000), font: font)
        XCTAssertEqual(page.count, 8192)
        XCTAssertTrue(page.contains(where: { $0 != 0 }))
    }
}
