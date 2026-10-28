/// Reconstructed SYSTEM.LIBRARY segment24 native P5 image expansion.
/// The source is a bounded original resource, not executable game code.
public enum ShipScreenDecoder {
    public enum Failure: Error { case truncatedSource, invalidStride }
    public struct Result: Sendable {
        public let page: [UInt8]
        public let consumedBytes: Int
    }
    public static func decode(encoded: [UInt8]) throws -> Result {
        guard let first = encoded.first else { throw Failure.truncatedSource }
        let stride = Int(first)
        guard stride > 0 else { throw Failure.invalidStride }
        var page = [UInt8](repeating: 0, count: 8192)
        var source = 1
        func next() throws -> UInt8 {
            guard source < encoded.count else { throw Failure.truncatedSource }
            defer { source += 1 }
            return encoded[source]
        }
        for column in 0..<stride {
            var destination = column
            while destination < 8192 {
                let token = try next()
                let count = Int(token & 0x7f) + 1
                if token & 0x80 == 0 {
                    let value = try next()
                    for _ in 0..<count {
                        page[destination] = value
                        destination += stride
                        if destination >= 8192 { break }
                    }
                } else {
                    for _ in 0..<count {
                        page[destination] = try next()
                        destination += stride
                        if destination >= 8192 { break }
                    }
                }
            }
        }
        return Result(page: page, consumedBytes: source)
    }
}
