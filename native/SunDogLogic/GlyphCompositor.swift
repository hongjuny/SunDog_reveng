/// Reconstructed normal drawing body of SYSTEM.LIBRARY segment 22, native P9.
/// The eight font rows are stored bottom first. This API intentionally excludes
/// the unverified caller clipping and mode-2 query paths.
public enum GlyphCompositor {
    public enum Failure: Error, Equatable {
        case invalidPageSize
        case invalidGlyphSize
        case outsideVerifiedDomain
    }

    /// Draw one eight-row glyph into an Apple II HGR page and return next x.
    /// Both destination bytes must exist; clipping is the caller's responsibility.
    @discardableResult
    public static func draw(
        glyph: [UInt8], page: inout [UInt8], x: Int, baseline: Int,
        maskLow: UInt8 = 0x3f, maskHigh: UInt8 = 0
    ) throws -> Int {
        guard page.count == 8192 else { throw Failure.invalidPageSize }
        guard glyph.count == 8 else { throw Failure.invalidGlyphSize }
        guard (0...272).contains(x), (7...191).contains(baseline) else {
            throw Failure.outsideVerifiedDomain
        }
        let column = x / 7
        let shift = x % 7
        for row in 0..<8 {
            let y = baseline - 7 + row
            let offset = (y & 7) * 0x400 + ((y >> 3) & 7) * 0x80 + (y >> 6) * 40 + column
            let bits = Int(glyph[7 - row] & 0x7f)
            if bits | Int(maskLow) == 0 { continue }
            let lowBits = (bits << shift) & 0x7f
            let highBits = shift == 0 ? 0 : bits >> (7 - shift)
            let lowMask = (Int(maskLow) << shift) & 0x7f
            let highMask = ((Int(maskHigh) << shift) |
                            (shift == 0 ? 0 : Int(maskLow & 0x7f) >> (7 - shift))) & 0x7f
            page[offset] = UInt8((Int(page[offset]) & (0x80 | (~lowMask & 0x7f))) ^ lowBits)
            page[offset + 1] = UInt8((Int(page[offset + 1]) & (0x80 | (~highMask & 0x7f))) ^ highBits)
        }
        return x + 6
    }
}
