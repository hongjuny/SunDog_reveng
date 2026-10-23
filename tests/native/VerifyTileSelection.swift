import Foundation
@main struct VerifyTileSelection {
    struct Case: Decodable {
        let originX: Int16; let originY: Int16; let cursorX: Int16; let cursorY: Int16
        let verticalDivisor: Int16; let column: Int; let row: Int; let value: UInt8
    }
    struct Cases: Decodable { let map: [UInt8]; let cases: [Case] }
    enum Failure: Error { case mismatch(Int), expectedFailure }
    static func main() throws {
        guard CommandLine.arguments.count == 2 else { throw Failure.expectedFailure }
        let input = try JSONDecoder().decode(Cases.self, from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
        guard !input.cases.isEmpty else { throw Failure.expectedFailure }
        for (i,c) in input.cases.enumerated() {
            let actual = try TileSelection.lookup(map: input.map, originX: c.originX, originY: c.originY,
                cursorX: c.cursorX, cursorY: c.cursorY, verticalDivisor: c.verticalDivisor)
            if actual.column != c.column || actual.row != c.row || actual.value != c.value || actual.selectionNibble != c.value & 15 {
                throw Failure.mismatch(i)
            }
        }
        do {
            _ = try TileSelection.lookup(map: [], originX: 0, originY: 0, cursorX: 0, cursorY: 0, verticalDivisor: 1)
            throw Failure.expectedFailure
        } catch TileSelection.Failure.invalidMapSize {}
        do {
            _ = try TileSelection.lookup(map: input.map, originX: 0, originY: 0, cursorX: 0, cursorY: 0, verticalDivisor: 0)
            throw Failure.expectedFailure
        } catch TileSelection.Failure.divisionByZero {}
        print("{\"native_cases\":\(input.cases.count),\"invalid_input_cases\":2,\"all_matched\":true}")
    }
}
