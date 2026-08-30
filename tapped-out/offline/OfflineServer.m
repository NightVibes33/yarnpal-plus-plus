#import <Foundation/Foundation.h>
#import <dispatch/dispatch.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <unistd.h>

static const uint16_t kOfflinePort = 31337;
static NSString * const kOfflineBase = @"http://127.0.0.1:31337";
static NSString * const kOfflineUserId = @"1000001";
static NSString * const kOfflineMayhemId = @"1000000000001";
static NSString * const kOfflineToken = @"OFFLINE_TSTO_TOKEN";
static NSString * const kOfflineCode = @"OFFLINE_TSTO_CODE";
static NSString * const kOfflineLandToken = @"OFFLINE-LAND-TOKEN-0001";
static const int32_t kOfflinePremium = 2000000000;

static void pbVarint(NSMutableData *out, uint64_t value) {
    while (value >= 0x80) {
        uint8_t b = (uint8_t)((value & 0x7f) | 0x80);
        [out appendBytes:&b length:1];
        value >>= 7;
    }
    uint8_t b = (uint8_t)value;
    [out appendBytes:&b length:1];
}

static void pbKey(NSMutableData *out, uint32_t field, uint8_t wire) {
    pbVarint(out, ((uint64_t)field << 3) | wire);
}

static void pbString(NSMutableData *out, uint32_t field, NSString *value) {
    NSData *data = [value dataUsingEncoding:NSUTF8StringEncoding] ?: [NSData data];
    pbKey(out, field, 2);
    pbVarint(out, data.length);
    [out appendData:data];
}

static void pbBytes(NSMutableData *out, uint32_t field, NSData *value) {
    pbKey(out, field, 2);
    pbVarint(out, value.length);
    [out appendData:value];
}

static void pbInt(NSMutableData *out, uint32_t field, uint64_t value) {
    pbKey(out, field, 0);
    pbVarint(out, value);
}

static NSData *pbUsersResponse(void) {
    NSMutableData *user = [NSMutableData data];
    pbString(user, 1, kOfflineMayhemId);
    pbString(user, 2, @"42");

    NSMutableData *token = [NSMutableData data];
    pbString(token, 1, @"OFFLINE_SESSION");

    NSMutableData *msg = [NSMutableData data];
    pbBytes(msg, 1, user);
    pbBytes(msg, 2, token);
    return msg;
}

static NSData *pbWholeLandToken(void) {
    NSMutableData *msg = [NSMutableData data];
    pbString(msg, 1, kOfflineLandToken);
    pbInt(msg, 2, 0);
    return msg;
}

static NSData *pbDeleteToken(void) {
    NSMutableData *msg = [NSMutableData data];
    pbInt(msg, 1, 1);
    return msg;
}

static NSData *pbCurrencyResponse(void) {
    NSTimeInterval now = [[NSDate date] timeIntervalSince1970];
    NSMutableData *currency = [NSMutableData data];
    pbString(currency, 1, kOfflineMayhemId);
    pbInt(currency, 2, 0);
    pbInt(currency, 3, (uint32_t)kOfflinePremium);
    pbInt(currency, 4, (uint32_t)kOfflinePremium);
    pbInt(currency, 5, (uint64_t)now);
    pbInt(currency, 6, (uint64_t)now);
    pbInt(currency, 7, 0);

    NSMutableData *msg = [NSMutableData data];
    pbBytes(msg, 1, currency);
    return msg;
}

static NSData *jsonData(id obj) {
    return [NSJSONSerialization dataWithJSONObject:obj options:0 error:nil] ?: [NSData dataWithBytes:"{}" length:2];
}

static NSString *stateDirectory(void) {
    NSArray<NSURL *> *urls = [[NSFileManager defaultManager] URLsForDirectory:NSApplicationSupportDirectory inDomains:NSUserDomainMask];
    NSURL *base = urls.firstObject ?: [NSURL fileURLWithPath:NSTemporaryDirectory() isDirectory:YES];
    NSURL *dir = [base URLByAppendingPathComponent:@"TSTOOffline" isDirectory:YES];
    [[NSFileManager defaultManager] createDirectoryAtURL:dir withIntermediateDirectories:YES attributes:nil error:nil];
    return dir.path;
}

static NSString *landSavePath(void) {
    return [stateDirectory() stringByAppendingPathComponent:@"land.pb"];
}

