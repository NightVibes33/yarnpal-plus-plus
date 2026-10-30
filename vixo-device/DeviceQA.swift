import UIKit
import Foundation

// VIXO QA harness for physical iPhones. No impersonation of production users
// or Apple hardware, and no write requests to the production VIXO backend.
@main
final class VixoQADevice: UIResponder, UIApplicationDelegate {
    var window: UIWindow?

    static func main() {
        UIApplicationMain(CommandLine.argc, CommandLine.unsafeArgv, nil,
                          NSStringFromClass(VixoQADevice.self))
    }

    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions launchOptions:
                     [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        let window = UIWindow(frame: UIScreen.main.bounds)
        window.rootViewController = DeviceQAScreen()
        window.makeKeyAndVisible()
        self.window = window
        return true
    }
}

final class DeviceQAScreen: UIViewController {
    private let launchId = UUID().uuidString
    private let accountControl = UISegmentedControl(items: ["QA account 1", "QA account 2"])
    private let titleLabel = UILabel()
    private let statusLabel = UILabel()
    private let balanceLabel = UILabel()
    private let sessionLabel = UILabel()
    private let noteLabel = UILabel()
    private let storageKey = "VixoQAOfflineCreditBalances"
    private let users = ["qa-one", "qa-two"]

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .systemBackground
        accountControl.selectedSegmentIndex = 0
        accountControl.addTarget(self, action: #selector(refreshBalance),
                                 for: .valueChanged)

        let previous = UserDefaults.standard.string(forKey: "VixoQAPriorLaunchUUID")
        UserDefaults.standard.set(launchId, forKey: "VixoQAPriorLaunchUUID")

        titleLabel.text = "VIXO • Device QA"
        titleLabel.font = .preferredFont(forTextStyle: .largeTitle)
        titleLabel.adjustsFontForContentSizeCategory = true

        sessionLabel.font = .preferredFont(forTextStyle: .caption1)
        sessionLabel.textColor = .secondaryLabel
        sessionLabel.numberOfLines = 0
        sessionLabel.text = "App-session UUID:\n\(launchId)\nChanged from previous launch: \(previous == nil ? "first launch" : (previous == launchId ? "NO" : "YES"))"

        balanceLabel.font = .monospacedDigitSystemFont(ofSize: 28, weight: .semibold)
        balanceLabel.textAlignment = .center

        statusLabel.font = .preferredFont(forTextStyle: .body)
        statusLabel.numberOfLines = 0
        statusLabel.text = "Select a QA account and sign in."

        noteLabel.font = .preferredFont(forTextStyle: .footnote)
        noteLabel.textColor = .secondaryLabel
        noteLabel.numberOfLines = 0
        noteLabel.text = "QA TEST ONLY. Credits are stored locally in this app. They are not VIXO production credits. No real account registration, purchases or credit grants are performed."

        let signIn = makeButton("QA login • set 9,999 test credits",
                                action: #selector(signIn))
        let spend = makeButton("Spend 100 test credits",
                               action: #selector(spendCredits))
        let verify = makeButton("Check VIXO credit API • read only",
                                action: #selector(checkProductionAPI))
        let stack = UIStackView(arrangedSubviews: [
            titleLabel, sessionLabel, accountControl, balanceLabel,
            signIn, spend, verify, statusLabel, noteLabel
        ])
        stack.axis = .vertical
        stack.spacing = 18
        stack.alignment = .fill
        stack.translatesAutoresizingMaskIntoConstraints = false
        let scroll = UIScrollView()
        scroll.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(scroll)
        scroll.addSubview(stack)
        NSLayoutConstraint.activate([
            scroll.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor),
            scroll.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor),
            scroll.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            scroll.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            stack.topAnchor.constraint(equalTo: scroll.contentLayoutGuide.topAnchor, constant: 24),
            stack.bottomAnchor.constraint(equalTo: scroll.contentLayoutGuide.bottomAnchor, constant: -24),
            stack.leadingAnchor.constraint(equalTo: scroll.contentLayoutGuide.leadingAnchor, constant: 22),
            stack.trailingAnchor.constraint(equalTo: scroll.contentLayoutGuide.trailingAnchor, constant: -22),
            stack.widthAnchor.constraint(equalTo: scroll.frameLayoutGuide.widthAnchor, constant: -44)
        ])
        refreshBalance()
    }

    private func makeButton(_ title: String, action: Selector) -> UIButton {
        let button = UIButton(type: .system)
        button.setTitle(title, for: .normal)
        button.titleLabel?.font = .preferredFont(forTextStyle: .headline)
        button.titleLabel?.numberOfLines = 0
        button.layer.cornerRadius = 12
        button.backgroundColor = .secondarySystemBackground
        button.contentEdgeInsets = UIEdgeInsets(top: 16, left: 10, bottom: 16, right: 10)
        button.addTarget(self, action: action, for: .touchUpInside)
        return button
    }

    private var selectedUser: String { users[accountControl.selectedSegmentIndex] }
    private var balances: [String: Int] {
        UserDefaults.standard.dictionary(forKey: storageKey) as? [String: Int] ?? [:]
    }

    private func setBalance(_ amount: Int, user: String) {
        var updated = balances
        updated[user] = amount
        UserDefaults.standard.set(updated, forKey: storageKey)
    }

    @objc private func refreshBalance() {
        balanceLabel.text = "\(balances[selectedUser] ?? 0) QA credits"
    }

    @objc private func signIn() {
        // Fixture-only sign-in. No real VIXO account or server is contacted.
        setBalance(9999, user: selectedUser)
        refreshBalance()
        statusLabel.text = "\(selectedUser): 9,999 local QA credits set on login."
    }

    @objc private func spendCredits() {
        let value = balances[selectedUser] ?? 0
        guard value >= 100 else {
            statusLabel.text = "Insufficient QA credits. Sign in first."
            return
        }
        setBalance(value - 100, user: selectedUser)
        refreshBalance()
        statusLabel.text = "Spent 100 QA credits. New local balance: \(value - 100)."
    }

    @objc private func checkProductionAPI() {
        // Fixed read-only request. No credentials, no account IDs, no body,
        // no mutations. This does NOT verify real server credit balances.
        guard let url = URL(string: "https://api.vixo.one/api/rest/user/points/info")
        else { return }
        statusLabel.text = "Checking public HTTPS endpoint (GET)..."
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.timeoutInterval = 10
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        URLSession.shared.dataTask(with: request) { [weak self] _, response, error in
            DispatchQueue.main.async {
                guard let self = self else { return }
                if let error = error {
                    self.statusLabel.text = "Network check failed: \(error.localizedDescription)"
                } else if let http = response as? HTTPURLResponse {
                    self.statusLabel.text = "Read-only VIXO API HTTP \(http.statusCode). No production credits changed."
                } else {
                    self.statusLabel.text = "No HTTP response from VIXO API."
                }
            }
        }.resume()
    }
}
