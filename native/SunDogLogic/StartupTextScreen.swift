/// Original selected P51(40,24) startup window and subsequent P44/P48 messages.
/// Game text and font bytes are supplied as local media-derived resources.
public enum StartupTextScreen {
    public enum Failure: Error { case invalidPage, invalidFont, invalidMessages }
    private static func rectangle(_ page: inout [UInt8], _ left: Int, _ right: Int,
                                  _ top: Int, _ bottom: Int, mode: Int) {
        for y in top...bottom {
            let row = (y & 7) * 1024 + ((y >> 3) & 7) * 128 + (y >> 6) * 40
            for x in left...right {
                let p = row + x / 7
                let bit = UInt8(1 << (x % 7))
                let pattern: UInt8 = mode == 11 ? 0xff : mode == 10 ? (x / 7 % 2 == 0 ? 0xd5 : 0xaa) : 0x80
                page[p] = (page[p] & ~bit) | (pattern & bit) | 0x80
            }
        }
    }
    public static func compose(background: [UInt8], font: [UInt8], messages: [[UInt8]]) throws -> [UInt8] {
        guard background.count == 8192 else { throw Failure.invalidPage }
        guard font.count == 1024 else { throw Failure.invalidFont }
        guard messages.allSatisfy({ $0.count <= 80 && $0.allSatisfy({ $0 < 128 }) }) else {
            throw Failure.invalidMessages
        }
        var page = background
        // P51's 20-byte by 96-row window image, positioned at column19,row88.
        // Its template is white with a 2-pixel side / 1-row inner inset.
        rectangle(&page, 133, 272, 88, 183, mode: 11)
        rectangle(&page, 135, 270, 89, 182, mode: 8)
        // P44 mode8 clears the text bounds; this is inside the black template.
        rectangle(&page, 135, 270, 90, 181, mode: 8)
        var cursor = WindowTextLayout.State(left: 135, right: 270, bottom: 181, x: 137, y: 100)
        for message in messages {
            let layout = try WindowTextLayout.plan(bytes: message, state: cursor)
            for g in layout.glyphs {
                let value = Int(g.character)
                try GlyphCompositor.draw(glyph: Array(font[value * 8..<(value + 1) * 8]), page: &page,
                    x: g.x, baseline: g.y, maskLow: 63, maskHigh: 0)
            }
            cursor = layout.state
        }
        return page
    }
    /// P25/P9 button visuals. Hit tests use x139...266 and y(top-2)...(bottom+2).
    public static func composeChoices(background: [UInt8], font: [UInt8], messages: [[UInt8]],
                                      labels: [[UInt8]], cursorX: Int? = nil, cursorY: Int? = nil) throws -> [UInt8] {
        guard labels.count <= 3, labels.allSatisfy({ $0.count <= 15 && $0.allSatisfy({ $0 < 128 }) }) else {
            throw Failure.invalidMessages
        }
        var page = try compose(background: background, font: font, messages: messages)
        for (index, label) in labels.enumerated() {
            let top = 139 + index * 15, bottom = top + 10
            rectangle(&page, 137, 268, top - 2, bottom + 2, mode: 10)
            rectangle(&page, 139, 266, top, bottom, mode: 8)
            var x = 139 + (128 - 6 * label.count) / 2
            let baseline = 148 + index * 15
            for c in label {
                let start = Int(c) * 8
                x = try GlyphCompositor.draw(glyph: Array(font[start..<start + 8]), page: &page,
                    x: x, baseline: baseline, maskLow: 63, maskHigh: 0)
            }
        }
        if let cursorX, let cursorY { page = try pointer(on: page, font: font, x: cursorX, y: cursorY) }
        return page
    }
    /// Original P41 selected cursor: XOR glyph1 at (x-3,y+3). Starting from a
    /// pointer-free page avoids XOR trails when the host pointer moves.
    public static func pointer(on background: [UInt8], font: [UInt8], x: Int, y: Int) throws -> [UInt8] {
        guard background.count == 8192 else { throw Failure.invalidPage }
        guard font.count == 1024 else { throw Failure.invalidFont }
        var page = background
        try GlyphCompositor.draw(glyph: Array(font[8..<16]), page: &page, x: x - 3,
            baseline: y + 3, maskLow: 0, maskHigh: 0)
        return page
    }
}