static NSString *dlcPathForRequest(NSString *path) {
    NSString *rel = path;
    if ([rel hasPrefix:@"/dlc/"]) rel = [rel substringFromIndex:5];
    while ([rel hasPrefix:@"/"]) rel = [rel substringFromIndex:1];
    if ([rel containsString:@".."] || rel.length == 0) return nil;

    NSString *container = [[stateDirectory() stringByAppendingPathComponent:@"dlc"] stringByAppendingPathComponent:rel];
    if ([[NSFileManager defaultManager] fileExistsAtPath:container]) return container;

    NSString *bundleRoot = [[[NSBundle mainBundle] resourcePath] stringByAppendingPathComponent:@"OfflineDLC"];
    NSString *bundled = [bundleRoot stringByAppendingPathComponent:rel];
    if ([[NSFileManager defaultManager] fileExistsAtPath:bundled]) return bundled;
    return nil;
}

static NSDictionary *directionResponse(void) {
    NSArray *serverData = @[
        @{ @"key": @"nexus.portal", @"value": kOfflineBase },
        @{ @"key": @"nexus.connect", @"value": [kOfflineBase stringByAppendingString:@"/"] },
        @{ @"key": @"nexus.proxy", @"value": [kOfflineBase stringByAppendingString:@"/"] },
        @{ @"key": @"synergy.director", @"value": kOfflineBase },
        @{ @"key": @"synergy.user", @"value": kOfflineBase },
        @{ @"key": @"synergy.drm", @"value": kOfflineBase },
        @{ @"key": @"synergy.product", @"value": kOfflineBase },
        @{ @"key": @"synergy.tracking", @"value": kOfflineBase },
        @{ @"key": @"synergy.m2u", @"value": kOfflineBase },
        @{ @"key": @"synergy.pns", @"value": kOfflineBase },
        @{ @"key": @"synergy.s2s", @"value": kOfflineBase },
        @{ @"key": @"synergy.cipgl", @"value": kOfflineBase },
        @{ @"key": @"mayhem.url", @"value": kOfflineBase },
        @{ @"key": @"service.discovery.url", @"value": kOfflineBase },
        @{ @"key": @"geoip.url", @"value": kOfflineBase },
        @{ @"key": @"friends.url", @"value": kOfflineBase },
        @{ @"key": @"eadp.friends.host", @"value": kOfflineBase },
        @{ @"key": @"antelope.friends.url", @"value": kOfflineBase },
        @{ @"key": @"antelope.groups.url", @"value": kOfflineBase },
        @{ @"key": @"antelope.inbox.url", @"value": kOfflineBase },
        @{ @"key": @"antelope.rtm.url", @"value": kOfflineBase },
        @{ @"key": @"antelope.rtm.host", @"value": @"127.0.0.1:31337" },
        @{ @"key": @"group.recommendations.url", @"value": kOfflineBase },
        @{ @"key": @"friend.recommendations.url", @"value": kOfflineBase },
        @{ @"key": @"river.pin", @"value": kOfflineBase },
        @{ @"key": @"pin.aruba.url", @"value": kOfflineBase },
        @{ @"key": @"aruba.url", @"value": kOfflineBase },
        @{ @"key": @"origincasualserver.url", @"value": kOfflineBase },
        @{ @"key": @"origincasualapp.url", @"value": kOfflineBase },
        @{ @"key": @"ens.url", @"value": kOfflineBase },
        @{ @"key": @"dmg.url", @"value": kOfflineBase },
        @{ @"key": @"akamai.url", @"value": [kOfflineBase stringByAppendingString:@"/dlc/"] }
    ];
    return @{
        @"DMGId": @0,
        @"appUpgrade": @0,
        @"clientId": @"simpsons4-ios-client",
        @"clientSecret": @"offline",
        @"disabledFeatures": @[],
        @"hwId": @2363,
        @"mayhemGameCode": @"bg_gameserver_plugin",
        @"mdmAppKey": @"simpsons-4-ios",
        @"packageId": @"com.ea.game.simpsons4_row",
        @"pollIntervals": @[ @{ @"key": @"badgePollInterval", @"value": @"300" } ],
        @"productId": @48302,
        @"resultCode": @0,
        @"sellId": @857120,
        @"serverApiVersion": @"1.0.0",
        @"serverData": serverData,
        @"telemetryFreq": @300
    };
}

