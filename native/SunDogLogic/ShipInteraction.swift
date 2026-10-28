/// Native reconstruction of SHIP15 P13/P14 and library22 P22.
/// Host mouse coordinates replace the calibrated paddle coordinates.
public struct ShipInteraction: Sendable {
    public struct Point: Equatable, Sendable {
        public var x: Int
        public var y: Int
        public init(_ x: Int, _ y: Int) { self.x=x; self.y=y }
    }
    public private(set) var actor: Point
    public private(set) var pointer: Point
    public private(set) var held = false
    public private(set) var lastAction = 0
    public let background: [UInt8]
    private let font: [UInt8]
    private let word38: Int
    private let word39: Int
    private let pointerGlyph: Int
    public enum Failure: Error { case invalidResources }
    public init(background: [UInt8], font: [UInt8], actor: Point,
                word38: Int, word39: Int, pointerGlyph: Int = 2) throws {
        guard background.count==8192, font.count==1024,
              (0...272).contains(actor.x), (7...191).contains(actor.y),
              (0..<128).contains(pointerGlyph) else { throw Failure.invalidResources }
        self.background=background; self.font=font; self.actor=actor
        self.word38=word38; self.word39=word39; self.pointerGlyph=pointerGlyph
        self.pointer=Point(max(3,min(267,actor.x+3)),max(5,min(180,actor.y-3)))
    }
    public mutating func movePointer(x: Double, y: Double) {
        guard x.isFinite, y.isFinite else { return }
        pointer=Point(Int(max(3,min(267,x))),Int(max(5,min(180,y))))
    }
    /// Cancel on focus loss without activating a facility.
    public mutating func cancel() { held=false }
    @discardableResult public mutating func button(down: Bool) -> Int? {
        guard down != held else { return nil }
        held=down
        if down { lastAction=0; return nil }
        let action=Self.action(at:actor,word38:word38,word39:word39)
        guard action != lastAction else { return nil }
        lastAction=action
        return action>0 ? action : nil
    }
    /// One held movement stage; caller supplies host pacing, not Apple II FPS.
    public mutating func step() {
        guard held else { return }
        let dx=pointer.x-3-actor.x, dy=pointer.y+3-actor.y
        let before=actor
        attempt(dx:max(-2,min(2,dx)),dy:max(-2,min(2,dy)))
        if actor==before { attempt(dx:dx.signum(),dy:dy.signum()) }
    }
    private mutating func attempt(dx: Int, dy: Int) {
        guard dx != 0 || dy != 0 else { return }
        for delta in [Point(dx,dy),Point(dx,0),Point(0,dy)] {
            let p=Point(actor.x+delta.x,actor.y+delta.y)
            if !collides(at:p) { actor=p; return }
        }
    }
    public func collides(at p: Point) -> Bool {
        guard (0...272).contains(p.x), (7...191).contains(p.y) else { return true }
        // P22 selects P9 mode2 with glyph13; SHIP global2=8 gives masks7F/7F.
        let column=p.x/7, shift=p.x%7
        for row in 0..<8 {
            let y=p.y-7+row
            let offset=(y&7)*0x400+((y>>3)&7)*0x80+(y>>6)*40+column
            let bits=Int(font[13*8+7-row]&0x7f)
            let low=(bits<<shift)&0x7f
            let high=shift==0 ? 0 : bits>>(7-shift)
            if Int(background[offset])&low != 0 || Int(background[offset+1])&high != 0 { return true }
        }
        return false
    }
    public func page() throws -> [UInt8] {
        var page=background
        try GlyphCompositor.draw(glyph:Array(font[96..<104]),page:&page,x:actor.x,baseline:actor.y,maskLow:0,maskHigh:0)
        try GlyphCompositor.draw(glyph:Array(font[pointerGlyph*8..<pointerGlyph*8+8]),page:&page,
            x:pointer.x-3,baseline:pointer.y+3,maskLow:0,maskHigh:0)
        return page
    }
    public static func action(at p: Point, word38: Int, word39: Int) -> Int {
        let col=(p.x+3)/7, row=(p.y-3)/8
        let equipped=(word38&63)+(word39&31)>0
        switch col {
        case 6: return row==12 ? 1 : 0
        case 8: return row==14 && equipped ? 4 : row==10 ? 6 : 0
        case 12: return row==13 ? 5 : 0
        case 14: return row==14 && equipped ? 3 : 0
        case 16: return [8:10,16:11,18:13][row] ?? ((p.y-5)/8==6 ? 8 : 0)
        case 17: return [15:7,7:9,17:12][row] ?? 0
        default: return 0
        }
    }
}
