#import <Foundation/Foundation.h>
#import <UIKit/UIKit.h>

NS_ASSUME_NONNULL_BEGIN

@interface KPFeature : NSObject
@property(nonatomic,copy) NSString *title;
@property(nonatomic,copy) NSString *key;
@property(nonatomic,copy) NSString *section;
+ (instancetype)feature:(NSString *)title key:(NSString *)key section:(NSString *)section;
@end

@interface KPFeatureController : UITableViewController
- (instancetype)initWithTitle:(NSString *)title features:(NSArray<KPFeature *> *)features defaultsDomain:(NSString *)domain;
@end

void KPInstallFloatingWheel(NSString *title, NSArray<KPFeature *> *(^featuresProvider)(void), NSString *domain, NSInteger tag);

NS_ASSUME_NONNULL_END