static NSData *bundleResource(NSString *name, NSString *ext) {
    NSString *path = [[NSBundle mainBundle] pathForResource:name ofType:ext];
    return path ? [NSData dataWithContentsOfFile:path] : nil;
}

static NSString *statusText(int status) {
    switch (status) {
        case 200: return @"OK";
        case 204: return @"No Content";
        case 400: return @"Bad Request";
        case 404: return @"Not Found";
        case 500: return @"Internal Server Error";
        default: return @"OK";
    }
}

static void writeAll(int fd, const void *bytes, size_t len) {
    const uint8_t *p = bytes;
    while (len > 0) {
        ssize_t n = send(fd, p, len, 0);
        if (n <= 0) break;
        p += n;
        len -= (size_t)n;
    }
}

static void respond(int fd, int status, NSString *type, NSData *body) {
    body = body ?: [NSData data];
    NSString *header = [NSString stringWithFormat:
        @"HTTP/1.1 %d %@\r\nContent-Type: %@\r\nContent-Length: %lu\r\nConnection: close\r\nCache-Control: no-store\r\n\r\n",
        status, statusText(status), type ?: @"application/octet-stream", (unsigned long)body.length];
    NSData *h = [header dataUsingEncoding:NSUTF8StringEncoding];
    writeAll(fd, h.bytes, h.length);
    if (body.length) writeAll(fd, body.bytes, body.length);
}

static NSDictionary *parseHeaders(NSString *headerText) {
    NSMutableDictionary *out = [NSMutableDictionary dictionary];
    NSArray<NSString *> *lines = [headerText componentsSeparatedByString:@"\r\n"];
    for (NSUInteger i = 1; i < lines.count; i++) {
        NSString *line = lines[i];
        NSRange r = [line rangeOfString:@":"];
        if (r.location == NSNotFound) continue;
        NSString *k = [[[line substringToIndex:r.location] lowercaseString] stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceCharacterSet];
        NSString *v = [[line substringFromIndex:r.location + 1] stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceCharacterSet];
        out[k] = v;
    }
    return out;
}

static BOOL readRequest(int fd, NSString **methodOut, NSString **targetOut, NSDictionary **headersOut, NSData **bodyOut) {
    NSMutableData *data = [NSMutableData data];
    const NSUInteger maxRequest = 16 * 1024 * 1024;
    NSRange headerRange = NSMakeRange(NSNotFound, 0);
    NSUInteger contentLength = 0;

    while (data.length < maxRequest) {
        uint8_t buf[8192];
        ssize_t n = recv(fd, buf, sizeof(buf), 0);
        if (n <= 0) break;
        [data appendBytes:buf length:(NSUInteger)n];
        if (headerRange.location == NSNotFound) {
            NSData *needle = [@"\r\n\r\n" dataUsingEncoding:NSASCIIStringEncoding];
            headerRange = [data rangeOfData:needle options:0 range:NSMakeRange(0, data.length)];
            if (headerRange.location != NSNotFound) {
                NSData *headData = [data subdataWithRange:NSMakeRange(0, headerRange.location)];
                NSString *head = [[NSString alloc] initWithData:headData encoding:NSUTF8StringEncoding];
                if (!head) return NO;
                NSArray<NSString *> *lines = [head componentsSeparatedByString:@"\r\n"];
                NSArray<NSString *> *parts = [lines.firstObject componentsSeparatedByString:@" "];
                if (parts.count < 2) return NO;
                *methodOut = parts[0];
                *targetOut = parts[1];
                NSDictionary *headers = parseHeaders(head);
                *headersOut = headers;
                contentLength = [headers[@"content-length"] integerValue];
            }
        }
        if (headerRange.location != NSNotFound) {
            NSUInteger bodyStart = NSMaxRange(headerRange);
            if (data.length >= bodyStart + contentLength) {
                *bodyOut = [data subdataWithRange:NSMakeRange(bodyStart, contentLength)];
                return YES;
            }
        }
    }
    return NO;
}

static BOOL pathHas(NSString *path, NSString *needle) {
    return [path rangeOfString:needle options:NSCaseInsensitiveSearch].location != NSNotFound;
}

