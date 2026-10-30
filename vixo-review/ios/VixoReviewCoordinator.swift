import Foundation

/// One identifier per application process. This is NOT an iOS hardware ID,
/// an IDFV, Firebase Installation ID, a push token, or a replacement for those.
public final class VixoReviewAppLaunch {
    public static let current = VixoReviewAppLaunch()
    public let virtualDeviceId = UUID().uuidString
    private init() {}
}

/// Implement in VIXO's original Account / Subscription service with the
/// ORIGINAL production login token and backend (not an unrelated Firebase user).
public protocol VixoReviewBackend {
    func hasServerApprovedReviewPremium() async throws -> Bool
    func registerVirtualReviewDevice(_ deviceId: String) async throws
}

/// Server's response is authoritative; no locally-forced premium flag.
public final class VixoReviewCoordinator {
    private let backend: any VixoReviewBackend
    private let virtualDeviceId: String

    public init(backend: any VixoReviewBackend,
                virtualDeviceId: String = VixoReviewAppLaunch.current.virtualDeviceId) {
        self.backend = backend
        self.virtualDeviceId = virtualDeviceId
    }

    /// Call after VIXO's ordinary login/session restore.
    public func initializeAfterLogin() async throws -> Bool {
        guard try await backend.hasServerApprovedReviewPremium() else { return false }
        try await backend.registerVirtualReviewDevice(virtualDeviceId)
        return true
    }
}
