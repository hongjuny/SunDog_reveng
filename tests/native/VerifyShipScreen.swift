import Foundation

private struct Fixture: Decodable { let encoded: [UInt8]; let page: [UInt8]; let consumed: Int }
@main struct VerifyShipScreen {
    static func main() throws {
        let fixtures = try JSONDecoder().decode([Fixture].self,
            from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
        for fixture in fixtures {
            let actual = try ShipScreenDecoder.decode(encoded: fixture.encoded)
            guard actual.page == fixture.page, actual.consumedBytes == fixture.consumed else {
                fatalError("Original native image decoder differs")
            }
        }
        var rejected = 0
        for data: [UInt8] in [[], [0], [1, 0], [1, 0x80]] {
            do { _ = try ShipScreenDecoder.decode(encoded: data); fatalError("Malformed source accepted") }
            catch { rejected += 1 }
        }
        print("{\"native_cases\":\(fixtures.count),\"invalid_sources\":\(rejected),\"all_matched\":true}")
    }
}