static void handleClient(int fd) {
    @autoreleasepool {
        NSString *method = nil;
        NSString *target = nil;
        NSDictionary *headers = nil;
        NSData *body = nil;
        if (!readRequest(fd, &method, &target, &headers, &body)) {
            respond(fd, 400, @"text/plain", [@"bad request" dataUsingEncoding:NSUTF8StringEncoding]);
            close(fd);
            return;
        }

        NSString *path = [[target componentsSeparatedByString:@"?"] firstObject] ?: @"/";

        if ([path isEqualToString:@"/"] || [path isEqualToString:@"/health"]) {
            respond(fd, 200, @"application/json", jsonData(@{ @"offline": @YES, @"version": @"4.69.5", @"port": @(kOfflinePort) }));
        }
        else if ([path hasPrefix:@"/director/api/"] && (pathHas(path, @"getDirectionByBundle") || pathHas(path, @"getDirectionByPackage"))) {
            respond(fd, 200, @"application/json", jsonData(directionResponse()));
        }
        else if ([path hasPrefix:@"/user/api/"] && pathHas(path, @"getDeviceID")) {
            respond(fd, 200, @"application/json", jsonData(@{ @"deviceId": @"OFFLINE-IOS-DEVICE", @"resultCode": @0, @"serverApiVersion": @"1.0.0" }));
        }
        else if ([path hasPrefix:@"/user/api/"] && pathHas(path, @"validateDeviceID")) {
            respond(fd, 200, @"application/json", jsonData(@{ @"deviceId": @"OFFLINE-IOS-DEVICE", @"resultCode": @0, @"serverApiVersion": @"1.0.0" }));
        }
        else if ([path hasPrefix:@"/user/api/"] && pathHas(path, @"getAnonUid")) {
            respond(fd, 200, @"application/json", jsonData(@{ @"resultCode": @0, @"serverApiVersion": @"1.0.0", @"uid": @1000000000000LL }));
        }
        else if ([path isEqualToString:@"/connect/auth"] || [path hasSuffix:@"/connect/auth"]) {
            respond(fd, 200, @"application/json", jsonData(@{ @"code": kOfflineCode, @"lnglv_token": kOfflineToken }));
        }
        else if ([path isEqualToString:@"/connect/token"] || [path hasSuffix:@"/connect/token"]) {
            NSDictionary *token = @{
                @"access_token": kOfflineToken,
                @"expires_in": @368435455,
                @"id_token": @"eyJhbGciOiJub25lIn0.eyJwaWRfaWQiOiIxMDAwMDAxIiwidXNlcl9pZCI6IjEwMDAwMDEiLCJwaWRfdHlwZSI6IkFVVEhFTlRJQ0FUT1JfQU5PTllNT1VTIn0.",
                @"refresh_token": @"OFFLINE_REFRESH",
                @"refresh_token_expires_in": @368435455,
                @"token_type": @"Bearer"
            };
            respond(fd, 200, @"application/json", jsonData(token));
        }
        else if ([path isEqualToString:@"/connect/tokeninfo"] || [path hasSuffix:@"/connect/tokeninfo"]) {
            NSDictionary *info = @{
                @"client_id": @"long_live_token",
                @"expires_in": @368435455,
                @"persona_id": @1000001,
                @"pid_id": kOfflineUserId,
                @"pid_type": @"AUTHENTICATOR_ANONYMOUS",
                @"scope": @"offline basic.identity basic.persona",
                @"user_id": kOfflineUserId,
                @"is_underage": @NO,
                @"authenticators": @[ @{ @"authenticator_pid_id": @1000001, @"authenticator_type": @"AUTHENTICATOR_ANONYMOUS" } ],
                @"stopProcess": @"OFF",
                @"telemetry_id": @1000001
            };
            respond(fd, 200, @"application/json", jsonData(info));
        }
        else if ([path isEqualToString:@"/probe"] || [path hasPrefix:@"/probe/"]) {
            respond(fd, 200, @"application/json", jsonData(@{}));
        }
        else if ([path hasPrefix:@"/mh/users"]) {
            respond(fd, 200, @"application/x-protobuf", pbUsersResponse());
        }
        else if ([path isEqualToString:@"/mh/games/lobby/time"]) {
            long long ms = (long long)([[NSDate date] timeIntervalSince1970] * 1000.0);
            NSString *xml = [NSString stringWithFormat:@"<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><Time><epochMilliseconds>%lld</epochMilliseconds></Time>", ms];
            respond(fd, 200, @"application/xml", [xml dataUsingEncoding:NSUTF8StringEncoding]);
        }
        else if (pathHas(path, @"/protoClientConfig")) {
            NSData *payload = bundleResource(@"OfflineClientConfig", @"pb") ?: [NSData data];
            respond(fd, 200, @"application/x-protobuf", payload);
        }
        else if ([path hasPrefix:@"/mh/gameplayconfig"]) {
            NSData *payload = bundleResource(@"OfflineGameplayConfig", @"pb") ?: [NSData data];
            respond(fd, 200, @"application/x-protobuf", payload);
        }
        else if (pathHas(path, @"protoWholeLandToken") && !pathHas(path, @"deleteToken")) {
            respond(fd, 200, @"application/x-protobuf", pbWholeLandToken());
        }
        else if (pathHas(path, @"deleteToken") && pathHas(path, @"protoWholeLandToken")) {
            respond(fd, 200, @"application/x-protobuf", pbDeleteToken());
        }
        else if (pathHas(path, @"/protocurrency/")) {
            respond(fd, 200, @"application/x-protobuf", pbCurrencyResponse());
        }
        else if (pathHas(path, @"/protoland/")) {
            NSString *save = landSavePath();
            if ([method isEqualToString:@"GET"]) {
                NSData *saved = [NSData dataWithContentsOfFile:save];
                if (saved.length) {
                    respond(fd, 200, @"application/x-protobuf", saved);
                } else {
                    NSString *xml = @"<?xml version=\"1.0\" encoding=\"UTF-8\"?><error code=\"404\" type=\"NO_SUCH_RESOURCE\" field=\"LAND_NOT_FOUND\"/>";
                    respond(fd, 404, @"application/xml", [xml dataUsingEncoding:NSUTF8StringEncoding]);
                }
            } else {
                if (body.length) [body writeToFile:save atomically:YES];
                respond(fd, 200, @"application/x-protobuf", [NSData data]);
            }
        }
        else if ([path hasPrefix:@"/dlc/"]) {
            NSString *file = dlcPathForRequest(path);
            NSData *payload = file ? [NSData dataWithContentsOfFile:file] : nil;
            if (payload) respond(fd, 200, @"application/octet-stream", payload);
            else respond(fd, 404, @"text/plain", [@"offline dlc missing" dataUsingEncoding:NSUTF8StringEncoding]);
        }
        else if (pathHas(path, @"friendData") || pathHas(path, @"tracking") || pathHas(path, @"telemetry") || pathHas(path, @"userstats") || pathHas(path, @"link")) {
            respond(fd, 200, @"application/octet-stream", [NSData data]);
        }
        else {
            NSString *accept = headers[@"accept"] ?: @"";
            if (pathHas(accept, @"application/x-protobuf")) {
                respond(fd, 200, @"application/x-protobuf", [NSData data]);
            } else {
                respond(fd, 200, @"application/json", jsonData(@{}));
            }
        }

        close(fd);
    }
}

