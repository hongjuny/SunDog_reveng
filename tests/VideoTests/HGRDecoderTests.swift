import CryptoKit
import XCTest
import AppleIIVideo
import SunDogCore

final class HGRDecoderTests: XCTestCase {
    func testRowsCoverVisibleBytesWithoutOverlap() {
        var addresses = Set<Int>()
        for row in 0..<192 {
            for column in 0..<40 { XCTAssertTrue(addresses.insert(HGRDecoder.rowOffset(row)+column).inserted) }
        }
        XCTAssertEqual(addresses.count, 7680)
        XCTAssertEqual(HGRDecoder.rowOffset(0), 0)
        XCTAssertEqual(HGRDecoder.rowOffset(8), 0x80)
        XCTAssertEqual(HGRDecoder.rowOffset(64), 0x28)
        XCTAssertEqual(HGRDecoder.rowOffset(191), 0x1fd0)
    }
    func testBlackPageIsOpaqueAndDoesNotExposePadding() throws {
        var page = [UInt8](repeating: 0, count: 8192)
        page[0x78] = 255 // hole after three visible 40-byte groups
        let frame = try HGRDecoder.decode(page: page)
        XCTAssertEqual(frame.rgba.count, 560*192*4)
        for p in stride(from: 0, to: frame.rgba.count, by: 4) {
            XCTAssertEqual(Array(frame.rgba[p..<p+4]), [0,0,0,255])
        }
    }
    func testPhaseAndByteBoundaryAreDecoded() throws {
        func pixel(_ value: UInt8, _ x: Int) throws -> [UInt8] {
            var page = [UInt8](repeating: 0, count: 8192); page[0] = value
            let frame = try HGRDecoder.decode(page: page)
            return Array(frame.rgba[x*4..<x*4+4])
        }
        XCTAssertEqual(try pixel(1,0), [0xc7,0x34,0xff,255])
        XCTAssertEqual(try pixel(0x81,0), [0x0d,0xa1,0xff,255])
        var page = [UInt8](repeating: 0, count: 8192); page[0]=0x40;page[1]=1
        let frame = try HGRDecoder.decode(page: page)
        XCTAssertEqual(Array(frame.rgba[12*4..<16*4]), Array(repeating: [UInt8](repeating:255,count:4),count:4).flatMap{$0})
    }
    func testInvalidPageFailsInsteadOfZeroFilling() {
        XCTAssertThrowsError(try HGRDecoder.decode(page: [0]))
    }
    func testTextCaptureDoesNotMasqueradeAsHGR() throws {
        let directory=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at:directory,withIntermediateDirectories:true)
        defer { try? FileManager.default.removeItem(at:directory) }
        let manifest: [String:Any] = ["events":[["label":"sample","softswitches":"TEXT=1 HIRES=1 MIXED=0 COL80=0 80STORE=0"]]]
        try JSONSerialization.data(withJSONObject:manifest).write(to:directory.appendingPathComponent("manifest.json"))
        XCTAssertThrowsError(try ReferenceCapture.load(directory:directory,label:"sample"))
    }
    func testCaptureRejectsTamperingAndMissingPageSwitch() throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }
        let memory = Data(repeating: 0, count: 65536)
        let hash = SHA256.hash(data: memory).map { String(format: "%02x", $0) }.joined()
        try memory.write(to: directory.appendingPathComponent("sample-main.bin"))
        func manifest(_ switches: String) throws {
            let value: [String: Any] = ["events": [["label": "sample", "softswitches": switches, "main_sha256": hash]]]
            try JSONSerialization.data(withJSONObject: value).write(to: directory.appendingPathComponent("manifest.json"))
        }
        let mode = "TEXT=0 HIRES=1 MIXED=0 COL80=0 80STORE=0"
        try manifest(mode)
        XCTAssertThrowsError(try ReferenceCapture.load(directory: directory, label: "sample"))
        try manifest(mode + " PAGE2=1")
        XCTAssertEqual(try ReferenceCapture.load(directory: directory, label: "sample").pageAddress, 0x4000)
        var changed = memory; changed[0] = 1
        try changed.write(to: directory.appendingPathComponent("sample-main.bin"))
        XCTAssertThrowsError(try ReferenceCapture.load(directory: directory, label: "sample"))
    }

}
