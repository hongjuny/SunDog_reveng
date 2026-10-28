import AppKit
import SwiftUI

/// Host bindings for the two original button samples and original menu hit boxes.
@MainActor struct GameInputSurface: NSViewRepresentable {
    var button: (Int,Bool,Double,Double)->Void
    var pointer: (Double,Double)->Void
    var cancel: ()->Void
    var activate: ()->Void
    var choice: (Int)->Void
    func makeNSView(context:Context)->Surface {
        let view=Surface();updateNSView(view,context:context);return view
    }
    func updateNSView(_ view:Surface,context:Context) {
        view.button=button;view.activate=activate;view.choice=choice;view.pointer=pointer;view.cancel=cancel
    }
    final class Surface:NSView {
        var button:((Int,Bool,Double,Double)->Void)?
        var pointer:((Double,Double)->Void)?
        var cancel:(()->Void)?
        private var tracking:NSTrackingArea?
        override func updateTrackingAreas() {
            super.updateTrackingAreas()
            if let tracking { removeTrackingArea(tracking) }
            let area=NSTrackingArea(rect:.zero,options:[.mouseMoved,.activeInKeyWindow,.inVisibleRect],owner:self,userInfo:nil)
            addTrackingArea(area);tracking=area
        }
        var activate:(()->Void)?
        var choice:((Int)->Void)?
        override var acceptsFirstResponder:Bool {true}
        override func viewDidMoveToWindow() {
            window?.acceptsMouseMovedEvents=true
            window?.makeFirstResponder(self)
        }
        private func track(_ event:NSEvent) {
            let p=convert(event.locationInWindow,from:nil)
            pointer?(Double(p.x/max(bounds.width,1))*280,Double(1-p.y/max(bounds.height,1))*192)
        }
        override func mouseMoved(with e:NSEvent) {track(e)}
        override func mouseDragged(with e:NSEvent) {track(e)}
        override func rightMouseDragged(with e:NSEvent) {track(e)}
        private func send(_ event:NSEvent,_ channel:Int,_ down:Bool) {
            let p=convert(event.locationInWindow,from:nil)
            let x=Double(p.x/max(bounds.width,1))*280
            let y=Double(1-p.y/max(bounds.height,1))*192
            pointer?(x,y)
            button?(channel,down,x,y)
        }
        override func mouseDown(with e:NSEvent) {window?.makeFirstResponder(self);send(e,0,true)}
        override func mouseUp(with e:NSEvent) {send(e,0,false)}
        override func rightMouseDown(with e:NSEvent) {window?.makeFirstResponder(self);send(e,1,true)}
        override func rightMouseUp(with e:NSEvent) {send(e,1,false)}
        override func keyDown(with e:NSEvent) {
            guard !e.isARepeat else{return}
            if e.keyCode==49 || e.keyCode==36 || e.keyCode==76 {activate?()}
            else if let text=e.charactersIgnoringModifiers,let number=Int(text),(1...3).contains(number) {choice?(number)}
        }
        override func keyUp(with e:NSEvent) {
            if e.keyCode==49 || e.keyCode==36 || e.keyCode==76 {button?(0,false,0,0)}
        }
        override func resignFirstResponder()->Bool {cancel?();return true}
    }
}
