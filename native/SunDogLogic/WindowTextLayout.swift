/// Selected successful paths of segment 22 P48/P47/P45. This planner emits
/// logical glyph positions; it does not implement P44 scrolling or P12 lines.
public enum WindowTextLayout {
    public struct State: Equatable, Sendable {
        public var left: Int
        public var right: Int
        public var bottom: Int
        public var x: Int
        public var y: Int
        public init(left: Int, right: Int, bottom: Int, x: Int, y: Int) {
            self.left = left; self.right = right; self.bottom = bottom
            self.x = x; self.y = y
        }
    }
    public struct Glyph: Equatable, Sendable {
        public let character: UInt8
        public let x: Int
        public let y: Int
    }
    public struct Result: Equatable, Sendable {
        public let glyphs: [Glyph]
        public let state: State
    }
    public enum Failure: Error, Equatable {
        case stringCapacityExceeded, unsupportedCharacter, unsupportedLongWord
        case outsideVerifiedDomain, requiresBottomHandler
    }

    public static func plan(bytes: [UInt8], state initial: State) throws -> Result {
        guard bytes.count <= 80 else { throw Failure.stringCapacityExceeded }
        guard bytes.allSatisfy({ $0 < 128 }) else { throw Failure.unsupportedCharacter }
        guard (0...270).contains(initial.left), (initial.left + 2...272).contains(initial.right),
              (7...191).contains(initial.bottom), (0...278).contains(initial.x),
              (7...initial.bottom).contains(initial.y) else { throw Failure.outsideVerifiedDomain }
        var state = initial
        var glyphs: [Glyph] = []
        func delimiter(_ c: UInt8) -> Bool { c == 32 || c == 92 || c == 124 }
        func nextLine() throws {
            state.x = state.left + 2
            state.y += 8
            guard state.y <= state.bottom else { throw Failure.requiresBottomHandler }
        }
        func draw(_ c: UInt8) throws {
            if state.x > state.right - 5 { try nextLine() }
            glyphs.append(Glyph(character: c, x: state.x, y: state.y))
            state.x += 6
            if state.x > state.right - 5 { try nextLine() }
        }
        var index = 0
        while index < bytes.count {
            let c = bytes[index]
            if c == 32 {
                if state.x > state.left + 2 { try draw(32) }
                index += 1
            } else if c == 92 {
                if state.x > state.left + 2 { try nextLine() }
                index += 1
            } else if c == 124 {
                try draw(32)
                index += 1
            } else {
                let start = index
                while index < bytes.count && !delimiter(bytes[index]) { index += 1 }
                let count = index - start
                // P48 local49 byte scratch aliases later scalar locals beyond
                // this selected safe prefix; do not assume an 80-byte word.
                guard count <= 20 else { throw Failure.unsupportedLongWord }
                if state.x + 6 * count > state.right { try nextLine() }
                for character in bytes[start..<index] { try draw(character) }
            }
        }
        return Result(glyphs: glyphs, state: state)
    }
}
