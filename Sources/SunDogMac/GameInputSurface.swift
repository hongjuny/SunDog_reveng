import AppKit
import SwiftUI

/// Host bindings for the two original button samples and original menu hit boxes.
@MainActor struct GameInputSurface: NSViewRepresentable {
    var button: (Int,Bool,Double,Double)->Void
    var activate: ()->Void
    var choice: (Int)->Void
    func makeNSView(context:Context)->Surface {
        let view=Surface();updateNSView(view,context:context);return view
    }
    func updateNSView(_ view:Surface,context:Context) {
        view.button=button;view.activate=activate;view.choice=choice
    }
    final class Surface:NSView {
        var button:((Int,Bool,Double,Double)->Void)?
        var activate:(()->Void)?
        var choice:((Int)->Void)?
        override var acceptsFirstResponder:Bool {true}
        override func viewDidMoveToWindow() { window?.makeFirstResponder(self) }
        private func send(_ event:NSEvent,_ channel:Int,_ down:Bool) {
            let p=convert(event.locationInWindow,from:nil)
            let x=Double(p.x/max(bounds.width,1))*280
            let y=Double(1-p.y/max(bounds.height,1))*192
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
        override func resignFirstResponder()->Bool {button?(0,false,0,0);button?(1,false,0,0);return true}
    }
}
