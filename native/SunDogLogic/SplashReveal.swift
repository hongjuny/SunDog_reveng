/// Reconstructed native $4000 title reveal. Each item is one ordered HGR byte
/// write; repeated corner writes are retained. No 6502 code runs in this type.
public struct SplashReveal: Sendable {
    public enum Failure: Error { case invalidPage, invalidProgress }
    public struct Write: Equatable, Sendable {
        public let offset: Int
        public let value: UInt8
    }
    public let writes: [Write]
    public private(set) var page = [UInt8](repeating: 0, count: 8192)
    public private(set) var appliedWriteCount = 0

    public init(source: [UInt8]) throws {
        guard source.count == 8192 else { throw Failure.invalidPage }
        var result: [Write] = []
        func put(_ row: Int, _ column: Int) {
            let offset = (row & 7) * 1024 + ((row >> 3) & 7) * 128 + (row >> 6) * 40 + column
            result.append(Write(offset: offset, value: source[offset]))
        }
        put(95, 19); put(95, 20); put(96, 19); put(96, 20)
        for iteration in 0..<19 {
            let left = 18 - iteration, right = 21 + iteration
            let top = 90 - 5 * iteration, bottom = 101 + 5 * iteration
            for column in left...right {
                for row in top..<(top + 5) { put(row, column) }
            }
            for row in top...bottom { put(row, right) }
            for column in stride(from: right, through: left, by: -1) {
                for row in stride(from: bottom, through: bottom - 4, by: -1) { put(row, column) }
            }
            for row in stride(from: bottom, through: top + 1, by: -1) { put(row, left) }
        }
        writes = result
    }

    public mutating func advance(to count: Int) throws {
        guard count >= appliedWriteCount, count <= writes.count else { throw Failure.invalidProgress }
        for index in appliedWriteCount..<count {
            let write = writes[index]
            page[write.offset] = write.value
        }
        appliedWriteCount = count
    }
    public mutating func reset() {
        page = [UInt8](repeating: 0, count: 8192)
        appliedWriteCount = 0
    }
}
