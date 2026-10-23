import Foundation

/// Original routine CPU-cycle schedule; physical display refresh and the chosen
/// nominal host clock remain separate from byte-order equivalence.
public struct SplashTimeline: Sendable {
    public let writeCycles: [Int]
    public let totalCycles: Int
    public static let nominalCPUHz = 1_023_000.0
    private struct Metadata: Decodable {
        let write_cycles: [Int]
        let total_cycles: Int
    }
    public enum Failure: Error { case invalidSchedule }
    public static func load(url: URL) throws -> SplashTimeline {
        let data = try JSONDecoder().decode(Metadata.self, from: Data(contentsOf: url))
        guard data.write_cycles.count == 8041, data.total_cycles == 515593,
              (data.write_cycles.first ?? 0) > 0,
              (data.write_cycles.last ?? Int.max) <= data.total_cycles,
              zip(data.write_cycles, data.write_cycles.dropFirst()).allSatisfy({ $0 < $1 }) else {
            throw Failure.invalidSchedule
        }
        return SplashTimeline(writeCycles: data.write_cycles, totalCycles: data.total_cycles)
    }
    public func writeCount(atCycle cycle: Int) -> Int {
        var low = 0, high = writeCycles.count
        while low < high {
            let middle = (low + high) / 2
            if writeCycles[middle] <= cycle { low = middle + 1 }
            else { high = middle }
        }
        return low
    }
    public func writeCount(at elapsed: TimeInterval) -> Int {
        guard elapsed > 0 else { return 0 }
        let cycles = elapsed * Self.nominalCPUHz
        var low = 0, high = writeCycles.count
        while low < high {
            let middle = (low + high) / 2
            if Double(writeCycles[middle]) <= cycles { low = middle + 1 }
            else { high = middle }
        }
        return low
    }
}
