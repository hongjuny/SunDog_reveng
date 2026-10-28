import Foundation

private struct Fixture: Decodable {
    let background: [UInt8]
    let font: [UInt8]
    let messages: [[UInt8]]
    let expected: [UInt8]
    let labels: [[UInt8]]?
    let cursor: [Int]?
}

@main struct VerifyStartupTextScreen {
    static func main() throws {
        var matched = 0
        for path in CommandLine.arguments.dropFirst() {
            let fixture = try JSONDecoder().decode(Fixture.self, from: Data(contentsOf: URL(fileURLWithPath: path)))
            let page: [UInt8]
            if let labels = fixture.labels {
                page = try StartupTextScreen.composeChoices(background: fixture.background, font: fixture.font,
                    messages: fixture.messages, labels: labels, cursorX: fixture.cursor?[0], cursorY: fixture.cursor?[1])
            } else {
                page = try StartupTextScreen.compose(background: fixture.background, font: fixture.font, messages: fixture.messages)
            }
            guard page == fixture.expected else {
                let differences = zip(page, fixture.expected).filter { $0 != $1 }.count
                fatalError("Original startup frame differs: \(differences) bytes")
            }
            matched += 1
        }
        print("{\"full_page_cases\":\(matched),\"all_matched\":true}")
    }
}
