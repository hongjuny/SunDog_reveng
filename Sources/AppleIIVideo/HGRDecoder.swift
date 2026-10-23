import Foundation

public enum VideoError: Error, LocalizedError {
    case invalidPageSize(Int)
    case unsupportedMode(String)
    public var errorDescription: String? {
        switch self {
        case .invalidPageSize(let size): "HGR requires an 8,192-byte page; received \(size)."
        case .unsupportedMode(let mode): "This viewer does not yet decode \(mode)."
        }
    }
}

public struct VideoFrame: Sendable {
    public let width: Int
    public let height: Int
    public let rgba: [UInt8]
    public let preset: String
}

/// Explicit reference profile, not a claim of signal-accurate NTSC decoding.
/// The a2m 3-bit window/palette method is public-domain source, pinned in
/// THIRD_PARTY.md. SunDog's row addresses are independently verified native data.
public enum HGRDecoder {
    public static let preset = "a2m-hgr-colour-v1"
    public static let width = 560
    public static let height = 192
    private static let palette: [UInt32] = [
        0x000000,0x000000,0xc734ff,0xffffff,
        0x000000,0x38cb00,0xffffff,0xffffff,
        0x000000,0x000000,0x0da1ff,0xffffff,
        0x000000,0xf25e00,0xffffff,0xffffff
    ]

    public static func rowOffset(_ row: Int) -> Int {
        precondition((0..<height).contains(row))
        return (row & 7) * 0x400 + ((row >> 3) & 7) * 0x80 + (row >> 6) * 40
    }

    public static func decode(page: [UInt8]) throws -> VideoFrame {
        guard page.count == 8192 else { throw VideoError.invalidPageSize(page.count) }
        var rgba = [UInt8](repeating: 0, count: width * height * 4)
        for row in 0..<height {
            let base = rowOffset(row)
            for column in 0..<40 {
                let byte = Int(page[base + column])
                let previous = column == 0 ? 0 : Int(page[base + column - 1] >> 6) & 1
                let following = column == 39 ? 0 : Int(page[base + column + 1]) & 1
                var window = (following << 8) | ((byte & 127) << 1) | previous
                let phase = (byte >> 7) * 8
                for bit in 0..<7 {
                    var index = window & 7
                    if (column + bit) & 1 == 1 && (index == 2 || index == 5) { index ^= 7 }
                    let color = palette[index + phase]
                    for sample in 0..<2 {
                        let p = (row * width + column * 14 + bit * 2 + sample) * 4
                        rgba[p] = UInt8(truncatingIfNeeded: color >> 16)
                        rgba[p + 1] = UInt8(truncatingIfNeeded: color >> 8)
                        rgba[p + 2] = UInt8(truncatingIfNeeded: color)
                        rgba[p + 3] = 255
                    }
                    window >>= 1
                }
            }
        }
        return VideoFrame(width: width, height: height, rgba: rgba, preset: preset)
    }
}
