#import "KPRebuiltCommon.h"
#import "KPBehaviorHooks.h"

static NSArray<KPFeature *> *YTKFeatures(void) {
#define F(t,k,s) [KPFeature feature:@t key:@k section:@s]
    return @[
        F("No ads","kEnableiKarwanNoAds","Core"), F("Background playback","kEnableiKarwanPlayInBackgrounds","Core"), F("PiP","kEnableiKGHDYTKPiP","Core"), F("Downloads","kEnableiKarwanDownloadit","Core"), F("SponsorBlock","kEnableiKGHDsponsorBlock","Core"), F("Fix video playback","kEnableiKarwanFixVideoplayback","Core"),
        F("Loop","kEnableiKGHDYTKLoop","Playback"), F("Playback speed","kEnableiKGHDPlayBackSpeed","Playback"), F("HD over cellular","kEnableiKGHDPlayHDVideosOverCellur","Playback"), F("Hold to seek","kEnableiKGHDHoldToSeek","Playback"), F("Disable autoplay videos","kEnableiKGHDDisableAutoplayVideos","Playback"), F("Disable captions","kEnableiKGHDDisableCaptions","Playback"), F("Keep captions on","kEnableiKGHDKeepCaptionOn","Playback"), F("Legacy quality selection","kEnableiKGHDLegacyQSelection","Playback"), F("Disable pinch to zoom","kEnableiKGHDDisablePinchToZoom","Playback"), F("Disable double tap","kEnableiKGHDDisableDoubleTap","Playback"),
        F("Hide Shorts","kEnableiKGHDHideYTShorts","Navigation"), F("Replace Shorts with Explore","kEnableiKGHDReplaceShortsWithExplore","Navigation"), F("Hide Create","kEnableiKGHDDisableCreate","Navigation"), F("Hide Search","kEnableiKGHDHideSearch","Navigation"), F("Hide Account","kEnableiKGHDHideAccount","Navigation"), F("Hide notification bell","kEnableiKGHDHideNotificationBill","Navigation"), F("Hide YT logo","kEnableiKGHDHideYTLogo","Navigation"), F("Hide YTKPlus icon","kEnableiKGHDHideYTKPlusIcon","Navigation"), F("Sticky navbar","kEnableiKGHDStickyNavBar","Navigation"),
        F("Hide Cast button","kEnableiKGHDHideCastButton","Overlay"), F("Hide overlay Cast","kEnableiKGHDHideCastButtonOverlay","Overlay"), F("Hide captions toggle","kEnableiKGHDHideCaptionsToggle","Overlay"), F("Hide autoplay toggle","kEnableiKGHDHideAutoplayToggle","Overlay"), F("Hide previous/next","kEnableiKGHDHidePreviousNextButton","Overlay"), F("Hide play/pause","kEnableiKGHDHidePlayPuase","Overlay"), F("Hide related videos","kEnableiKGHDHideRelatedVideos","Overlay"), F("Hide info cards","kEnableiKGHDHideInfoCard","Overlay"), F("Hide end-screen videos","kEnableiKGHDHideEndScreenVideos","Overlay"), F("Hide dark overlay","kEnableiKGHDHideDarkOverlayBackground","Overlay"), F("Hide volume bar","kEnableiKGHDHideVolumeBar","Overlay"), F("Hide status bar","kEnableiKGHDHideStatusBar","Overlay"),
        F("Floating mini player","kEnableiKGHDFloatingMiniPlayer","Mini Player"), F("iPad-style mini player","kEnableiKGHDMiniPlayerIpadStyle","Mini Player"), F("Redefined mini player","kEnableiKGHDRedefindMiniPlayer","Mini Player"), F("Mini player everywhere","kEnableiKGHDminiPlayerall","Mini Player"),
        F("Hide comments","kEnableiKGHDHideComments","Content"), F("Hide playlists","kEnableiKGHDHidePlayList","Content"), F("Hide filter tags","kEnableiKGHDHideFilterTags","Content"), F("Hide suggested video","kEnableiKGHDHideSuggestedVideo","Content"), F("No paid promotion","kEnableiKGHDNoPaidPromotion","Content"), F("No premium popup","kEnableiKGHDNoPremiumpopup","Content"), F("No topics","kEnableiKGHDNoTopics","Content"), F("No searched history","kEnableiKGHDNoSearchedHistory","Content"), F("No update prompt","kEnableiKGHDNoYTUpdate","Content"),
        F("Dark keyboard","kEnableiKGHDDarkKeyboard","Appearance"), F("Old dark theme","kEnableiKGHDOldDarkTheme","Appearance"), F("Disable dark mode","kEnableiKGHDDisableDarkMode","Appearance"), F("Rounded UI","kEnableiKGHDRoundedUIView","Appearance"), F("Use premium logo","kEnableiKGHDUsePremiumLogo","Appearance"), F("Line separator","kEnableiKGHDLineSeprator","Appearance"),
        F("Classic share sheet","kEnableiKGHDClassicShareSheet","Misc"), F("iPadOS mode","kEnableiKGHDiPadOSMode","Misc"), F("Age restriction override","kEnableiKGHDAgeRestriction","Misc"), F("Cast confirmation","kEnableiKGHDCastconfirm","Misc"), F("Swipe to hide fullscreen panel","kEnableiKGHDSwipeToHidePanelInFullscreen","Misc"), F("Shorts fullscreen","kEnableiKGHDShortFS","Misc")
    ];
#undef F
}

__attribute__((constructor)) static void YTKPlusRebuiltInit(void) {
    @autoreleasepool {
        KPInstallFloatingWheel(@"YTKillerPlus", ^NSArray<KPFeature *> *{ return YTKFeatures(); }, @"YTKPlus.Rebuilt.Free", 0x59544B50);
        KPInstallYTKBehaviorHooks();
    }
}
