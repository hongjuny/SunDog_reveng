import SunDogLogic

/// Preview-only macOS event sampling policy, separate from original game timing.
public struct HostButtonBridge {
    public enum Failure: Error { case invalidChannel }
    private var samples: [UInt8] = [0, 0]
    private var filter = ButtonInput()
    public init() {}

    public mutating func set(channel: Int, down: Bool) throws -> [Bool] {
        guard (0..<2).contains(channel) else { throw Failure.invalidChannel }
        samples[channel] = down ? 0x80 : 0
        filter.latch(first: samples[0], second: samples[1])
        // Poll both channels: otherwise a held other button could leave a stale
        // pending press that masks a later release in the event-driven preview.
        return try (0..<2).map { try filter.poll(selector: UInt8($0), sample: samples[$0]).value }
    }
}
