#import "KPDevPremiumEntitlement.h"

@implementation KPDevPremiumEntitlement

+ (KPDevPremiumMode)mode {
#if defined(KILLERPLUS_DEV_PREMIUM) && KILLERPLUS_DEV_PREMIUM
    return KPDevPremiumModeEnabled;
#else
    return KPDevPremiumModeDisabled;
#endif
}

+ (BOOL)isPremiumActive {
    return [self mode] == KPDevPremiumModeEnabled;
}

+ (NSString *)email {
    return @"dev-premium@local.invalid";
}

+ (NSString *)licenseKey {
    return @"DEV-PREMIUM";
}

+ (NSString *)deviceIdentifier {
    return @"DEV-PREMIUM-DEVICE";
}

+ (NSString *)expirationString {
    return @"2099-12-31 23:59:59";
}

+ (NSDate *)expirationDate {
    static NSDateFormatter *formatter;
    static dispatch_once_t onceToken;
    dispatch_once(&onceToken, ^{
        formatter = [[NSDateFormatter alloc] init];
        formatter.locale = [[NSLocale alloc] initWithLocaleIdentifier:@"en_US_POSIX"];
        formatter.timeZone = [NSTimeZone timeZoneForSecondsFromGMT:0];
        formatter.dateFormat = @"yyyy-MM-dd HH:mm:ss";
    });
    return [formatter dateFromString:[self expirationString]] ?: [NSDate distantFuture];
}

@end
