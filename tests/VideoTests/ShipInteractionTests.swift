import XCTest
import SunDogLogic

final class ShipInteractionTests: XCTestCase {
    func testHoldReleaseAndCancel() throws {
        let page=[UInt8](repeating:0,count:8192)
        let font=[UInt8](repeating:0,count:1024)
        var ship=try ShipInteraction(background:page,font:font,actor:.init(42,103),word38:0,word39:0)
        XCTAssertEqual(ship.button(down:false),nil)
        XCTAssertEqual(ship.button(down:true),nil)
        ship.step()
        XCTAssertEqual(ship.actor,.init(42,103))
        XCTAssertEqual(ship.button(down:false),1)
        XCTAssertEqual(ship.button(down:false),nil)
        ship.movePointer(x:80,y:100)
        ship.step();XCTAssertEqual(ship.actor,.init(42,103))
        ship.button(down:true);ship.step()
        XCTAssertEqual(ship.actor,.init(44,103))
        ship.cancel();ship.step()
        XCTAssertFalse(ship.held);XCTAssertEqual(ship.actor,.init(44,103))
    }
    func testClampAndXORErase() throws {
        var font=[UInt8](repeating:0,count:1024)
        font[96]=7; font[16]=7
        let background=[UInt8](repeating:0x80,count:8192)
        var ship=try ShipInteraction(background:background,font:font,actor:.init(42,103),word38:0,word39:0)
        ship.movePointer(x:-500,y:500)
        XCTAssertEqual(ship.pointer,.init(3,180))
        XCTAssertNotEqual(try ship.page(),background)
        XCTAssertEqual(ship.background,background)
        ship.movePointer(x:.infinity,y:.nan)
        XCTAssertEqual(ship.pointer,.init(3,180))
        XCTAssertThrowsError(try ShipInteraction(background:[],font:font,actor:.init(42,103),word38:0,word39:0))
    }
    func testCollisionSlidingAndStepFallback() throws {
        var font=[UInt8](repeating:0,count:1024)
        font[13*8]=1 // bottom row collision pixel
        var page=[UInt8](repeating:0,count:8192)
        func block(_ x:Int,_ y:Int) { page[(y&7)*1024+((y>>3)&7)*128+(y>>6)*40+x/7] |= UInt8(1<<(x%7)) }
        block(50,115)
        var ship=try ShipInteraction(background:page,font:font,actor:.init(48,114),word38:0,word39:0)
        ship.movePointer(x:53,y:112);ship.button(down:true);ship.step()
        XCTAssertEqual(ship.actor,.init(50,114))
        XCTAssertTrue(ship.collides(at:.init(50,115)))
        XCTAssertTrue(ship.collides(at:.init(-1,115)))
        block(50,114);block(48,115)
        var fallback=try ShipInteraction(background:page,font:font,actor:.init(48,114),word38:0,word39:0)
        fallback.movePointer(x:53,y:112);fallback.button(down:true);fallback.step()
        XCTAssertEqual(fallback.actor,.init(49,115))
    }
}
