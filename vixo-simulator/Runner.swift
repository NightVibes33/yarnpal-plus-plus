import UIKit
import Foundation

// Simulator-only VIXO QA harness. UUID is application-managed, not hardware identity.
@main final class Runner: UIResponder, UIApplicationDelegate {
    var window: UIWindow?
    static func main() {
        UIApplicationMain(CommandLine.argc, CommandLine.unsafeArgv, nil,
                          NSStringFromClass(Runner.self))
    }
    func application(_ app: UIApplication, didFinishLaunchingWithOptions opts:
                     [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        let w = UIWindow(frame: UIScreen.main.bounds)
        let root = UIViewController()
        root.view.backgroundColor = .white
        let label = UILabel(frame: CGRect(x: 20, y: 120, width: 330, height: 120))
        label.text = "VIXO QA - Simulator\nBackend integration test"
        label.numberOfLines = 0
        root.view.addSubview(label)
        w.rootViewController = root
        w.makeKeyAndVisible()
        window = w
        Task { await self.run() }
        return true
    }
    func request(_ route: String, _ body: [String: Any] = [:],
                 _ token: String? = nil, method: String = "POST") async throws -> [String: Any] {
        var req = URLRequest(url: URL(string: "http://127.0.0.1:18777/" + route)!)
        req.httpMethod = method
        req.timeoutInterval = 15
        if let token = token { req.setValue("Bearer " + token, forHTTPHeaderField: "Authorization") }
        if method == "POST" {
            req.httpBody = try JSONSerialization.data(withJSONObject: body)
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        let (data, response) = try await URLSession.shared.data(for: req)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw NSError(domain: "VixoQA", code: 1, userInfo: [NSLocalizedDescriptionKey:
                "Request failed: " + (String(data: data, encoding: .utf8) ?? "")])
        }
        guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw NSError(domain: "VixoQA", code: 2)
        }
        return json
    }
    func store(_ value: [String: Any]) {
        do {
            let dir = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
            try JSONSerialization.data(withJSONObject: value, options: [.prettyPrinted])
                .write(to: dir.appendingPathComponent("result.json"), options: .atomic)
        } catch { NSLog("QA result write failed: %@", String(describing: error)) }
    }
    func run() async {
        let launchId = UUID().uuidString
        do {
            var accounts = [[String: Any]]()
            for uid in ["qa-one", "qa-two"] {
                let login = try await request("login", ["userId": uid])
                let token = login["token"] as! String
                let session = try await request("session", ["launchId": launchId], token)
                let grant = try await request("grant", [:], token)
                let balance = try await request("balance", [:], token, method: "GET")
                let spend = try await request("spend", ["amount": 100], token)
                accounts.append(["uid": uid, "session": session["id"] as! String,
                                 "registered": session["registered"] as! Bool,
                                 "grant": grant["credits"] as! Int,
                                 "before": balance["credits"] as! Int,
                                 "after": spend["credits"] as! Int])
            }
            store(["launchId": launchId, "accounts": accounts, "qaOnly": true])
        } catch { store(["launchId": launchId, "error": String(describing: error)]) }
    }
}
