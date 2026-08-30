#!/usr/bin/env python3
import argparse
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def main():
    ap = argparse.ArgumentParser(description="Upgrade OfflineServer.m with local DLC import, streaming and range support")
    ap.add_argument("input")
    ap.add_argument("output")
    args = ap.parse_args()

    text = Path(args.input).read_text()
    text = replace_once(
        text,
        '#include <sys/socket.h>\n#include <sys/stat.h>\n#include <unistd.h>\n',
        '#include <sys/socket.h>\n#include <sys/stat.h>\n#include <fcntl.h>\n#include <unistd.h>\n',
        'headers',
    )

    old = '''static NSString *dlcPathForRequest(NSString *path) {
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
'''
    new = '''static NSString *documentsDirectory(void) {
    NSArray<NSURL *> *urls = [[NSFileManager defaultManager] URLsForDirectory:NSDocumentDirectory inDomains:NSUserDomainMask];
    NSURL *base = urls.firstObject ?: [NSURL fileURLWithPath:NSTemporaryDirectory() isDirectory:YES];
    return base.path;
}

static NSString *importDlcDirectory(void) {
    const char *override = getenv("TSTO_OFFLINE_DLC_ROOT");
    if (override && override[0]) return [NSString stringWithUTF8String:override];
    return [documentsDirectory() stringByAppendingPathComponent:@"TSTOOfflineDLC"];
}

static void ensureDlcImportArea(void) {
    NSFileManager *fm = [NSFileManager defaultManager];
    NSString *root = importDlcDirectory();
    [fm createDirectoryAtPath:root withIntermediateDirectories:YES attributes:nil error:nil];
    NSString *readme = [root stringByAppendingPathComponent:@"README-OFFLINE-DLC.txt"];
    if (![fm fileExistsAtPath:readme]) {
        NSString *text = @"Tapped Out offline DLC import directory.\\n\\nCopy the contents of your own cached/backed-up TSTO DLC tree into this folder while preserving its relative directories. The embedded server serves it at http://127.0.0.1:31337/dlc/. Files here override the application-support and bundled DLC copies.\\n";
        [text writeToFile:readme atomically:YES encoding:NSUTF8StringEncoding error:nil];
    }
    NSString *cache = [stateDirectory() stringByAppendingPathComponent:@"dlc"];
    [fm createDirectoryAtPath:cache withIntermediateDirectories:YES attributes:nil error:nil];
}

static NSArray<NSString *> *dlcRoots(void) {
    return @[
        importDlcDirectory(),
        [stateDirectory() stringByAppendingPathComponent:@"dlc"],
        [[[NSBundle mainBundle] resourcePath] stringByAppendingPathComponent:@"OfflineDLC"]
    ];
}

static NSString *safeRelativeDlcPath(NSString *path) {
    NSString *rel = path;
    if ([rel hasPrefix:@"/dlc/"]) rel = [rel substringFromIndex:5];
    while ([rel hasPrefix:@"/"]) rel = [rel substringFromIndex:1];
    rel = [rel stringByRemovingPercentEncoding] ?: rel;
    rel = [rel stringByReplacingOccurrencesOfString:@"\\\\" withString:@"/"];
    if (rel.length == 0 || [rel hasPrefix:@"/"]) return nil;
    NSArray<NSString *> *parts = [rel componentsSeparatedByString:@"/"];
    for (NSString *part in parts) {
        if ([part isEqualToString:@".."] || [part isEqualToString:@"."] || part.length == 0) return nil;
    }
    return rel;
}

static NSString *dlcPathForRequest(NSString *path) {
    NSString *rel = safeRelativeDlcPath(path);
    if (!rel) return nil;
    NSFileManager *fm = [NSFileManager defaultManager];
    for (NSString *root in dlcRoots()) {
        NSString *standardRoot = [root stringByStandardizingPath];
        NSString *candidate = [[root stringByAppendingPathComponent:rel] stringByStandardizingPath];
        if (![candidate hasPrefix:[standardRoot stringByAppendingString:@"/"]]) continue;
        BOOL isDir = NO;
        if ([fm fileExistsAtPath:candidate isDirectory:&isDir] && !isDir) return candidate;
    }
    return nil;
}

static NSDictionary *dlcStats(void) {
    NSFileManager *fm = [NSFileManager defaultManager];
    unsigned long long files = 0;
    unsigned long long bytes = 0;
    NSMutableArray *roots = [NSMutableArray array];
    for (NSString *root in dlcRoots()) {
        BOOL isDir = NO;
        BOOL exists = [fm fileExistsAtPath:root isDirectory:&isDir] && isDir;
        unsigned long long rootFiles = 0;
        unsigned long long rootBytes = 0;
        if (exists) {
            NSDirectoryEnumerator *it = [fm enumeratorAtPath:root];
            for (NSString *rel in it) {
                NSString *p = [root stringByAppendingPathComponent:rel];
                NSDictionary *a = [fm attributesOfItemAtPath:p error:nil];
                if ([a[NSFileType] isEqualToString:NSFileTypeRegular]) {
                    rootFiles++;
                    rootBytes += [a[NSFileSize] unsignedLongLongValue];
                }
            }
        }
        files += rootFiles;
        bytes += rootBytes;
        [roots addObject:@{ @"path": root, @"exists": @(exists), @"files": @(rootFiles), @"bytes": @(rootBytes) }];
    }
    return @{ @"files": @(files), @"bytes": @(bytes), @"roots": roots, @"importRoot": importDlcDirectory() };
}
'''
    text = replace_once(text, old, new, 'dlc path helper')

    old = '''static NSString *statusText(int status) {
    switch (status) {
        case 200: return @"OK";
        case 204: return @"No Content";
        case 400: return @"Bad Request";
        case 404: return @"Not Found";
        case 500: return @"Internal Server Error";
        default: return @"OK";
    }
}
'''
    new = '''static NSString *statusText(int status) {
    switch (status) {
        case 200: return @"OK";
        case 204: return @"No Content";
        case 206: return @"Partial Content";
        case 400: return @"Bad Request";
        case 404: return @"Not Found";
        case 416: return @"Range Not Satisfiable";
        case 500: return @"Internal Server Error";
        default: return @"OK";
    }
}
'''
    text = replace_once(text, old, new, 'status text')

    marker = '''static NSDictionary *parseHeaders(NSString *headerText) {'''
    helper = r'''static NSString *mimeTypeForPath(NSString *path) {
    NSString *ext = path.pathExtension.lowercaseString;
    if ([ext isEqualToString:@"json"]) return @"application/json";
    if ([ext isEqualToString:@"xml"]) return @"application/xml";
    if ([ext isEqualToString:@"txt"]) return @"text/plain";
    if ([ext isEqualToString:@"png"]) return @"image/png";
    if ([ext isEqualToString:@"jpg"] || [ext isEqualToString:@"jpeg"]) return @"image/jpeg";
    if ([ext isEqualToString:@"gz"]) return @"application/gzip";
    if ([ext isEqualToString:@"zip"]) return @"application/zip";
    return @"application/octet-stream";
}

static void respondFile(int fd, NSString *path, NSDictionary *headers, BOOL headOnly) {
    NSDictionary *attrs = [[NSFileManager defaultManager] attributesOfItemAtPath:path error:nil];
    unsigned long long size = [attrs[NSFileSize] unsignedLongLongValue];
    if (!attrs || size == 0) {
        if (attrs && size == 0) {
            NSString *h = [NSString stringWithFormat:@"HTTP/1.1 200 OK\r\nContent-Type: %@\r\nContent-Length: 0\r\nAccept-Ranges: bytes\r\nConnection: close\r\n\r\n", mimeTypeForPath(path)];
            NSData *hd = [h dataUsingEncoding:NSUTF8StringEncoding];
            writeAll(fd, hd.bytes, hd.length);
            return;
        }
        respond(fd, 404, @"text/plain", [@"offline dlc missing" dataUsingEncoding:NSUTF8StringEncoding]);
        return;
    }

    unsigned long long start = 0;
    unsigned long long end = size - 1;
    BOOL partial = NO;
    NSString *range = headers[@"range"];
    if ([range hasPrefix:@"bytes="]) {
        NSString *spec = [range substringFromIndex:6];
        NSString *first = [[spec componentsSeparatedByString:@","] firstObject];
        NSArray<NSString *> *parts = [first componentsSeparatedByString:@"-"];
        if (parts.count == 2) {
            NSString *a = parts[0];
            NSString *b = parts[1];
            if (a.length) start = strtoull(a.UTF8String, NULL, 10);
            if (b.length) end = strtoull(b.UTF8String, NULL, 10);
            else end = size - 1;
            if (start >= size || end < start) {
                NSString *h = [NSString stringWithFormat:@"HTTP/1.1 416 Range Not Satisfiable\r\nContent-Range: bytes */%llu\r\nContent-Length: 0\r\nConnection: close\r\n\r\n", size];
                NSData *hd = [h dataUsingEncoding:NSUTF8StringEncoding];
                writeAll(fd, hd.bytes, hd.length);
                return;
            }
            if (end >= size) end = size - 1;
            partial = YES;
        }
    }

    unsigned long long length = end - start + 1;
    NSMutableString *h = [NSMutableString stringWithFormat:
        @"HTTP/1.1 %d %@\r\nContent-Type: %@\r\nContent-Length: %llu\r\nAccept-Ranges: bytes\r\nConnection: close\r\nCache-Control: public, max-age=31536000, immutable\r\n",
        partial ? 206 : 200, statusText(partial ? 206 : 200), mimeTypeForPath(path), length];
    if (partial) [h appendFormat:@"Content-Range: bytes %llu-%llu/%llu\r\n", start, end, size];
    [h appendString:@"\r\n"];
    NSData *hd = [h dataUsingEncoding:NSUTF8StringEncoding];
    writeAll(fd, hd.bytes, hd.length);
    if (headOnly) return;

    int filefd = open(path.fileSystemRepresentation, O_RDONLY);
    if (filefd < 0) return;
    if (lseek(filefd, (off_t)start, SEEK_SET) < 0) { close(filefd); return; }
    unsigned long long remaining = length;
    uint8_t buf[64 * 1024];
    while (remaining > 0) {
        size_t want = remaining < sizeof(buf) ? (size_t)remaining : sizeof(buf);
        ssize_t n = read(filefd, buf, want);
        if (n <= 0) break;
        writeAll(fd, buf, (size_t)n);
        remaining -= (unsigned long long)n;
    }
    close(filefd);
}

'''
    if marker not in text:
        raise SystemExit('parseHeaders marker missing')
    text = text.replace(marker, helper + marker, 1)

    old = '''        else if ([path hasPrefix:@"/dlc/"]) {
            NSString *file = dlcPathForRequest(path);
            NSData *payload = file ? [NSData dataWithContentsOfFile:file] : nil;
            if (payload) respond(fd, 200, @"application/octet-stream", payload);
            else respond(fd, 404, @"text/plain", [@"offline dlc missing" dataUsingEncoding:NSUTF8StringEncoding]);
        }
'''
    new = '''        else if ([path isEqualToString:@"/offline/dlc/status"]) {
            NSMutableDictionary *status = [NSMutableDictionary dictionaryWithDictionary:dlcStats()];
            status[@"offline"] = @YES;
            status[@"baseURL"] = [kOfflineBase stringByAppendingString:@"/dlc/"];
            respond(fd, 200, @"application/json", jsonData(status));
        }
        else if ([path hasPrefix:@"/dlc/"]) {
            NSString *file = dlcPathForRequest(path);
            if (!file) {
                respond(fd, 404, @"text/plain", [@"offline dlc missing" dataUsingEncoding:NSUTF8StringEncoding]);
            } else if ([method isEqualToString:@"GET"] || [method isEqualToString:@"HEAD"]) {
                respondFile(fd, file, headers, [method isEqualToString:@"HEAD"]);
            } else {
                respond(fd, 400, @"text/plain", [@"unsupported dlc method" dataUsingEncoding:NSUTF8StringEncoding]);
            }
        }
'''
    text = replace_once(text, old, new, 'dlc handler')

    old = '''static void startOfflineServer(void) {
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED, 0), ^{
        serverLoop();
    });
}
'''
    new = '''static void startOfflineServer(void) {
    ensureDlcImportArea();
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED, 0), ^{
        serverLoop();
    });
}
'''
    text = replace_once(text, old, new, 'server startup')

    Path(args.output).write_text(text)
    print(f"wrote {args.output}")
    print("DLC import + streaming + HEAD + Range support enabled")


if __name__ == "__main__":
    main()
