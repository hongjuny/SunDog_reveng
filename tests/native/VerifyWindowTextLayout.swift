import Foundation

private struct Placement: Decodable { let character: UInt8; let x: Int; let y: Int }
private struct Expected: Decodable { let placements: [Placement]; let x: Int; let y: Int; let mask: Int; let mode: Int; let boundary: String? }
private struct Fixture: Decodable {
    let text: String; let left: Int; let right: Int; let bottom: Int; let x: Int; let y: Int
    let expected: Expected
}

@main struct VerifyWindowTextLayout {
    static func main() throws {
        let cases = try JSONDecoder().decode([Fixture].self,
            from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
        var matched = 0
        var stopped = 0
        for item in cases {
            let state = WindowTextLayout.State(left: item.left, right: item.right,
                                               bottom: item.bottom, x: item.x, y: item.y)
            do {
                let actual = try WindowTextLayout.plan(bytes: Array(item.text.utf8), state: state)
                let expected = item.expected
                guard expected.boundary == nil,
                      expected.mode == 3, expected.mask == 63,
                      actual.state.x == expected.x, actual.state.y == expected.y,
                      actual.glyphs.count == expected.placements.count else { fatalError("Layout summary mismatch: \(item.text)") }
                for (a, e) in zip(actual.glyphs, expected.placements) {
                    guard a.character == e.character, a.x == e.x, a.y == e.y else { fatalError("Glyph placement mismatch") }
                }
                matched += 1
            } catch WindowTextLayout.Failure.requiresBottomHandler {
                guard item.expected.boundary == "bottom_P44" else { fatalError("Unexpected bottom boundary") }
                stopped += 1
            }
        }
        let initial = WindowTextLayout.State(left: 0, right: 272, bottom: 191, x: 2, y: 15)
        var rejected = 0
        let invalid: [[UInt8]] = [[UInt8](repeating: 65, count: 81), [UInt8](repeating: 65, count: 21), [128]]
        for bytes in invalid {
            do { _ = try WindowTextLayout.plan(bytes: bytes, state: initial); fatalError("Invalid input accepted") }
            catch { rejected += 1 }
        }
        let report: [String: Any] = ["cfg_cases": matched, "bottom_boundaries": stopped,
                                     "invalid_input_cases": rejected, "all_matched": true]
        print(String(decoding: try JSONSerialization.data(withJSONObject: report, options: .sortedKeys), as: UTF8.self))
    }
}
