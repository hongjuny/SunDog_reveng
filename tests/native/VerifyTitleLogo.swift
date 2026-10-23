import Foundation
private struct Write: Decodable { let offset: Int; let value: UInt8 }
private struct Step: Decodable { let glyph: Int; let iteration: Int; let writes: [Write] }
private struct Fixture: Decodable { let background: [UInt8]; let glyphs: [UInt8]; let steps: [Step]; let final_page: [UInt8] }
@main struct VerifyTitleLogo {
    static func main() throws {
        let fixture = try JSONDecoder().decode(Fixture.self, from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
        var title = try TitleLogo(background: fixture.background, glyphs: fixture.glyphs)
        guard title.steps.count == fixture.steps.count else { fatalError("Step count mismatch") }
        var expected = fixture.background
        var writes = 0
        for (index, pair) in zip(title.steps, fixture.steps).enumerated() {
            let (actual, original) = pair
            guard actual.glyph == original.glyph, actual.iteration == original.iteration,
                  actual.writes.count == original.writes.count else { fatalError("Step contract mismatch at \(index)") }
            for (a, b) in zip(actual.writes, original.writes) {
                guard a.offset == b.offset, a.value == b.value else { fatalError("Ordered write mismatch at \(index)") }
                expected[b.offset] = b.value
                writes += 1
            }
            try title.advance(to: index + 1)
            guard title.page == expected else { fatalError("Intermediate page mismatch") }
        }
        guard title.page == fixture.final_page else { fatalError("Final logo mismatch") }
        var rejected = 0
        do { _ = try TitleLogo(background: [], glyphs: fixture.glyphs); fatalError("Bad background accepted") } catch { rejected += 1 }
        do { _ = try TitleLogo(background: fixture.background, glyphs: []); fatalError("Bad glyph resource accepted") } catch { rejected += 1 }
        do { try title.advance(to: 0); fatalError("Rewind accepted") } catch { rejected += 1 }
        print("{\"steps\":\(title.steps.count),\"ordered_writes\":\(writes),\"invalid_inputs\":\(rejected),\"all_matched\":true}")
    }
}
