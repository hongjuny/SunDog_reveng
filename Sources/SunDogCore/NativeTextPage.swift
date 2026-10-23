import Foundation
import AppleIIVideo
import SunDogLogic

/// Host-side layout around the verified normal glyph body. Wrapping and line
/// placement here are preview choices, not reconstructed Pascal window rules.
public enum NativeTextPage {
    public enum Failure: Error, LocalizedError {
        case invalidFont, unsupportedText
        public var errorDescription: String? {
            switch self {
            case .invalidFont: "The font must contain 128 eight-byte glyphs (1,024 bytes)."
            case .unsupportedText: "Use character codes 0–127; Unicode mapping is not reconstructed."
            }
        }
    }

    public static func compose(text: String, font: [UInt8]) throws -> [UInt8] {
        guard font.count == 1024 else { throw Failure.invalidFont }
        guard text.unicodeScalars.allSatisfy({ $0.value < 128 }) else { throw Failure.unsupportedText }
        var page = [UInt8](repeating: 0, count: 8192)
        var x = 7
        var baseline = 15
        for value in text.utf8 {
            if value == 10 { x = 7; baseline += 8; continue }
            if x > 266 { x = 7; baseline += 8 }
            guard baseline <= 191 else { break }
            let glyph = Array(font[Int(value) * 8 ..< Int(value + 1) * 8])
            x = try GlyphCompositor.draw(glyph: glyph, page: &page, x: x, baseline: baseline)
        }
        return page
    }
}
