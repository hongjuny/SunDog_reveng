import XCTest
import Foundation
import SunDogCore
import SunDogLogic

final class SplashTimelineTests: XCTestCase {
    func testCycleBoundariesAndInvalidSchedule() throws {
        let file = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: file) }
        var cycles = Array(1...8041)
        func save() throws {
            try JSONSerialization.data(withJSONObject: ["write_cycles": cycles, "total_cycles": 515593]).write(to: file)
        }
        try save()
        let schedule = try SplashTimeline.load(url: file)
        XCTAssertEqual(schedule.writeCount(atCycle: 0), 0)
        XCTAssertEqual(schedule.writeCount(atCycle: 1), 1)
        XCTAssertEqual(schedule.writeCount(atCycle: 500), 500)
        XCTAssertEqual(schedule.writeCount(atCycle: 515593), 8041)
        XCTAssertEqual(schedule.writeCount(at: -1), 0)
        cycles[1] = cycles[0]
        try save()
        XCTAssertThrowsError(try SplashTimeline.load(url: file))
    }
    func testRevealRejectsRewindWithoutMutatingFrame() throws {
        var reveal = try SplashReveal(source: [UInt8](repeating: 0x7f, count: 8192))
        try reveal.advance(to: 100)
        let current = reveal.page
        XCTAssertThrowsError(try reveal.advance(to: 50))
        XCTAssertEqual(reveal.page, current)
        XCTAssertThrowsError(try reveal.advance(to: 8042))
        reveal.reset()
        XCTAssertEqual(reveal.appliedWriteCount, 0)
        XCTAssertTrue(reveal.page.allSatisfy { $0 == 0 })
    }
}
