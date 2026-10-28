import XCTest
import SunDogLogic

final class PlayDiskGateTests: XCTestCase {
    func testExactMarkerAndOriginalIOExit() throws {
        var block=[UInt8](repeating:0,count:512)
        XCTAssertEqual(try PlayDiskGate.check(block:block),.wrongSide)
        XCTAssertEqual(try PlayDiskGate.check(block:block,wantUtility:true),.accepted)
        block[252]=9
        XCTAssertEqual(try PlayDiskGate.check(block:block),.accepted)
        XCTAssertEqual(try PlayDiskGate.check(block:block,ioResult:1),.nonlocalExit)
        XCTAssertEqual(try PlayDiskGate.check(block:block,ioResult:-1),.accepted)
        XCTAssertThrowsError(try PlayDiskGate.check(block:Array(block.prefix(511))))
    }
}
