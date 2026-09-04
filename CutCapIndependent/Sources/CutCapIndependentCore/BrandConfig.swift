import Foundation

public enum BrandConfig {
    // Temporary brand derived from the uploaded CutCap.ipa filename.
    // Keep all product identity in one place so the final name can be changed cleanly.
    public static let displayName = "CutCap"
    public static let bundleIdentifier = "com.nightvibes33.cutcap"
    public static let appGroupIdentifier = "group.com.nightvibes33.cutcap"
    public static let deepLinkScheme = "cutcap"

    public static let shareExtensionBundleIdentifier = "com.nightvibes33.cutcap.share"
    public static let notificationExtensionBundleIdentifier = "com.nightvibes33.cutcap.notification"
    public static let actionExtensionBundleIdentifier = "com.nightvibes33.cutcap.action"
    public static let liveActivityExtensionBundleIdentifier = "com.nightvibes33.cutcap.liveactivity"
    public static let intentExtensionBundleIdentifier = "com.nightvibes33.cutcap.intents"

    public static let defaultProjectName = "New project"
    public static let exportMetadataCreator = displayName
}
