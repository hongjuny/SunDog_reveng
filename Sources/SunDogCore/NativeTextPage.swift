import Foundation
import AppleIIVideo
import SunDogLogic

/// Reconstructed P48/P47/P45 placement followed by the verified normal P9 body.
/// The selected preview window is host policy. P44 scrolling and P12 lines are
/// explicit unsupported boundaries, never replaced with made-up game behavior.
public enum NativeTextPage {
    public enum Failure: Error, LocalizedError {
        case invalidFont, unsupportedText, unsupportedLayout(String)
        public var errorDescription: String? {
            switch self {
            case .invalidFont: "The font must contain 128 eight-byte glyphs (1,024 bytes)."
            case .unsupportedText: "Use character codes 0–127; Unicode mapping is not reconstructed."
            case .unsupportedLayout(let description): description
            }
        }
    }

    public static func compose(text: String, font: [UInt8]) throws -> [UInt8] {
        guard font.count == 1024 else { throw Failure.invalidFont }
        guard text.unicodeScalars.allSatisfy({ $0.value < 128 }) else { throw Failure.unsupportedText }
        var page = [UInt8](repeating: 0, count: 8192)
        let layout: WindowTextLayout.Result
        do {
            layout = try WindowTextLayout.plan(bytes: Array(text.utf8), state:
                .init(left: 5, right: 272, bottom: 191, x: 7, y: 15))
        } catch WindowTextLayout.Failure.stringCapacityExceeded {
            throw Failure.unsupportedLayout("Original P48 strings have a capacity of 80 bytes.")
        } catch WindowTextLayout.Failure.unsupportedLongWord {
            throw Failure.unsupportedLayout("Words longer than 20 bytes are outside the verified scratch-buffer contract.")
        } catch WindowTextLayout.Failure.requiresBottomHandler {
            throw Failure.unsupportedLayout("This text reaches the original scrolling handler, which is not yet ported.")
        }
        for position in layout.glyphs {
            let value = Int(position.character)
            let glyph = Array(font[value * 8 ..< (value + 1) * 8])
            _ = try GlyphCompositor.draw(glyph: glyph, page: &page, x: position.x, baseline: position.y,
                                         maskLow: 0x3f, maskHigh: 0)
        }
        return page
    }
}
