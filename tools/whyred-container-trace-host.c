#include <stdarg.h>
#include <stddef.h>
#include <stdint.h>
#include <limits.h>
#include <stdbool.h>

/* Match Apple's unsigned UINT16_MAX spelling, including in Windows checks. */
#undef UINT16_MAX
#define UINT16_MAX 0xffffU

static int failure_line;
static void host_assert(bool ok, int line) { if (!ok && !failure_line) failure_line = line; }
#define assert(x) host_assert(!!(x), __LINE__)
#ifdef _WIN32
#define API __declspec(dllexport)
#else
#define API __attribute__((visibility("default")))
#endif
void *memcpy(void *d, const void *s, size_t n) { unsigned char *a=d; const unsigned char *b=s; while(n--) *a++=*b++; return d; }
void *memset(void *d, int v, size_t n) { unsigned char *a=d; while(n--) *a++=(unsigned char)v; return d; }
static size_t strlen(const char *s) { size_t n=0; while(s[n])n++; return n; }
static int memcmp(const void *a,const void *b,size_t n) { const unsigned char *x=a,*y=b; while(n--) { if(*x!=*y)return (int)*x-(int)*y; x++; y++; } return 0; }
static int strcmp(const char *a,const char *b) { while(*a && *a==*b){a++;b++;}return (unsigned char)*a-(unsigned char)*b; }
static char *strcpy(char *d,const char *s) { char *r=d; do {*d++=*s;} while(*s++); return r; }
static char *strstr(const char *a,const char *b) { size_t n=strlen(b); for(;*a;a++) if(strlen(a)>=n && !memcmp(a,b,n)) return (char *)a; return NULL; }

/* Darwin errors needed by the actual helper; not the host's errno values. */
#define ENOENT 2
#define EINTR 4
#define EIO 5
#define EBADF 9
#define EEXIST 17
#define EINVAL 22
#define ENOSPC 28
#define EAGAIN 35
#define ENAMETOOLONG 63
#define ENOATTR 93
#define bzero(p, n) memset(p, 0, n)
#include "syscall-defines.h"
typedef uint64_t user_addr_t;
struct proc { char p_name[33], p_comm[17]; int pid; };
struct uthread { uint64_t uu_arg[8]; int32_t uu_rval[2]; };
struct arm_saved_state { int is64; uint64_t pc; };
struct { unsigned int sy_narg; } sysent[1024];
struct fileproc { int value; };
struct vnode { int value; };
typedef struct vnode *vnode_t;
#define NULLVP ((vnode_t)0)
static unsigned int tests, parse_calls, copy_calls, fd_gets, fd_drops, vnode_gets, vnode_puts;
static int option, copy_failure, fd_failure, vnode_failure, path_failure;
static user_addr_t attr_address;
static unsigned int attr_copy_calls;
static int attr_copy_failure;
static char output[300000];
static size_t used;
static struct vnode node;
static struct fileproc file;
#define CHECK(x) do { tests++; assert(x); } while (0)
static void emit(char c) { assert(used+1 < sizeof(output)); if(used+1 < sizeof(output)){output[used++]=c;output[used]=0;} }
static void emit_string(const char *s) { while(*s) emit(*s++); }
static void emit_number(uint64_t v, unsigned int base) { char s[24]; size_t n=0;do{s[n++]="0123456789abcdef"[v%base];v/=base;}while(v);while(n)emit(s[--n]); }
static int mock_printf(const char *fmt, ...) {
    va_list args;
    va_start(args, fmt);
    size_t before=used;
    while(*fmt) {
        if(*fmt!='%'){emit(*fmt++);continue;}
        fmt++;
        bool wide=false;
        if(fmt[0]=='l' && fmt[1]=='l'){wide=true;fmt+=2;}
        char conversion=*fmt++;
        if(conversion=='s') emit_string(va_arg(args,const char *));
        else if(conversion=='d'){int v=va_arg(args,int);if(v<0){emit('-');emit_number((uint64_t)(-(int64_t)v),10);}else emit_number((uint64_t)v,10);}
        else if(conversion=='u' || conversion=='x'){uint64_t v=wide?va_arg(args,uint64_t):va_arg(args,unsigned int);emit_number(v,conversion=='x'?16:10);}
        else assert(false);
    }
    va_end(args);
    return (int)(used-before);
}
static int PE_parse_boot_argn(const char *name, void *out, size_t size) {
    assert(strcmp(name, "whyred-container-trace") == 0 && size == sizeof(int));
    parse_calls++;
    *(int *)out = option;
    return option != 0;
}
static int is_saved_state64(struct arm_saved_state *s) { return s->is64; }
static uint64_t get_saved_state_pc(struct arm_saved_state *s) { return s->pc; }
static int proc_pid(struct proc *p) { return p->pid; }
static int copyinstr(user_addr_t addr, char *out, size_t cap, size_t *done) {
    copy_calls++;
    if (copy_failure || addr == 0) { memset(out, 'X', cap); return 14; }
    const char *src = (const char *)(uintptr_t)addr;
    size_t len = strlen(src);
    if (len >= cap) { memcpy(out, src, cap); *done = cap; return ENAMETOOLONG; }
    memcpy(out, src, len + 1); *done = len + 1; return 0;
}
static int copyin(user_addr_t addr, void *out, size_t size) {
    attr_copy_calls++;assert(size==24);
    if(attr_copy_failure || !addr || addr!=attr_address){memset(out,0xab,size);return 14;}
    memcpy(out,(const void *)(uintptr_t)addr,size);return 0;
}
static int fp_getfvp(struct proc *p, int fd, struct fileproc **fp, vnode_t *vp) {
    (void)p; fd_gets++;
    if (fd_failure || fd != 7) return EBADF;
    *fp = &file; *vp = &node; return 0;
}
static int fp_drop(struct proc *p, int fd, struct fileproc *fp, int locked) {
    (void)p; assert(fd == 7 && fp == &file && !locked); fd_drops++; return 0;
}
static int vnode_getwithref(vnode_t vp) {
    assert(vp == &node); vnode_gets++; return vnode_failure ? EIO : 0;
}
static int vn_getpath(vnode_t vp, char *path, int *size) {
    assert(vp == &node && *size >= 30);
    if (path_failure) { memset(path, 'Y', (size_t)*size); return EIO; }
    strcpy(path, "/private/var/test.metadata"); return 0;
}
static void vnode_put(vnode_t vp) { assert(vp == &node); vnode_puts++; }
#define printf mock_printf
#include "whyred_container_trace.h"
#undef printf

