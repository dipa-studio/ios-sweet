/* Explicit, reversible development-identity experiment on the volatile verified whyred97/98 cache.
 * Does not advertise a Wi-Fi controller or change any persistent partition. */
#import <Foundation/Foundation.h>
#import <TargetConditionals.h>
#include <CommonCrypto/CommonDigest.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/sysctl.h>
#include <uuid/uuid.h>
#include <unistd.h>
#include <dlfcn.h>
#include <time.h>

static NSString *const cachePath = @"/private/var/containers/Shared/SystemGroup/systemgroup.com.apple.mobilegestaltcache/Library/Caches/com.apple.MobileGestalt.plist";
static NSString *const dataKey = @"nFRqKto/RuQAV1P+0/qkBA";
static NSString *const textKey = @"re6Zb+zwFKJNlkQTUeT+/w";

static NSString *hex(const unsigned char *bytes, size_t n) {
    NSMutableString *s = [NSMutableString stringWithCapacity:n * 2];
    for (size_t i = 0; i < n; i++) [s appendFormat:@"%02x", bytes[i]];
    return s;
}
static NSString *digest(NSData *data) {
    unsigned char bytes[CC_SHA256_DIGEST_LENGTH];
    CC_SHA256(data.bytes, (CC_LONG)data.length, bytes); return hex(bytes, sizeof(bytes));
}
static NSData *developmentID(void) {
    /* Read the existing platform UUID directly. gethostuuid is unavailable in
     * the iOS SDK and can apply process-specific fallback policy. */
    uuid_t uuid = {0}, zero = {0};
    void *library = dlopen("/System/Library/Frameworks/IOKit.framework/Versions/A/IOKit", RTLD_NOW | RTLD_LOCAL);
    CFMutableDictionaryRef (*matching)(const char *) = library ? dlsym(library, "IOServiceMatching") : NULL;
    uint32_t (*serviceForMatch)(uint32_t, CFDictionaryRef) = library ? dlsym(library, "IOServiceGetMatchingService") : NULL;
    CFTypeRef (*property)(uint32_t, CFStringRef, CFAllocatorRef, uint32_t) = library ? dlsym(library, "IORegistryEntryCreateCFProperty") : NULL;
    int (*releaseService)(uint32_t) = library ? dlsym(library, "IOObjectRelease") : NULL;
    if (!matching || !serviceForMatch || !property || !releaseService) { if (library) dlclose(library); return nil; }
    CFMutableDictionaryRef match = matching("IOPlatformExpertDevice");
    uint32_t service = match ? serviceForMatch(0, match) : 0;
    id value = service ? CFBridgingRelease(property(service, CFSTR("IOPlatformUUID"), kCFAllocatorDefault, 0)) : nil;
    if (service) releaseService(service);
    dlclose(library);
    if (![value isKindOfClass:NSString.class]) return nil;
    NSUUID *platform = [[NSUUID alloc] initWithUUIDString:value];
    if (!platform) return nil;
    [platform getUUIDBytes:uuid];
    if (!memcmp(uuid, zero, sizeof(uuid))) return nil;
    NSMutableData *input = [[@"whyred-development-identity-v1:" dataUsingEncoding:NSUTF8StringEncoding] mutableCopy];
    [input appendBytes:uuid length:sizeof(uuid)];
    unsigned char bytes[CC_SHA1_DIGEST_LENGTH];
    CC_SHA1(input.bytes, (CC_LONG)input.length, bytes);
    return [NSData dataWithBytes:bytes length:sizeof(bytes)];
}
static NSDictionary *parse(NSData *data) {
    if (!data || data.length > 1024 * 1024) return nil;
    id value = [NSPropertyListSerialization propertyListWithData:data options:0 format:NULL error:NULL];
    if (![value isKindOfClass:NSDictionary.class]) return nil;
    NSDictionary *d = value;
    if (![d[@"CacheVersion"] isEqual:@"20F66"] ||
        ![d[@"CacheUUID"] isKindOfClass:NSString.class] ||
        ![d[@"CacheData"] isKindOfClass:NSData.class] ||
        ![d[@"CacheExtra"] isKindOfClass:NSDictionary.class]) return nil;
    return d;
}
static BOOL atomicWrite(NSData *data, NSString *path, const struct stat *original) {
    NSError *error = nil;
    if (![data writeToFile:path options:NSDataWritingAtomic error:&error]) {
        fprintf(stderr, "GESTALT: atomic write failed: %s\n", error.localizedDescription.UTF8String); return NO;
    }
    return !chown(path.fileSystemRepresentation, original->st_uid, original->st_gid) &&
        !chmod(path.fileSystemRepresentation, original->st_mode & 0777);
}
static int experiment(const char *mode, const char *expected) {
#if !TARGET_OS_IPHONE || TARGET_OS_SIMULATOR
    (void)mode; (void)expected;
    puts("GESTALT: requires the physical iOS target"); return 1;
#endif
    char uuid[80] = {0}; size_t size = sizeof(uuid);
    if (sysctlbyname("kern.uuid", uuid, &size, NULL, 0) || (strcmp(uuid, "1444AADE-E57B-3F55-88A9-866FFA6086A0") &&
        strcmp(uuid, "936C980F-9428-33A1-B076-CDB09ABDC855"))) return 1;
    NSData *identity = developmentID(); if (!identity) { puts("GESTALT: no platform host UUID"); return 1; }
    NSString *identityText = hex(identity.bytes, identity.length);
    if (!strcmp(mode, "probe")) {
        void *library = dlopen("/usr/lib/libMobileGestalt.dylib", RTLD_NOW | RTLD_LOCAL);
        CFTypeRef (*copyAnswer)(CFStringRef) = library ? dlsym(library, "MGCopyAnswer") : NULL;
        if (!copyAnswer) return 1;
        struct timespec before, after; clock_gettime(CLOCK_MONOTONIC, &before);
        id a = CFBridgingRelease(copyAnswer(CFSTR("UniqueDeviceID")));
        id b = CFBridgingRelease(copyAnswer(CFSTR("UniqueDeviceIDData")));
        clock_gettime(CLOCK_MONOTONIC, &after);
        BOOL matches = [a isKindOfClass:NSString.class] && [a isEqual:identityText] &&
            [b isKindOfClass:NSData.class] && [b isEqual:identity];
        double elapsed = after.tv_sec - before.tv_sec + (after.tv_nsec - before.tv_nsec) / 1e9;
        printf("GESTALT: development_identity_matches=%d elapsed_ms=%.3f values_printed=0\n", matches, elapsed * 1000);
        dlclose(library); return matches ? 0 : 1;
    }
    if (geteuid() != 0 || !expected || strlen(expected) != 64) return 2;
    struct statfs fs; struct stat st;
    if (statfs(cachePath.fileSystemRepresentation, &fs) || strcmp(fs.f_fstypename, "whyredramfs") ||
        lstat(cachePath.fileSystemRepresentation, &st) || !S_ISREG(st.st_mode) || st.st_nlink != 1 || st.st_size > 1024 * 1024) return 1;
    NSData *old = [NSData dataWithContentsOfFile:cachePath]; NSDictionary *d = parse(old);
    if (!d || ![digest(old) isEqual:[NSString stringWithUTF8String:expected]]) {
        puts("GESTALT: current cache guard mismatch"); return 1;
    }
    NSString *backup = [cachePath stringByAppendingString:@".whyred-original"];
    if (!strcmp(mode, "rollback")) {
        NSData *original = [NSData dataWithContentsOfFile:backup];
        if (!parse(original) || !atomicWrite(original, cachePath, &st)) return 1;
        puts("GESTALT: original volatile cache restored"); return 0;
    }
    if (strcmp(mode, "seed")) return 2;
    if ([[NSFileManager defaultManager] fileExistsAtPath:backup]) {
        puts("GESTALT: original backup already exists; refusing replacement"); return 1;
    }
    NSDictionary *extra = d[@"CacheExtra"];
    if (extra[dataKey] || extra[textKey]) { puts("GESTALT: existing device identity preserved"); return 1; }
    NSMutableDictionary *newExtra = [extra mutableCopy]; newExtra[dataKey] = identity; newExtra[textKey] = identityText;
    NSMutableDictionary *updated = [d mutableCopy]; updated[@"CacheExtra"] = newExtra;
    NSData *replacement = [NSPropertyListSerialization dataWithPropertyList:updated format:NSPropertyListBinaryFormat_v1_0 options:0 error:NULL];
    if (!parse(replacement) || !atomicWrite(old, backup, &st)) return 1;
    if (!atomicWrite(replacement, cachePath, &st)) { atomicWrite(old, cachePath, &st); return 1; }
    NSData *verify = [NSData dataWithContentsOfFile:cachePath];
    if (![verify isEqual:replacement]) { atomicWrite(old, cachePath, &st); return 1; }
    printf("GESTALT: volatile development identity seeded keys_added=2 preserved_fields=3 sha256=%s\n", digest(verify).UTF8String);
    return 0;
}
int main(int argc, const char **argv) {
    @autoreleasepool {
        if (argc == 2 && !strcmp(argv[1], "probe")) return experiment(argv[1], NULL);
        if (argc == 3 && (!strcmp(argv[1], "seed") || !strcmp(argv[1], "rollback"))) return experiment(argv[1], argv[2]);
        fprintf(stderr, "usage: whyred-gestalt-cache probe | seed CURRENT_SHA256 | rollback CURRENT_SHA256\n"); return 2;
    }
}
