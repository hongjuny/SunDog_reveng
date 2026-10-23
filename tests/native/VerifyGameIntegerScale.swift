import Foundation

@main struct VerifyGameIntegerScale {
    struct Case: Decodable { let x:Int16;let y:Int16;let divisor:Int16;let result:Int16 }
    enum Failure: Error { case missingCases, mismatch(Int), unexpectedErrorBehavior }
    static func main() throws {
        guard CommandLine.arguments.count==2 else { throw Failure.missingCases }
        let cases=try JSONDecoder().decode([Case].self,from:Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[1])))
        guard !cases.isEmpty else { throw Failure.missingCases }
        for (index,row) in cases.enumerated() {
            guard try GameIntegerScale.apply(x:row.x,y:row.y,divisor:row.divisor)==row.result else { throw Failure.mismatch(index) }
        }
        for (x,y,d): (Int16,Int16,Int16) in [(0,1,1),(1,1,0),(0,0,0)] {
            do { _=try GameIntegerScale.apply(x:x,y:y,divisor:d);throw Failure.unexpectedErrorBehavior }
            catch GameIntegerScale.Failure.divisionByZero {}
        }
        do { _=try GameIntegerScale.apply(x:-1,y:2,divisor:1);throw Failure.unexpectedErrorBehavior }
        catch GameIntegerScale.Failure.outsideVerifiedDomain {}
        print("{\"native_cases\":\(cases.count),\"zero_error_cases\":3,\"unsupported_domain_rejected\":true}")
    }
}
