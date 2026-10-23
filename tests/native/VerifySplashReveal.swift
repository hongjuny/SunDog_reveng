import Foundation

private struct ExpectedWrite: Decodable { let offset: Int; let value: UInt8; let cycles: Int }
private struct Fixture: Decodable {
    let source: [UInt8]; let final_page: [UInt8]; let writes: [ExpectedWrite]; let total_cycles: Int
}
@main struct VerifySplashReveal {
    static func main() throws {
        let fixture = try JSONDecoder().decode(Fixture.self,
            from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
        var native = try SplashReveal(source: fixture.source)
        guard native.writes.count == fixture.writes.count else { fatalError("Write count mismatch") }
        for (actual, expected) in zip(native.writes, fixture.writes) {
            guard actual.offset == expected.offset, actual.value == expected.value else { fatalError("Write order mismatch") }
        }
        var checkpoints = 0
        for count in [0, 1, 4, 5, 100, 1000, 4000, 8040, 8041] {
            try native.advance(to: count)
            var expected = [UInt8](repeating: 0, count: 8192)
            for write in fixture.writes.prefix(count) { expected[write.offset] = write.value }
            guard native.page == expected else { fatalError("Partial frame mismatch") }
            checkpoints += 1
        }
        guard native.page == fixture.final_page else { fatalError("Final image mismatch") }
        native.reset()
        guard native.appliedWriteCount == 0, native.page.allSatisfy({ $0 == 0 }) else { fatalError("Reset failed") }
        print("{\"ordered_writes\":\(native.writes.count),\"partial_frames\":\(checkpoints),\"all_matched\":true}")
    }
}
