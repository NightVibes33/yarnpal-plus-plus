import Foundation
import FirebaseAuth
import FirebaseFunctions

/// QA-only credit observer for the optional Firebase Auth test backend.
/// Does not change a real VIXO account's payment-service credit balance.
final class VixoQaCreditsService {
    static let shared = VixoQaCreditsService()
    private let functions = Functions.functions(region: "us-central1")
    private var listener: AuthStateDidChangeListenerHandle?
    private init() {}

    /// Start once during app launch. Calls the authenticated Cloud Function on
    /// every sign-in/session restore. An online success is required before the
    /// QA UI may show 9,999 credits.
    func start(onBalance: @escaping (Result<Int, Error>) -> Void) {
        stop()
        listener = Auth.auth().addStateDidChangeListener { [weak self] _, user in
            guard let self = self, user != nil else { return }
            self.functions.httpsCallable("vixoQaEnsureCredits").call([:]) {
                result, error in
                if let error = error {
                    onBalance(.failure(error))
                    return
                }
                guard let response = result?.data as? [String: Any],
                      let credits = response["credits"] as? Int else {
                    onBalance(.failure(NSError(
                        domain: "VixoQaCredits",
                        code: 1,
                        userInfo: [
                            NSLocalizedDescriptionKey: "Invalid server credit response"
                        ]
                    )))
                    return
                }
                onBalance(.success(credits))
            }
        }
    }

    func stop() {
        if let listener = listener {
            Auth.auth().removeStateDidChangeListener(listener)
            self.listener = nil
        }
    }
}
