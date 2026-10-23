import Foundation

@main struct VerifyButtonInput {
    struct Filter: Decodable {
        let selector: UInt8
        let sample: UInt8
        let pending: UInt8
        let previous: Bool
        let result: Bool
        let remaining: UInt8
        let history: Bool
    }
    struct Latch: Decodable {
        let first: UInt8
        let second: UInt8
        let pending: [UInt8]
        let expected: [UInt8]
    }
    struct Fixtures: Decodable { let filters: [Filter]; let latches: [Latch] }
    enum Failure: Error { case missingCases, mismatch(Int), unexpectedAcceptance }
    static func main() throws {
        guard CommandLine.arguments.count == 2 else { throw Failure.missingCases }
        let rows = try JSONDecoder().decode(Fixtures.self, from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
        guard rows.filters.count == 512, rows.latches.count == 256 else { throw Failure.missingCases }
        for (index, row) in rows.filters.enumerated() {
            var pending = [UInt8](repeating: 0x17, count: 4)
            var previous = [Bool](repeating: true, count: 4)
            let channel = Int(row.selector & 3)
            pending[channel] = row.pending; previous[channel] = row.previous
            var input = try ButtonInput(pending: pending, previous: previous)
            let result = try input.poll(selector: row.selector, sample: row.sample)
            pending[channel] = row.remaining; previous[channel] = row.history
            guard result.value == row.result, !result.restoreDispatch,
                  input.pending == pending, input.previous == previous else { throw Failure.mismatch(index) }
        }
        for (index, row) in rows.latches.enumerated() {
            var input = try ButtonInput(pending: row.pending, previous: [true, false, true, false])
            input.latch(first: row.first, second: row.second)
            guard input.pending == row.expected, input.previous == [true, false, true, false] else { throw Failure.mismatch(512 + index) }
        }
        var restored = try ButtonInput(pending: [1, 2, 3, 4], previous: [true, false, true, false])
        let result = try restored.poll(selector: 8, sample: 255)
        guard !result.value, result.restoreDispatch, restored.pending == [1, 2, 3, 4],
              restored.previous == [true, false, true, false] else { throw Failure.mismatch(768) }
        for selector in UInt8(9)...UInt8(255) {
            do { _ = try restored.poll(selector: selector, sample: 0); throw Failure.unexpectedAcceptance }
            catch ButtonInput.Failure.unsupportedSelector {}
        }
        do { _ = try ButtonInput(pending: [], previous: []); throw Failure.unexpectedAcceptance }
        catch ButtonInput.Failure.invalidChannelCount {}
        print("{\"filter_cases\":512,\"latch_cases\":256,\"restore_cases\":1,\"invalid_selectors_rejected\":247}")
    }
}
