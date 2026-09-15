#import "KPRebuiltCommon.h"
#import <objc/runtime.h>

@implementation KPFeature
+ (instancetype)feature:(NSString *)title key:(NSString *)key section:(NSString *)section { KPFeature *f=[KPFeature new]; f.title=title; f.key=key; f.section=section; return f; }
@end

static UIViewController *KPTopController(UIViewController *vc) { if (!vc) return nil; if (vc.presentedViewController) return KPTopController(vc.presentedViewController); if ([vc isKindOfClass:UINavigationController.class]) return KPTopController(((UINavigationController *)vc).visibleViewController); if ([vc isKindOfClass:UITabBarController.class]) return KPTopController(((UITabBarController *)vc).selectedViewController); return vc; }

@interface KPFeatureController ()
@property(nonatomic,strong) NSArray<KPFeature *> *features; @property(nonatomic,strong) NSArray<NSString *> *sections; @property(nonatomic,strong) NSDictionary<NSString *,NSArray<KPFeature *> *> *grouped; @property(nonatomic,copy) NSString *defaultsDomain;
@end
@implementation KPFeatureController
- (instancetype)initWithTitle:(NSString *)title features:(NSArray<KPFeature *> *)features defaultsDomain:(NSString *)domain { if ((self=[super initWithStyle:UITableViewStyleInsetGrouped])) { self.title=title; _features=features; _defaultsDomain=[domain copy]; NSMutableArray *order=[NSMutableArray array]; NSMutableDictionary *groups=[NSMutableDictionary dictionary]; for (KPFeature *f in features) { if (!groups[f.section]) { groups[f.section]=[NSMutableArray array]; [order addObject:f.section]; } [groups[f.section] addObject:f]; } _sections=[order copy]; _grouped=[groups copy]; } return self; }
- (void)viewDidLoad { [super viewDidLoad]; self.navigationItem.rightBarButtonItem=[[UIBarButtonItem alloc] initWithBarButtonSystemItem:UIBarButtonSystemItemDone target:self action:@selector(kp_done)]; }
- (void)kp_done { [self dismissViewControllerAnimated:YES completion:nil]; }
- (NSInteger)numberOfSectionsInTableView:(UITableView *)tableView { return self.sections.count; }
- (NSInteger)tableView:(UITableView *)tableView numberOfRowsInSection:(NSInteger)section { return self.grouped[self.sections[section]].count; }
- (NSString *)tableView:(UITableView *)tableView titleForHeaderInSection:(NSInteger)section { return self.sections[section]; }
- (UITableViewCell *)tableView:(UITableView *)tableView cellForRowAtIndexPath:(NSIndexPath *)indexPath { UITableViewCell *cell=[tableView dequeueReusableCellWithIdentifier:@"f"]; if (!cell) cell=[[UITableViewCell alloc] initWithStyle:UITableViewCellStyleSubtitle reuseIdentifier:@"f"]; KPFeature *f=self.grouped[self.sections[indexPath.section]][indexPath.row]; cell.textLabel.text=f.title; UISwitch *sw=[UISwitch new]; sw.on=[[NSUserDefaults standardUserDefaults] boolForKey:f.key]; sw.accessibilityIdentifier=f.key; [sw addTarget:self action:@selector(kp_toggle:) forControlEvents:UIControlEventValueChanged]; cell.accessoryView=sw; return cell; }
- (void)kp_toggle:(UISwitch *)sender { if (sender.accessibilityIdentifier.length) { [[NSUserDefaults standardUserDefaults] setBool:sender.isOn forKey:sender.accessibilityIdentifier]; [[NSUserDefaults standardUserDefaults] synchronize]; [[NSNotificationCenter defaultCenter] postNotificationName:@"KPRebuiltPreferenceChanged" object:sender.accessibilityIdentifier]; } }
@end

@interface KPFloatingTarget : NSObject
@property(nonatomic,copy) NSString *title; @property(nonatomic,copy) NSString *domain; @property(nonatomic,copy) NSArray<KPFeature *> *(^featuresProvider)(void); - (void)open:(id)sender;
@end
@implementation KPFloatingTarget
- (void)open:(id)sender { UIWindow *w=nil; for (UIScene *scene in UIApplication.sharedApplication.connectedScenes) if ([scene isKindOfClass:UIWindowScene.class] && scene.activationState==UISceneActivationStateForegroundActive) { for (UIWindow *candidate in ((UIWindowScene *)scene).windows) if (candidate.isKeyWindow) { w=candidate; break; } if (w) break; } if (!w) w=UIApplication.sharedApplication.windows.firstObject; UIViewController *top=KPTopController(w.rootViewController); if (!top) return; KPFeatureController *settings=[[KPFeatureController alloc] initWithTitle:self.title features:self.featuresProvider ? self.featuresProvider() : @[] defaultsDomain:self.domain]; UINavigationController *nav=[[UINavigationController alloc] initWithRootViewController:settings]; nav.modalPresentationStyle=UIModalPresentationPageSheet; [top presentViewController:nav animated:YES completion:nil]; }
@end

static NSMutableArray *gTargets;
static void KPInstallOne(NSString *title, NSArray<KPFeature *> *(^provider)(void), NSString *domain, NSInteger tag) { dispatch_async(dispatch_get_main_queue(), ^{ UIWindow *w=nil; for (UIScene *scene in UIApplication.sharedApplication.connectedScenes) if ([scene isKindOfClass:UIWindowScene.class] && scene.activationState==UISceneActivationStateForegroundActive) { for (UIWindow *candidate in ((UIWindowScene *)scene).windows) if (candidate.isKeyWindow) { w=candidate; break; } if (w) break; } if (!w || [w viewWithTag:tag]) return; UIButton *b=[UIButton buttonWithType:UIButtonTypeSystem]; b.tag=tag; b.frame=CGRectMake(MAX(12,w.bounds.size.width-62),MAX(120,w.safeAreaInsets.top+70),50,50); b.layer.cornerRadius=25; b.backgroundColor=[UIColor colorWithWhite:0.10 alpha:0.82]; b.tintColor=UIColor.whiteColor; [b setImage:[UIImage systemImageNamed:@"gearshape.fill"] forState:UIControlStateNormal]; b.autoresizingMask=UIViewAutoresizingFlexibleLeftMargin|UIViewAutoresizingFlexibleBottomMargin; KPFloatingTarget *target=[KPFloatingTarget new]; target.title=title; target.domain=domain; target.featuresProvider=provider; if (!gTargets) gTargets=[NSMutableArray array]; [gTargets addObject:target]; [b addTarget:target action:@selector(open:) forControlEvents:UIControlEventTouchUpInside]; [w addSubview:b]; [w bringSubviewToFront:b]; }); }
void KPInstallFloatingWheel(NSString *title, NSArray<KPFeature *> *(^featuresProvider)(void), NSString *domain, NSInteger tag) { void (^install)(void)=^{ KPInstallOne(title,featuresProvider,domain,tag); dispatch_after(dispatch_time(DISPATCH_TIME_NOW,(int64_t)(2*NSEC_PER_SEC)),dispatch_get_main_queue(),^{ KPInstallOne(title,featuresProvider,domain,tag); }); }; [[NSNotificationCenter defaultCenter] addObserverForName:UIApplicationDidBecomeActiveNotification object:nil queue:NSOperationQueue.mainQueue usingBlock:^(__unused NSNotification *n){ install(); }]; dispatch_after(dispatch_time(DISPATCH_TIME_NOW,(int64_t)(1*NSEC_PER_SEC)),dispatch_get_main_queue(),install); }
