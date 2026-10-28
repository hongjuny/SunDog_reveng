/// Original Play segment7 P2: one 512-byte unit block and a marker at byte252.
public enum PlayDiskGate {
    public enum Result: Equatable { case accepted, wrongSide, nonlocalExit }
    public enum Failure: Error { case invalidBlock }
    public static func check(block: [UInt8], wantUtility: Bool = false, ioResult: Int16 = 0) throws -> Result {
        guard block.count == 512 else { throw Failure.invalidBlock }
        if ioResult > 0 { return .nonlocalExit }
        return block[252] == (wantUtility ? 0 : 9) ? .accepted : .wrongSide
    }
}
