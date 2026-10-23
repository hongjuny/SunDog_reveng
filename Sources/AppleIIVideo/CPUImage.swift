import Foundation
import CoreGraphics

public extension VideoFrame {
    func cgImage() throws -> CGImage {
        guard let provider = CGDataProvider(data: Data(rgba) as CFData),
              let space = CGColorSpace(name: CGColorSpace.sRGB),
              let image = CGImage(width: width, height: height, bitsPerComponent: 8,
                bitsPerPixel: 32, bytesPerRow: width * 4, space: space,
                bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.last.rawValue).union(.byteOrder32Big),
                provider: provider, decode: nil, shouldInterpolate: false, intent: .defaultIntent) else {
            throw CaptureErrorForImage.invalid
        }
        return image
    }
}

private enum CaptureErrorForImage: Error { case invalid }