static void serverLoop(void) {
    @autoreleasepool {
        int server = socket(AF_INET, SOCK_STREAM, 0);
        if (server < 0) return;
        int yes = 1;
        setsockopt(server, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof(yes));

        struct sockaddr_in addr;
        memset(&addr, 0, sizeof(addr));
        addr.sin_family = AF_INET;
        addr.sin_port = htons(kOfflinePort);
        addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        if (bind(server, (struct sockaddr *)&addr, sizeof(addr)) != 0) {
            close(server);
            return;
        }
        if (listen(server, 16) != 0) {
            close(server);
            return;
        }

        for (;;) {
            int client = accept(server, NULL, NULL);
            if (client < 0) continue;
            dispatch_async(dispatch_get_global_queue(QOS_CLASS_UTILITY, 0), ^{
                handleClient(client);
            });
        }
    }
}

static void startOfflineServer(void) {
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED, 0), ^{
        serverLoop();
    });
}

#ifndef TSTO_OFFLINE_STANDALONE
__attribute__((constructor)) static void TSTOOfflineConstructor(void) {
    startOfflineServer();
}
#else
int main(int argc, const char *argv[]) {
    @autoreleasepool {
        startOfflineServer();
        fprintf(stdout, "TSTO embedded offline server listening on 127.0.0.1:%u\n", kOfflinePort);
        fflush(stdout);
        [[NSRunLoop currentRunLoop] run];
    }
    return 0;
}
#endif
