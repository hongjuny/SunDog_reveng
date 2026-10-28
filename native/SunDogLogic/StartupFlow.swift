/// Source-specific segment26 P6 begin gate and mode selection.
/// This models the original decisions without modifying or rebooting game media.
public struct StartupFlow: Sendable {
    public enum Mode: String, Codable, Sendable { case utility, play }
    public enum Choice: Int, Codable, Sendable, CaseIterable {
        case useUtilities = 1, play = 2, demo = 3
    }
    public enum Stage: String, Codable, Sendable { case awaitingBegin, choosingMode, transitionReady }
    public enum Destination: String, Codable, Sendable { case utility, play, demo }
    public struct Profile: Codable, Sendable {
        public let skipIntro: Bool
        public let slotIndex: UInt8
        public let stateWord: UInt16
        public let word42: UInt16
        public let word43: UInt16
        public let damaged: Bool
        public init(skipIntro: Bool, slotIndex: UInt8, stateWord: UInt16, word42: UInt16, word43: UInt16, damaged: Bool) {
            self.skipIntro = skipIntro; self.slotIndex = slotIndex; self.stateWord = stateWord
            self.word42 = word42; self.word43 = word43; self.damaged = damaged
        }
        public var state: UInt16 { (stateWord >> 8) & 15 }
        public var playAllowed: Bool { state != 12 && state != 13 && !damaged && slotIndex < 4 }
        public var newGame: Bool { word43 & 0x3fff == 0 && word42 >> 8 == 0 && word42 & 0x3f == 0 }
    }
    public struct Route: Equatable, Sendable {
        public let destination: Destination
        /// A description of the original disk action, not an instruction to write.
        public let originalDirectoryTemplate: Int?
        public let skipLogoOnOriginalRestart: Bool
    }
    public enum Failure: Error { case wrongStage, unavailableChoice }
    public let mode: Mode
    public let profile: Profile
    public private(set) var stage: Stage
    public private(set) var selectedRoute: Route?
    public private(set) var remainingIterations: Int16 = 11400
    private var buttons = ButtonInput()
    public init(mode: Mode, profile: Profile) {
        self.mode = mode; self.profile = profile
        stage = profile.skipIntro ? .transitionReady : .awaitingBegin
        selectedRoute = profile.skipIntro
            ? Route(destination: mode == .play ? .play : .utility,
                    originalDirectoryTemplate: nil, skipLogoOnOriginalRestart: false)
            : nil
    }
    public var choices: [Choice] {
        (profile.playAllowed ? [.play] : []) + [.useUtilities, .demo]
    }
    /// One original logical polling iteration. The host chooses when to sample;
    /// 11,400 iterations have no inferred wall-clock duration here.
    @discardableResult public mutating func poll(first: UInt8, second: UInt8) throws -> Bool {
        guard stage == .awaitingBegin else { throw Failure.wrongStage }
        buttons.latch(first: first, second: second)
        let firstEdge = try buttons.poll(selector: 0, sample: first).value
        let secondEdge = try buttons.poll(selector: 1, sample: second).value
        remainingIterations = remainingIterations &- 1
        let finished = firstEdge || secondEdge || remainingIterations <= 0
        if finished { stage = .choosingMode }
        return finished
    }
    public mutating func select(_ choice: Choice) throws -> Route {
        guard stage == .choosingMode else { throw Failure.wrongStage }
        guard choices.contains(choice) else { throw Failure.unavailableChoice }
        let route: Route
        if choice == .demo {
            route = Route(destination: .demo, originalDirectoryTemplate: 82, skipLogoOnOriginalRestart: false)
        } else if mode == .utility && choice == .play {
            route = Route(destination: .play, originalDirectoryTemplate: 80, skipLogoOnOriginalRestart: true)
        } else if mode == .play && choice == .useUtilities {
            route = Route(destination: .utility, originalDirectoryTemplate: 81, skipLogoOnOriginalRestart: true)
        } else {
            route = Route(destination: mode == .play ? .play : .utility,
                          originalDirectoryTemplate: nil, skipLogoOnOriginalRestart: false)
        }
        selectedRoute = route
        stage = .transitionReady
        return route
    }
}
