#!/usr/bin/env python3
"""Run the exact whyred RFC3394 helper and call boundary with guarded host buffers.

Uses the already staged BearSSL AES code that backs this board's kernel AES API.
Fixed public test keys exist only in this host harness, never in the kernel patch.
"""
import argparse
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source', type=Path)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    src, out = args.source.resolve(), args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    arm = src / 'iokit/Kernel/arm'
    bear = src / 'libkern/crypto/sweet_bearssl'
    cpp = (arm / 'SweetKeyStore.cpp').read_text()
    start = cpp.index('static int\nwhyred_aks_encrypt(')
    boundary = cpp[start:cpp.index('\n#endif', start)]
    shim = r'''
#include <stddef.h>
#include <stdint.h>
extern "C" {
#include "bearssl_block.h"
void *memcpy(void *d,const void *s,size_t n) { for(size_t i=0;i<n;i++) ((char*)d)[i]=((const char*)s)[i];return d; }
void *memmove(void *d,const void *s,size_t n) { if((uintptr_t)d<(uintptr_t)s)return memcpy(d,s,n);for(size_t i=n;i>0;i--)((char*)d)[i-1]=((const char*)s)[i-1];return d; }
void *memset(void *d,int v,size_t n) { for(size_t i=0;i<n;i++)((char*)d)[i]=(char)v;return d; }
}
#include "SweetKeyStoreWrap.h"
typedef br_aes_ct_cbcenc_keys aes_encrypt_ctx;
typedef br_aes_ct_cbcdec_keys aes_decrypt_ctx;
struct aes_ctx { aes_decrypt_ctx decrypt; aes_encrypt_ctx encrypt; };
enum { aes_good=0 };
static int aes_encrypt_key256(const uint8_t *k,aes_encrypt_ctx *c) {br_aes_ct_cbcenc_init(c,k,32);return 0;}
static int aes_decrypt_key256(const uint8_t *k,aes_decrypt_ctx *c) {br_aes_ct_cbcdec_init(c,k,32);return 0;}
static int aes_encrypt(const uint8_t *i,uint8_t *o,aes_encrypt_ctx *c) {uint8_t iv[16]={0};memmove(o,i,16);br_aes_ct_cbcenc_run(c,iv,o,16);return 0;}
static int aes_decrypt(const uint8_t *i,uint8_t *o,aes_decrypt_ctx *c) {uint8_t iv[16]={0};memmove(o,i,16);br_aes_ct_cbcdec_run(c,iv,o,16);return 0;}
typedef int IOReturn;
enum {kIOReturnSuccess=0,kIOReturnBadArgument=-1,kIOReturnNoSpace=-2,kIOReturnUnderrun=-3,kIOReturnError=-4,kIOReturnNotPermitted=-5,kIOReturnUnsupported=-6};
#define SWEET_AKS_SYSTEM_HANDLE 0
static bool test_enabled = true;
class AppleKeyStore { uint8_t keys[12][32]; public:
 AppleKeyStore(){for(unsigned c=0;c<12;c++)for(unsigned i=0;i<32;i++)keys[c][i]=(uint8_t)(i+37*c);}
 bool volatileWrapEnabled() const {return test_enabled;}
 const uint8_t *wrapKey(uint32_t c) const {return c>=1&&c<=12?keys[c-1]:NULL;}
};
struct Descriptor {
 uint8_t *bytes; uint64_t length; uint64_t limit;
 uint64_t getLength(){return length;}
 uint64_t readBytes(uint64_t off,void *d,uint64_t n){if(n>limit)n=limit;memcpy(d,bytes+off,(size_t)n);return n;}
 uint64_t writeBytes(uint64_t off,const void *s,uint64_t n){if(n>limit)n=limit;memcpy(bytes+off,s,(size_t)n);return n;}
};
struct IOExternalMethodArguments {
 const uint64_t *scalarInput; uint32_t scalarInputCount;
 const void *structureInput; uint32_t structureInputSize; Descriptor *structureInputDescriptor;
 uint64_t *scalarOutput; uint32_t scalarOutputCount;
 void *structureOutput; uint32_t structureOutputSize; Descriptor *structureOutputDescriptor;
 uint32_t structureOutputDescriptorSize;
};
'''
    exports = r'''
#ifdef _WIN32
#define EXPORT extern "C" __declspec(dllexport)
#else
#define EXPORT extern "C"
#endif
EXPORT int kw(int unwrap,const uint8_t *k,uint32_t kl,const uint8_t *i,uint32_t il,uint8_t *o,uint32_t cap,uint32_t *ol) {
 aes_ctx c;int r;
 if(unwrap){br_aes_ct_cbcdec_init(&c.decrypt,k,kl);r=sweet_aks_kw(unwrap,whyred_aks_decrypt,&c.decrypt,i,il,o,cap,ol);}
 else {br_aes_ct_cbcenc_init(&c.encrypt,k,kl);r=sweet_aks_kw(unwrap,whyred_aks_encrypt,&c.encrypt,i,il,o,cap,ol);}
 sweet_aks_clear(&c,sizeof(c));return r;
}
EXPORT int abi(IOExternalMethodArguments *a,int unwrap,int nullstore) {AppleKeyStore s;test_enabled=nullstore!=2;return whyred_aks_wrap(nullstore==1?NULL:&s,a,unwrap);}
static int broken(void *,const uint8_t *,uint8_t *) {return -1;}
EXPORT int crypto_failure(const uint8_t *i,uint8_t *o,uint32_t *ol) {int c=0;return sweet_aks_kw(0,broken,&c,i,32,o,40,ol);}
'''
    wrapper = out / 'aks-wrapper.cpp'
    wrapper.write_text(shim + boundary + exports, encoding='utf-8')
    cc = os.environ.get('CC') or shutil.which('clang') or 'cc'
    # Minimal declarations suffice for the freestanding staged AES source.
    # Keep this local to the harness so Windows needs no installed C runtime SDK.
    (out/'string.h').write_text('#include <stddef.h>\nvoid *memcpy(void *,const void *,size_t);\nvoid *memmove(void *,const void *,size_t);\nvoid *memset(void *,int,size_t);\n',encoding='utf-8')
    common = ['-I', str(out), '-O2' , '-ffreestanding', '-fno-builtin', '-fno-stack-protector', '-I', str(bear/'inc'), '-I', str(bear/'src'), '-I', str(arm)]
    env = os.environ.copy()
    env.pop('SDKROOT', None)
    env.pop('MACOSX_DEPLOYMENT_TARGET', None)
    if sys.platform == 'darwin':
        sdk = subprocess.check_output(['xcrun', '--sdk', 'macosx', '--show-sdk-path'],
                                      text=True, env=env).strip()
        common += ['-isysroot', sdk]
    if sys.platform != 'win32': common += ['-fPIC']
    else: common += ['--target=x86_64-pc-windows-msvc']
    objects = []
    for name in ('aes_ct','aes_ct_enc','aes_ct_dec','aes_ct_cbcenc','aes_ct_cbcdec'):
        obj = out/(name+'.o')
        subprocess.run([cc, *common, '-c', str(bear/'src/symcipher'/(name+'.c')), '-o', str(obj)], check=True, env=env)
        objects.append(str(obj))
    for name in ('dec32le','enc32le','dec32be','enc32be'):
        obj = out/(name+'.o')
        subprocess.run([cc, *common, '-c', str(bear/'src/codec'/(name+'.c')), '-o', str(obj)], check=True, env=env)
        objects.append(str(obj))
    library = out/('aks.dll' if sys.platform == 'win32' else 'aks.so')
    command = [cc, *common, '-std=c++17', '-fno-exceptions', '-fno-rtti', '-shared', str(wrapper), *objects, '-o', str(library)]
    if sys.platform == 'win32': command += ['-nostdlib', '-fuse-ld=lld', '-Wl,/noentry', '-Wl,/nodefaultlib']
    subprocess.run(command, check=True, env=env)
    lib = C.CDLL(str(library))
    U8P, U32P = C.POINTER(C.c_uint8), C.POINTER(C.c_uint32)
    lib.kw.argtypes = [C.c_int,U8P,C.c_uint32,U8P,C.c_uint32,U8P,C.c_uint32,U32P]
    lib.kw.restype = C.c_int
    checks = []
    def kw(unwrap, key, data, capacity=None, declared=None):
        buf = bytearray([0xCD]*112)
        dest = (C.c_uint8*len(buf)).from_buffer(buf)
        kp=(C.c_uint8*len(key)).from_buffer_copy(key)
        ip=(C.c_uint8*len(data)).from_buffer_copy(data)
        length=C.c_uint32(999)
        ret=lib.kw(unwrap,kp,len(key),ip,len(data) if declared is None else declared,C.cast(C.byref(dest,16),U8P),80 if capacity is None else capacity,C.byref(length))
        assert buf[:16]==b'\xcd'*16 and buf[96:]==b'\xcd'*16
        if ret: assert length.value==0 and buf==b'\xcd'*112
        else: assert buf[16+length.value:]==b'\xcd'*(96-length.value)
        return ret,bytes(buf[16:16+length.value])
    # RFC3394 sections 4.1,4.2,4.3,4.6 (public known-answer vectors).
    for kh, ph, wh in [
        ('000102030405060708090a0b0c0d0e0f','00112233445566778899aabbccddeeff','1fa68b0a8112b447aef34bd8fb5a7b829d3e862371d2cfe5'),
        ('000102030405060708090a0b0c0d0e0f1011121314151617','00112233445566778899aabbccddeeff','96778b25ae6ca435f92b5b97c050aed2468ab8a17ad84e5d'),
        ('000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f','00112233445566778899aabbccddeeff','64e8c3f9ce0f5ba263e9777905818a2a93c8191e7d6e8ae7'),
        ('000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f','00112233445566778899aabbccddeeff000102030405060708090a0b0c0d0e0f','28c9f404c4b810f4cbccb35cfb87f8263f5786e2d80ed326cbc7f0e71a99f43bfb988b9b7a02dd21')]:
        k,p,w=map(bytes.fromhex,(kh,ph,wh))
        assert kw(0,k,p)==(0,w)
        assert kw(1,k,w)==(0,p)
        checks.append('RFC3394 KAT '+str(len(k)*8)+'/'+str(len(p)*8))
    k=bytes(range(32)); plain=bytes(range(32)); _,wrapped=kw(0,k,plain)
    for n in (16,24,32,40,48,56,64):
        p=bytes(range(n));r,w=kw(0,k,p,capacity=n+8);assert r==0
        assert kw(1,k,w,capacity=n)==(0,p)
    checks.append('all supported lengths and exact capacities')
    for index in range(len(wrapped)):
        for bit in range(8):
            bad=bytearray(wrapped);bad[index]^=1<<bit
            assert kw(1,k,bad)[0]==-4
    assert kw(1,bytes(reversed(k)),wrapped)[0]==-4
    checks.append('320 single-bit modifications and wrong KEK rejected without plaintext')
    for un in (0,1):
        for n in range(89):
            if n%8 or n<(24 if un else 16) or n>(72 if un else 64):assert kw(un,k,bytes(96),declared=n)[0]==-1
        for n in (2**32-1,2**32-8):assert kw(un,k,bytes(96),declared=n)[0]==-1
    assert kw(0,k,plain,39)[0]==-2
    assert kw(1,k,wrapped,31)[0]==-2
    checks.append('malformed/overflow lengths and short output rejected')
    ol=C.c_uint32(999);inbuf=(C.c_uint8*32).from_buffer_copy(plain);outbuf=(C.c_uint8*40)(*([0xCD]*40))
    lib.crypto_failure.argtypes=[U8P,U8P,U32P]
    assert lib.crypto_failure(inbuf,outbuf,C.byref(ol))==-3 and ol.value==0 and bytes(outbuf)==b'\xcd'*40
    checks.append('AES callback failure leaves output unchanged')
    class Descriptor(C.Structure): _fields_=[('bytes',U8P),('length',C.c_uint64),('limit',C.c_uint64)]
    class Args(C.Structure): _fields_=[('si',C.POINTER(C.c_uint64)),('sic',C.c_uint32),('inp',C.c_void_p),('ins',C.c_uint32),('ind',C.POINTER(Descriptor)),('so',C.POINTER(C.c_uint64)),('soc',C.c_uint32),('out',C.c_void_p),('outs',C.c_uint32),('outd',C.POINTER(Descriptor)),('outds',C.c_uint32)]
    lib.abi.argtypes=[C.POINTER(Args),C.c_int,C.c_int]
    def abi(un,data,desc=False,bag=0,cls=6,capacity=80,sic=2,soc=None,shortread=False,shortwrite=False,nullstore=0):
        ib=(C.c_uint8*len(data)).from_buffer_copy(data);ob=(C.c_uint8*112)(*([0xCD]*112))
        si=(C.c_uint64*2)(bag,cls);so=(C.c_uint64*1)(999)
        op=C.cast(C.byref(ob,16),U8P)
        di=Descriptor(ib,len(data),len(data)-int(shortread));do=Descriptor(op,capacity,capacity if not shortwrite else 1)
        a=Args(si,sic,C.cast(ib,C.c_void_p),len(data),C.pointer(di) if desc else None,so,(0 if un else 1) if soc is None else soc,C.cast(op,C.c_void_p),capacity,C.pointer(do) if desc else None,0)
        r=lib.abi(C.byref(a),un,nullstore)
        n=a.outds if desc else a.outs
        assert bytes(ob[:16])==b'\xcd'*16 and bytes(ob[96:])==b'\xcd'*16
        if r:
            assert n==0 and a.soc==0 and so[0]==999
            if not shortwrite:assert bytes(ob)==b'\xcd'*112
        else:
            assert a.soc==(0 if un else 1)
            if not un:assert so[0]==cls
        return r,bytes(ob[16:16+n])
    for desc in (False,True):
        for cls in range(1,13):
            r,w=abi(0,plain,desc,cls=cls,capacity=40);assert r==0 and len(w)==40 and w!=plain
            assert abi(1,w,desc,cls=cls,capacity=32)==(0,plain)
            assert abi(1,w,desc,cls=6 if cls!=6 else 7)[0]==-5
        for kwargs in ({'bag':1},{'bag':2**64-1},{'cls':0},{'cls':13},{'cls':2**64-1},{'sic':1},{'soc':0},{'soc':2},{'nullstore':1}):assert abi(0,plain,desc,**kwargs)[0]==-1
        assert abi(0,plain,desc,capacity=39)[0]==-2
    assert abi(0,plain,nullstore=2)[0]==-6
    assert abi(0,plain,True,shortread=True)[0]==-3
    assert abi(0,plain,True,shortwrite=True)[0]==-3
    checks.append('exact call boundary: opt-in gate, bag/classes/scalars, actualClass, inline/descriptors, short read/write')
    report={'passed':True,'checks':checks,'header_sha256':hashlib.sha256((arm/'SweetKeyStoreWrap.h').read_bytes()).hexdigest(),'call_boundary_sha256':hashlib.sha256(boundary.encode()).hexdigest(),'command':command}
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__': main()
