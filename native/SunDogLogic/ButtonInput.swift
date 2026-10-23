/// Reconstructed segment 22 / native procedure 2 input state.
/// Samples are bytes supplied by the host; no device mapping or timing is implied.
public struct ButtonInput: Sendable {
    public enum Failure: Error { case invalidChannelCount, unsupportedSelector }
    public struct PollResult: Sendable, Equatable {
        public let value: Bool
        /// Selector 8 restores the original interpreter dispatch pointer.
        /// A native host receives this signal without patching any machine code.
        public let restoreDispatch: Bool
    }

    public private(set) var pending: [UInt8]
    public private(set) var previous: [Bool]

    public init() {
        pending = [UInt8](repeating: 0, count: 4)
        previous = [Bool](repeating: false, count: 4)
    }

    public init(pending: [UInt8], previous: [Bool]) throws {
        guard pending.count == 4, previous.count == 4 else { throw Failure.invalidChannelCount }
        self.pending = pending
        self.previous = previous
    }

    /// The original ADD16 hook latches exactly the first two raw channels.
    public mutating func latch(first: UInt8, second: UInt8) {
        pending[0] |= first
        pending[1] |= second
    }

    /// 0...3: rising edge; 4...7: level without updating edge history.
    /// Exactly 8: false plus restore signal. Other selectors are unverified.
    public mutating func poll(selector: UInt8, sample: UInt8) throws -> PollResult {
        guard selector <= 8 else { throw Failure.unsupportedSelector }
        if selector == 8 { return PollResult(value: false, restoreDispatch: true) }
        let channel = Int(selector & 3)
        let down = ((sample | pending[channel]) & 0x80) != 0
        if down { pending[channel] = 0 }
        if selector & 4 != 0 {
            return PollResult(value: down, restoreDispatch: false)
        }
        let edge = down && !previous[channel]
        previous[channel] = down
        return PollResult(value: edge, restoreDispatch: false)
    }
}
