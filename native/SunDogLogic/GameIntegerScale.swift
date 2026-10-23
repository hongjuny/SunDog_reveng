/// Reconstructed from Apple II game segment 20, procedure 18.
/// This contract covers the verified nonnegative domain only.
/// Preserve the original order, signed 16-bit wrapping and integer truncation.
public enum GameIntegerScale {
    public enum Failure: Error { case divisionByZero, outsideVerifiedDomain }
    public static func apply(x: Int16, y: Int16, divisor: Int16) throws -> Int16 {
        guard x != 0, divisor != 0 else { throw Failure.divisionByZero }
        guard x > 0, y >= 0, divisor > 0 else { throw Failure.outsideVerifiedDomain }
        let a=Int32(x), b=Int32(y), d=Int32(divisor)
        if 32767/a <= b {
            return Int16(truncatingIfNeeded: a*(b/d))
        }
        let product=Int16(truncatingIfNeeded:a*b)
        return Int16(truncatingIfNeeded:Int32(product)/d)
    }
}
