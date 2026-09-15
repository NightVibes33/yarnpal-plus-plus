#import "KPRebuiltCommon.h"
#import "KPBehaviorHooks.h"

static NSArray<KPFeature *> *TTKFeatures(void) {
#define F(t,k,s) [KPFeature feature:@t key:@k section:@s]
    return @[
        F("Enable TTKPlus","TTKPlus_Enabled","General"),
        F("Block ads","TTKPlus_AdBlock","Feed"), F("Clear display","TTKPlus_ClearDisplayEnabled","Feed"), F("Country pill","TTKPlus_CountryPill","Feed"), F("Grid date","TTKPlus_GridDate","Feed"), F("Download button","TTKPlus_DownloadButton","Feed"), F("Loop mode","TTKPlus_LoopMode","Feed"), F("Disable warnings","TTKPlus_DisableWarnings","Feed"), F("Skip recommendations","TTKPlus_SkipRecommendations","Feed"),
        F("Show follow badge","TTKPlus_ShowFollowBadge","Profile"), F("Show video count","TTKPlus_ShowVideoCount","Profile"), F("Avatar long press","TTKPlus_AvatarLongPress","Profile"), F("Bio tools","TTKPlus_Bio","Profile"), F("Anonymous profile view","TTKPlus_AnonymousProfileView","Profile"),
        F("Story read control","TTKPlus_StoryEye","Privacy"), F("Message read control","TTKPlus_MsgEye","Privacy"),
        F("LIVE auto click","TTKPlus_LiveAutoClick","Automation"),
        F("Follow confirmation","TTKPlus_FollowConfirmation","Confirmations"), F("Like confirmation","TTKPlus_LikeConfirmation","Confirmations"), F("Comment-like confirmation","TTKPlus_LikeCommentConfirmation","Confirmations"),
        F("Hide Friends tab","TTKPlus_HideFriendsTab","Tabs"), F("Hide Create tab","TTKPlus_HideCreateTab","Tabs"), F("Hide Inbox tab","TTKPlus_HideInboxTab","Tabs")
    ];
#undef F
}

__attribute__((constructor)) static void TTKPlusRebuiltInit(void) {
    @autoreleasepool {
        [[NSUserDefaults standardUserDefaults] registerDefaults:@{@"TTKPlus_Enabled":@YES}];
        KPInstallFloatingWheel(@"TTKillerPlus", ^NSArray<KPFeature *> *{ return TTKFeatures(); }, @"TTKPlus.Rebuilt.Free", 0x54544B50);
        KPInstallTTKBehaviorHooks();
    }
}
