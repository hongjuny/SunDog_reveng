/// Reconstructed segment21 P21 / P40 byte-map selection. Names distinguish the
/// portable call contract from original frame slot numbers; they do not establish
/// the gameplay meaning of every map value.
public enum TileSelection {
    public enum Failure: Error, Equatable { case invalidMapSize, divisionByZero }
    public struct Result: Equatable, Sendable {
        public let column: Int
        public let row: Int
        public let value: UInt8
        /// P40 follows its byte read with magnitude remainder16; P21 retains value.
        public var selectionNibble: UInt8 { value & 15 }
    }
    public static func lookup(map: [UInt8], originX: Int16, originY: Int16,
                              cursorX: Int16, cursorY: Int16, verticalDivisor: Int16) throws -> Result {
        guard map.count == 960 else { throw Failure.invalidMapSize }
        guard verticalDivisor != 0 else { throw Failure.divisionByZero }
        func wrap(_ value: Int32) -> Int16 { Int16(truncatingIfNeeded: value) }
        func divide(_ value: Int16, _ divisor: Int16) -> Int16 {
            wrap(Int32(value) / Int32(divisor))
        }
        let xStep = divide(wrap(Int32(cursorX) + 3), 28)
        let yStep = divide(wrap(Int32(cursorY) - 3), verticalDivisor)
        // Original 8E is remainder of operand magnitudes, not Swift signed %.
        let column = Int(abs(Int32(wrap(Int32(originX) + Int32(xStep)))) % 40)
        let row = Int(abs(Int32(wrap(Int32(originY) + Int32(yStep)))) % 24)
        return Result(column: column, row: row, value: map[row * 40 + column])
    }
}