static void reset(void) {
    memset(&whyred_ct_budget, 0, sizeof(whyred_ct_budget)); whyred_ct_enabled = 0;
    option = 1; used = 0; output[0] = 0;
    parse_calls = copy_calls = fd_gets = fd_drops = vnode_gets = vnode_puts = 0;
    copy_failure = fd_failure = vnode_failure = path_failure = 0;
    attr_address=0;attr_copy_calls=0;attr_copy_failure=0;
}
static void call(struct proc *p, unsigned short code, int error, struct uthread *u) {
    struct uthread before = *u;
    struct arm_saved_state s = { 1, 0x18001234 };
    whyred_container_trace_error(p, u, &s, code, error);
    CHECK(memcmp(&before, u, sizeof(before)) == 0);
    CHECK(s.pc == 0x18001234 && s.is64 == 1);
}
API int whyred_container_host_checks(void) {
#include "syscall-init.h"
    struct proc manager = { "containermanagerd", "containermanager", 67 };
    struct proc pkd = { "pkd", "pkd", 264 };
    struct proc unrelated = { "SpringBoard", "SpringBoard", 45 };
    struct uthread u = { { (uint64_t)(uintptr_t)"/private/var/metadata", 0x1234, 3, 4, 5, 6, 7, 8 }, { 0, 0 } };
    reset(); option = 0; call(&manager, SYS_open, EIO, &u);
    CHECK(used == 0 && copy_calls == 0 && fd_gets == 0 && parse_calls == 1);
    call(&manager, SYS_open, EIO, &u); CHECK(parse_calls == 1 && used == 0);
    reset(); call(&unrelated, SYS_open, EIO, &u); CHECK(used == 0 && copy_calls == 0);
    reset(); call(&manager, SYS_open, 0, &u); call(&manager, SYS_open, -1, &u);
    CHECK(used == 0 && parse_calls == 0);
    reset(); struct arm_saved_state s32 = { 0, 42 };
    whyred_container_trace_error(&manager, &u, &s32, SYS_open, EIO);
    CHECK(used == 0 && parse_calls == 0);
    reset(); call(&manager, 999, EIO, &u); CHECK(used == 0);
    reset(); call(&manager, SYS_open_dprotected_np, EINVAL, &u);
    CHECK(strstr(output, "proc=containermanagerd") != NULL);
    CHECK(strstr(output, "op=open_dprotected_np") != NULL);
    CHECK(strstr(output, "errno=22") != NULL && strstr(output, "pc=0x18001234") != NULL);
    CHECK(strstr(output, "path1=/private/var/metadata copy_errno=0") != NULL);
    CHECK(strstr(output, "args=") != NULL);
    uint32_t masks[6]={5,0x1234,0x80000000,1,2,4};
    for(unsigned i=0;i<4;i++) {
        reset();attr_address=(user_addr_t)(uintptr_t)masks;
        unsigned code=i==0?SYS_getattrlist:i==1?SYS_fgetattrlist:i==2?SYS_getattrlistat:SYS_getattrlistbulk;
        struct uthread attr={{0}, {0,0}};
        unsigned slot=i==2?2:1;
        attr.uu_arg[0]=(i==1||i==3)?7:(uint64_t)(uintptr_t)"/dev";
        if(i==2)attr.uu_arg[1]=(uint64_t)(uintptr_t)"/dev";
        attr.uu_arg[slot]=attr_address;attr.uu_arg[slot+1]=0x99;attr.uu_arg[slot+2]=64;attr.uu_arg[slot+3]=8;
        call(&manager,(unsigned short)code,EINVAL,&attr);
        CHECK(attr_copy_calls==1&&strstr(output,"count=5 reserved=0 common=0x1234 volume=0x80000000")!=NULL);
        CHECK(strstr(output,"directory=0x1 file=0x2 fork=0x4 bufsize=64 options=0x8")!=NULL);
        reset();attr_address=(user_addr_t)(uintptr_t)masks;attr_copy_failure=1;
        call(&manager,(unsigned short)code,EINVAL,&attr);
        CHECK(attr_copy_calls==1&&strstr(output,"attrlist_copy_errno=14 count=0 reserved=0 common=0x0")!=NULL);
        reset();attr_address=(user_addr_t)(uintptr_t)masks;
        call(&manager,(unsigned short)code,EIO,&attr);CHECK(attr_copy_calls==0);
    }
    reset(); call(&pkd, SYS_open, ENOENT, &u);
    CHECK(strstr(output, ",1234,3,0,0,0,0") != NULL); /* no stale words beyond sy_narg */
    reset(); u.uu_arg[0] = 7; call(&manager, SYS_fcntl, EINVAL, &u);
    CHECK(strstr(output, "fd=7 fdpath=/private/var/test.metadata path_errno=0") != NULL);
    CHECK(fd_gets == 1 && fd_drops == 1 && vnode_gets == 1 && vnode_puts == 1);
    reset(); vnode_failure = 1; call(&manager, SYS_fsync, EIO, &u);
    CHECK(fd_drops == 1 && vnode_puts == 0 && strstr(output, "fdpath= path_errno=5") != NULL);
    reset(); path_failure = 1; call(&manager, SYS_fsync, EIO, &u);
    CHECK(fd_drops == 1 && vnode_puts == 1 && strstr(output, "fdpath= path_errno=5") != NULL);
    reset(); fd_failure = 1; call(&manager, SYS_fsync, EIO, &u);
    CHECK(fd_drops == 0 && vnode_gets == 0 && strstr(output, "path_errno=9") != NULL);
    reset(); copy_failure = 1; call(&pkd, SYS_open, EIO, &u);
    CHECK(strstr(output, "path1= copy_errno=14") != NULL);
    reset(); char longpath[500]; memset(longpath, 'a', sizeof(longpath)); longpath[499] = 0;
    u.uu_arg[0] = (uint64_t)(uintptr_t)longpath; call(&pkd, SYS_open, EIO, &u);
    CHECK(strstr(output, "copy_errno=63") != NULL);
    CHECK(strlen(strstr(output, "path1=")) < 240);
    reset(); u.uu_arg[0] = (uint64_t)(uintptr_t)"/var/a\n\033bad";
    call(&pkd, SYS_open, EIO, &u); CHECK(strstr(output, "/var/a??bad") != NULL);
    reset(); u.uu_arg[0] = (uint64_t)(uintptr_t)"/var/from";
    u.uu_arg[1] = (uint64_t)(uintptr_t)"/var/to"; call(&manager, SYS_rename, EIO, &u);
    CHECK(strstr(output, "path1=/var/from") != NULL && strstr(output, "path2=/var/to") != NULL);
    reset(); u.uu_arg[0] = 7; u.uu_arg[1] = (uint64_t)(uintptr_t)"relative/from";
    u.uu_arg[2] = 8; u.uu_arg[3] = (uint64_t)(uintptr_t)"relative/to";
    call(&manager, SYS_renameatx_np, EIO, &u);
    CHECK(strstr(output, "path1=relative/from") != NULL && strstr(output, "path2=relative/to") != NULL);
    reset(); for (unsigned int i = 1; i <= 16; i++) {
        unsigned int r = whyred_ct_reserve(1, SYS_open, EIO);
        CHECK((r != 0) == (i <= 4 || i == 8 || i == 16));
    }
    reset(); whyred_ct_budget.lock = 1;
    CHECK(whyred_ct_reserve(1, SYS_open, EIO) == 0 && whyred_ct_budget.lock == 1);
    reset(); whyred_ct_enabled = 1; call(&manager, SYS_open, EIO, &u); CHECK(used == 0);
    reset(); u.uu_arg[0] = 7; u.uu_arg[2] = 10; u.uu_rval[0] = 4;
    call(&pkd, SYS_write, 0, &u);
    CHECK(strstr(output, "errno=0") != NULL && strstr(output, "reason=short-write requested=10 returned=4") != NULL);
    CHECK(fd_drops == 1 && vnode_puts == 1);
    reset(); u.uu_rval[0] = 10; call(&pkd, SYS_write_nocancel, 0, &u); CHECK(used == 0);
    reset(); u.uu_arg[2] = 0; u.uu_rval[0] = 0; call(&pkd, SYS_pwrite, 0, &u); CHECK(used == 0);
    reset(); u.uu_arg[2] = 10; u.uu_rval[0] = 0; call(&pkd, SYS_read, 0, &u); CHECK(used == 0);
    reset(); u.uu_arg[2] = UINT64_C(0x100000006); u.uu_rval[0] = 4; u.uu_rval[1] = 1;
    call(&pkd, SYS_pwrite_nocancel, 0, &u);
    CHECK(strstr(output, "requested=4294967302 returned=4294967300") != NULL);
    reset(); u.uu_arg[2] = 10; u.uu_rval[0] = 4; u.uu_rval[1] = 0; option = 0;
    call(&manager, SYS_write, 0, &u); CHECK(used == 0 && fd_gets == 0);
    reset(); for (unsigned int i = 0; i < 128; i++) {
        (void)whyred_ct_reserve(1, (unsigned short)i, ENOENT);
    }
    CHECK(whyred_ct_budget.common == WHYRED_CT_COMMON_LIMIT);
    CHECK(whyred_ct_reserve(1, 0, EIO) != 0); /* common misses cannot fill severe-error slots */
    reset(); whyred_ct_budget.common = WHYRED_CT_COMMON_LIMIT;
    CHECK(whyred_ct_reserve(1, SYS_open, EIO) != 0 && whyred_ct_budget.other == 1);
    for (unsigned int code = 0; code < 64; code++) for (unsigned int e = 20; e < 22; e++) {
        for (unsigned int i = 0; i < 8; i++) (void)whyred_ct_reserve(1, (unsigned short)code, e);
    }
    CHECK(whyred_ct_budget.other == WHYRED_CT_OTHER_LIMIT);
    CHECK(whyred_ct_budget.common + whyred_ct_budget.other == 256);
    reset(); whyred_ct_budget.keys[WHYRED_CT_KEYS / 2] = (struct whyred_ct_key){ SYS_open, EIO, 1, UINT_MAX };
    CHECK(whyred_ct_reserve(1, SYS_open, EIO) == 0 && whyred_ct_budget.keys[WHYRED_CT_KEYS / 2].count == UINT_MAX);
    CHECK(whyred_ct_target("containermanager") == 0 && whyred_ct_target("pkd-other") == 0);
    CHECK(whyred_ct_target("calaccessd") == 3);
    return failure_line;
}
API unsigned int whyred_container_check_count(void) { return tests; }
