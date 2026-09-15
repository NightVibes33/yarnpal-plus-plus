#import <Foundation/Foundation.h>

NS_ASSUME_NONNULL_BEGIN

typedef NS_ENUM(NSInteger, KPDevPremiumMode) {
    KPDevPremiumModeDisabled = 0,
    KPDevPremiumModeEnabled = 1,
};

@interface KPDevPremiumEntitlement : NSObject

+ (KPDevPremiumMode)mode;
+ (BOOL)isPremiumActive;
+ (NSString *)email;
+ (NSString *)licenseKey;
+ (NSString *)deviceIdentifier;
+ (NSString *)expirationString;
+ (NSDate *)expirationDate;

@end

NS_ASSUME_NONNULL_END
