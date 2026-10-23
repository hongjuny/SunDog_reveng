import Foundation

@main struct VerifyGlyphCompositor {
    struct Fixture: Decodable {
        let glyph: [UInt8]
        let x: Int
        let baseline: Int
        let maskLow: UInt8
        let maskHigh: UInt8
        let initialPage: [UInt8]
        let expectedPage: [UInt8]
        let nextX: Int
    }
    enum Failure: Error { case missingCases, mismatch(Int), invalidInputAccepted }
    static func main() throws {
        guard CommandLine.arguments.count == 2 else { throw Failure.missingCases }
        let fixtures = try JSONDecoder().decode([Fixture].self, from:
            Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
        guard !fixtures.isEmpty else { throw Failure.missingCases }
        for (index, fixture) in fixtures.enumerated() {
            var page = fixture.initialPage
            let next = try GlyphCompositor.draw(glyph: fixture.glyph, page: &page,
                x: fixture.x, baseline: fixture.baseline,
                maskLow: fixture.maskLow, maskHigh: fixture.maskHigh)
            guard next == fixture.nextX, page == fixture.expectedPage else { throw Failure.mismatch(index) }
        }
        // Unsupported coordinates fail before touching the page.
        for (x, baseline) in [(-1, 7), (273, 7), (0, 6), (0, 192)] {
            var page = [UInt8](repeating: 0x80, count: 8192)
            let original = page
            do {
                _ = try GlyphCompositor.draw(glyph: [UInt8](repeating: 0, count: 8),
                                            page: &page, x: x, baseline: baseline)
                throw Failure.invalidInputAccepted
            } catch GlyphCompositor.Failure.outsideVerifiedDomain {}
            guard page == original else { throw Failure.invalidInputAccepted }
        }
        var shortPage = [UInt8](repeating: 0, count: 8191)
        do {
            _ = try GlyphCompositor.draw(glyph: [UInt8](repeating: 0, count: 8), page: &shortPage, x: 0, baseline: 7)
            throw Failure.invalidInputAccepted
        } catch GlyphCompositor.Failure.invalidPageSize {}
        var page = [UInt8](repeating: 0, count: 8192)
        do {
            _ = try GlyphCompositor.draw(glyph: [0], page: &page, x: 0, baseline: 7)
            throw Failure.invalidInputAccepted
        } catch GlyphCompositor.Failure.invalidGlyphSize {}
        print("{\"native_cases\":\(fixtures.count),\"invalid_input_cases\":6,\"all_matched\":true}")
    }
}
