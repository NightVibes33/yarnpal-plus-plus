import Foundation
import FirebaseAuth
import FirebaseFunctions

/// Fresh for every app process, retained during that process's lifetime.
/// For VIXO-owned session registration only; not a persistent hardware ID.
final class VixoReviewLaunch {
    static let shared = VixoReviewLaunch()
    let sessionId = UUID().uuidString
    private init() {}
}

/// Add to the *original* VIXO project, then connect to the existing login,
/// entitlement view-model and authenticated backend. The server is authoritative.
final class VixoReviewAccessService {
    static let shared = VixoReviewAccessService()
    private let functions = Functions.functions(region: "us-central1")
    private init() {}

    // Call after Firebase Auth restores its current user at app launch.
    func initializeOnLaunch(completion: @escaping (Result<Bool, Error>) -> Void) {
        guard Auth.auth().currentUser != nil else {
            completion(.success(false))
            return
        }
        checkReviewEntitlement { [weak self] result in
            switch result {
            case .failure(let error):
                completion(.failure(error))
            case .success(false):
                completion(.success(false))
            case .success(true):
                self?.registerFreshLaunch { registerResult in
                    switch registerResult {
                    case .failure(let error): completion(.failure(error))
                    case .success(let registered): completion(.success(registered))
                    }
                }
            }
        }
    }

    func signIn(email: String, password: String,
                completion: @escaping (Result<Bool, Error>) -> Void) {
        Auth.auth().signIn(withEmail: email, password: password) { [weak self] _, error in
            if let error = error { completion(.failure(error)); return }
            self?.initializeOnLaunch(completion: completion)
        }
    }

    func checkReviewEntitlement(completion: @escaping (Result<Bool, Error>) -> Void) {
        functions.httpsCallable("vixoReviewAccess").call([:]) { result, error in
            if let error = error { completion(.failure(error)); return }
            guard let value = result?.data as? [String: Any],
                  let premium = value["premium"] as? Bool,
                  let review = value["review"] as? Bool else {
                completion(.failure(NSError(domain: "VixoReview", code: 1,
                    userInfo: [NSLocalizedDescriptionKey: "Malformed server response"])))
                return
            }
            completion(.success(premium && review))
        }
    }

    private func registerFreshLaunch(completion: @escaping (Result<Bool, Error>) -> Void) {
        functions.httpsCallable("vixoReviewLaunch")
            .call(["launchId": VixoReviewLaunch.shared.sessionId]) { result, error in
                if let error = error { completion(.failure(error)); return }
                guard let value = result?.data as? [String: Any],
                      let registered = value["registered"] as? Bool else {
                    completion(.failure(NSError(domain: "VixoReview", code: 2,
                        userInfo: [NSLocalizedDescriptionKey: "Malformed launch response"])))
                    return
                }
                completion(.success(registered))
            }
    }
}
