import SwiftUI
import AppleIIVideo

/// A static 560x192 frame needs no GPU setup. Avoid silently selecting a Metal
/// path just because a device exists; shader/queue/drawable creation can fail.
struct NativeScreen: View {
    let frame: VideoFrame
    var body: some View {
        if let image = try? frame.cgImage() {
            Image(decorative: image, scale: 1)
                .resizable()
                .interpolation(.none)
        } else {
            Text("Could not display the generated frame.")
                .foregroundStyle(.white)
        }
    }
}
