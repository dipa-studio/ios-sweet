# Redwood userland build for iOS 16.7.16

This directory carries the ios-sweet overlay for the supplied HackiOS Redwood
libraries. The overlay targets iPhone10,3 / iOS 16.7.16 (20H392), whose matching
dyld shared cache is already in the local research workspace. The kernel and
root filesystem remain separate build inputs.

`patches/20H392-redwood.patch` is applied to the pinned public
`oosexgang/hackios-xnu-userland` source revision by the GitHub Actions workflow.
The workflow builds only `libredwood.dylib` and `libredwood-sb.dylib` for arm64
and uploads them as `redwood-20H392`. It does not fetch an IPSW or modify an
iOS disk image.

The patch keeps address checks in place. Objective-C IMPs and QuartzCore slots
were matched against the 20H392 dyld cache; the `begin_update` and
`finish_update` vtable entries have moved relative to 20F66. The optional Siri
orb hook remains guarded to 20F66 and is intentionally inactive until its
20H392 implementation address is resolved.
