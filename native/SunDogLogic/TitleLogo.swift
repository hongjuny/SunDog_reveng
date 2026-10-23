/// Original segment26 P14/P16 logo visuals, rewritten as byte operations.
/// Sound-generator pacing and the rest of the startup menu are separate contracts.
public struct TitleLogo: Sendable {
    public enum Failure: Error { case invalidBackground, invalidGlyphs, invalidProgress }
    public struct Write: Equatable, Sendable {
        public let offset: Int
        public let value: UInt8
    }
    public struct Step: Sendable {
        public let glyph: Int
        public let iteration: Int
        public let writes: [Write]
    }
    public let steps: [Step]
    public private(set) var page: [UInt8]
    public private(set) var appliedStepCount = 0

    public init(background: [UInt8], glyphs: [UInt8]) throws {
        guard background.count == 8192 else { throw Failure.invalidBackground }
        guard glyphs.count == 6144 else { throw Failure.invalidGlyphs }
        page = background
        var work = background
        var result: [Step] = []
        func offset(_ y: Int, _ column: Int) -> Int {
            (y & 7) * 1024 + ((y >> 3) & 7) * 128 + (y >> 6) * 40 + column
        }
        var writes: [Write] = []
        func put(_ y: Int, _ column: Int, _ value: UInt8) {
            let p = offset(y, column)
            work[p] = value
            writes.append(Write(offset: p, value: value))
        }
        // P9: blank4, colored4, blank32, colored4, blank4 scanlines per column.
        for column in 0..<30 {
            let color: UInt8 = column == 29 ? 0 : column % 2 == 0 ? 0xaa : 0xd5
            for y in 32..<80 { put(y, column, (36..<40).contains(y) || (72..<76).contains(y) ? color : 0) }
        }
        result.append(Step(glyph: -1, iteration: 0, writes: writes))
        let snapshot = (44..<68).flatMap { y in (0..<40).map { work[offset(y, $0)] } }
        for glyph in 0..<6 {
            let initialX = glyph % 2 == 0 ? 252 : 245
            let targetX = glyph * 35
            var x = initialX, trailingX = initialX + 21
            var active = true, restoring = false, frame = 0, pair = 0, iteration = 0
            repeat {
                writes = []; iteration += 1
                if active || frame < 8 {
                    let selectedFrame = frame == 8 ? 7 : frame
                    for row in 0..<24 {
                        for column in 0..<4 {
                            put(44 + row, x / 7 + column, glyphs[glyph * 1024 + selectedFrame * 128 + row * 4 + column] | 0x80)
                        }
                    }
                    if x > targetX { x -= 14 } else { active = false }
                }
                if restoring {
                    for row in 0..<24 { put(44 + row, trailingX / 7, snapshot[row * 40 + trailingX / 7]) }
                    trailingX -= 7
                }
                if x == initialX - 28 { restoring = true }
                if trailingX == targetX + 21 { restoring = false }
                pair += 1
                if frame < 8 && pair == 2 { pair = 0; frame += 1 }
                result.append(Step(glyph: glyph, iteration: iteration, writes: writes))
            } while trailingX != targetX + 21 || frame != 8
        }
        steps = result
    }
    public mutating func advance(to count: Int) throws {
        guard count >= appliedStepCount, count <= steps.count else { throw Failure.invalidProgress }
        for step in steps[appliedStepCount..<count] {
            for write in step.writes { page[write.offset] = write.value }
        }
        appliedStepCount = count
    }
    public static func compose(background: [UInt8], glyphs: [UInt8]) throws -> [UInt8] {
        var result = try TitleLogo(background: background, glyphs: glyphs)
        try result.advance(to: result.steps.count)
        return result.page
    }
}
