import Foundation
import CryptoKit
import SunDogLogic

public struct StartupResources: Sendable {
    public struct Label: Decodable, Sendable { public let id: Int; public let bytes: [UInt8] }
    private struct Texts: Decodable {
        let greeting: [String: [UInt8]]; let labels: [Label]; let playFlip: [[UInt8]]
    }
    private struct Gate: Decodable { let gate_messages: [[UInt8]]; let font_sha256: String }
    private struct NamedProfile: Decodable { let name: String; let mode: StartupFlow.Mode }
    public let profile: StartupFlow.Profile
    public let mode: StartupFlow.Mode
    public let name: String
    public let font: [UInt8]
    public let gateMessages: [[UInt8]]
    public let greeting: [String: [UInt8]]
    public let labels: [Label]
    public let playFlipMessages: [[UInt8]]
    public let playBoot: [UInt8]
    public let initialShip: [UInt8]
    public struct ShipState: Decodable, Sendable {
        public let x: Int; public let y: Int
        public let word38: Int; public let word39: Int; public let pointerGlyph: Int
    }
    public let shipState: ShipState
    private struct ShipMetadata: Decodable { let length: Int; let sha256: String; let decoded_sha256: String }
    public enum Failure: Error { case invalidResources }

    public static func load(directory: URL) throws -> StartupResources {
        func read(_ name: String) throws -> Data { try Data(contentsOf: directory.appendingPathComponent(name)) }
        let decoder=JSONDecoder()
        let profileData=try read("sundog-startup-profile.json")
        let profile=try decoder.decode(StartupFlow.Profile.self,from:profileData)
        let named=try decoder.decode(NamedProfile.self,from:profileData)
        let texts=try decoder.decode(Texts.self,from:read("sundog-startup-ui.json"))
        let gate=try decoder.decode(Gate.self,from:read("startup-text.json"))
        let font=try read("sundog-font.bin")
        let digest=SHA256.hash(data:font).map { String(format:"%02x",$0) }.joined()
        let boot=[UInt8](try read("sundog-play-boot.bin"))
        let shipState=try decoder.decode(ShipState.self,from:read("sundog-ship-interaction.json"))
        let shipSource=try read("sundog-initial-ship.bin")
        let shipMetadata=try decoder.decode(ShipMetadata.self,from:read("sundog-initial-ship.json"))
        let sourceDigest=SHA256.hash(data:shipSource).map { String(format:"%02x",$0) }.joined()
        let ship=try ShipScreenDecoder.decode(encoded:Array(shipSource))
        let shipDigest=SHA256.hash(data:Data(ship.page)).map { String(format:"%02x",$0) }.joined()
        guard font.count==1024,digest==gate.font_sha256,boot.count==512,
              sourceDigest==shipMetadata.sha256,shipSource.count==shipMetadata.length,
              shipDigest==shipMetadata.decoded_sha256,
              named.name.utf8.count<=20,named.name.unicodeScalars.allSatisfy({$0.value<128}) else {
            throw Failure.invalidResources
        }
        return StartupResources(profile:profile,mode:named.mode,name:named.name,font:Array(font),
            gateMessages:gate.gate_messages,greeting:texts.greeting,labels:texts.labels,
            playFlipMessages:texts.playFlip,playBoot:boot,initialShip:ship.page,shipState:shipState)
    }
    public func greetingMessages() throws -> [[UInt8]] {
        func word(_ key: String) throws -> [UInt8] {
            guard let value=greeting[key] else { throw Failure.invalidResources }
            return value
        }
        let dead=profile.state==12, won=profile.state==13
        var result=[try word(dead || profile.damaged ? "tooBad" : won ? "wellDone" : "hello"),Array(name.utf8)]
        if dead || won {
            result += [try word(dead ? "died" : "succeeded"),try word("gameOver")]
        } else if profile.damaged { result += [try word("damaged")] }
        result += [try word("can")]
        if profile.playAllowed {
            result += [try word(profile.newGame ? "start" : "continueGame"),try word("yourGame")]
        }
        result += [try word("options")]
        return result
    }
}
