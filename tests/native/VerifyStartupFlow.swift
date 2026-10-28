import Foundation
private struct Case: Decodable {
    let mode: StartupFlow.Mode
    let profile: StartupFlow.Profile
    let choices: [Int]
    let newGame: Bool
}
private struct Gate: Decodable { let remaining: Int16; let first: Bool; let second: Bool; let next: Int16; let finished: Bool }
private struct Route: Decodable { let mode: StartupFlow.Mode; let choice: Int; let destination: String; let template: Int?; let skip: Bool }
private struct Fixture: Decodable { let profiles: [Case]; let gates: [Gate]; let routes: [Route] }
@main struct VerifyStartupFlow {
    static func main() throws {
        let fixture=try JSONDecoder().decode(Fixture.self,from:Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[1])))
        var count=0
        for item in fixture.profiles {
            let flow=StartupFlow(mode:item.mode,profile:item.profile)
            guard flow.choices.map({$0.rawValue})==item.choices,
                  flow.profile.newGame==item.newGame,
                  flow.stage==(item.profile.skipIntro ? .transitionReady : .awaitingBegin) else { fatalError("Profile mismatch") }
            if item.profile.skipIntro {
                guard flow.selectedRoute?.destination.rawValue==item.mode.rawValue else { fatalError("Skip route mismatch") }
            }
            count+=1
        }
        let profile=StartupFlow.Profile(skipIntro:false,slotIndex:1,stateWord:0,word42:0,word43:0,damaged:false)
        var timeout=StartupFlow(mode:.utility,profile:profile)
        for index in 1...11400 {
            let done=try timeout.poll(first:0,second:0)
            guard done==(index==11400),timeout.remainingIterations==Int16(11400-index) else { fatalError("Timeout mismatch") }
        }
        var edges=0
        for channel in 0...1 {
            var flow=StartupFlow(mode:.utility,profile:profile)
            guard try !flow.poll(first:0x7f,second:0x7f) else { fatalError("Low-bit sample became press") }
            guard try flow.poll(first:channel==0 ? 0x80 : 0,second:channel==1 ? 0x80 : 0),flow.stage == .choosingMode else {
                fatalError("Channel press failed")
            }
            edges+=1
        }
        for item in fixture.routes {
            var flow=StartupFlow(mode:item.mode,profile:profile)
            _=try flow.poll(first:0x80,second:0)
            let actual=try flow.select(StartupFlow.Choice(rawValue:item.choice)!)
            guard actual.destination.rawValue==item.destination,actual.originalDirectoryTemplate==item.template,
                  actual.skipLogoOnOriginalRestart==item.skip,flow.stage == .transitionReady else { fatalError("Choice route mismatch") }
        }
        let blocked=StartupFlow.Profile(skipIntro:false,slotIndex:4,stateWord:0,word42:0,word43:0,damaged:false)
        var flow=StartupFlow(mode:.utility,profile:blocked)
        _=try flow.poll(first:0x80,second:0)
        var rejected=0
        do {_=try flow.select(.play);fatalError("Disabled Play accepted")} catch {rejected+=1}
        do {_=try flow.poll(first:0,second:0);fatalError("Wrong-stage polling accepted")} catch {rejected+=1}
        print("{\"profiles\":\(count),\"timeout_polls\":11400,\"edge_channels\":\(edges),\"choice_routes\":\(fixture.routes.count),\"invalid_actions\":\(rejected),\"all_matched\":true}")
    }
}
