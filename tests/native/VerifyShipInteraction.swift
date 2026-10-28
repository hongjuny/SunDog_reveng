import Foundation
@main struct VerifyShipInteraction {
    struct Fixture: Decodable {
        struct Collision: Decodable { let x:Int;let y:Int;let hit:Bool }
        struct Action: Decodable { let x:Int;let y:Int;let w38:Int;let w39:Int;let action:Int }
        let page:[UInt8];let font:[UInt8];let collisions:[Collision];let actions:[Action]
    }
    static func main() throws {
        let data=try Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[1]))
        let f=try JSONDecoder().decode(Fixture.self,from:data)
        let ship=try ShipInteraction(background:f.page,font:f.font,actor:.init(42,103),word38:0,word39:0)
        for c in f.collisions { precondition(ship.collides(at:.init(c.x,c.y))==c.hit,"Native collision mismatch") }
        for a in f.actions { precondition(ShipInteraction.action(at:.init(a.x,a.y),word38:a.w38,word39:a.w39)==a.action,"Native action mismatch") }
        print("Ship collision \(f.collisions.count) and action \(f.actions.count) comparisons passed")
    }
}
