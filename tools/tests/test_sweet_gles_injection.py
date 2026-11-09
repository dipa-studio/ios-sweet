"""Exercise the actual opt-in exec helper and AMFI90 copy ABI with host mocks."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / 'xnu/patches/0205-sweet-gles-exec-dyld-policy.patch'


def added_function(name):
    source = '\n'.join(line[1:] for line in PATCH.read_text().splitlines()
                       if line.startswith('+') and not line.startswith('+++'))
    start = source.index('static int\n' + name + '(')
    return source[start:source.index('\n}', start) + 2]


@unittest.skipUnless(shutil.which('cc'), 'needs a host C compiler')
class GLESInjectionTests(unittest.TestCase):
    def compile_run(self, source):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test.c'
            path.write_text(source)
            binary = path.with_suffix('')
            compiled = subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=address,undefined', str(path), '-o', str(binary)],
                           capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            subprocess.run([str(binary)], check=True, capture_output=True)

    def test_exec_gate_duplicate_conflict_and_space_accounting(self):
        self.compile_run(r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#define printf(...) ((void)0)
#undef CAST_USER_ADDR_T
#define CAST_USER_ADDR_T(x) ((uintptr_t)(x))
#define UIO_SYSSPACE 1
#define TRUE 1
struct nameidata { struct { size_t cn_namelen; const char *cn_nameptr; } ni_cnd; };
struct image_params {
    char *ip_endargv, *ip_strendp; int ip_argspace, ip_strspace;
    int ip_envc; struct nameidata *ip_ndp;
};
static uint32_t sweet_gles_exec_enabled;
static int injected_error, added;
static int exec_add_user_string(struct image_params *p, uintptr_t a, int space, int count) {
    assert(space==UIO_SYSSPACE && count==TRUE);added++;
    if(injected_error)return injected_error;
    size_t n=strlen((char*)a)+1;
    if(p->ip_argspace<(int)n || p->ip_strspace<(int)n)return E2BIG;
    memcpy(p->ip_strendp,(void*)a,n);p->ip_strendp+=n;
    p->ip_argspace-=n;p->ip_strspace-=n;return 0;
}
''' + added_function('sweet_gles_exec_env') + r'''
int main(void) {
    char buf[512]="A=B";
    struct nameidata nd={ {10,"backboardd"} };
    struct image_params p={buf,buf+4,400,500,1,&nd};
    assert(!sweet_gles_exec_env(&p,8) && added==0);
    sweet_gles_exec_enabled=2;assert(!sweet_gles_exec_env(&p,8) && added==0);
    sweet_gles_exec_enabled=1;assert(!sweet_gles_exec_env(&p,4) && added==0);
    p.ip_ndp=0;assert(!sweet_gles_exec_env(&p,8) && added==0);p.ip_ndp=&nd;
    nd.ni_cnd.cn_nameptr="SpringBoard";nd.ni_cnd.cn_namelen=11;
    assert(!sweet_gles_exec_env(&p,8) && added==0);
    nd.ni_cnd.cn_nameptr="backboardX";nd.ni_cnd.cn_namelen=10;
    assert(!sweet_gles_exec_env(&p,8) && added==0);
    nd.ni_cnd.cn_nameptr="backboardd";
    assert(!sweet_gles_exec_env(&p,8) && added==1 && p.ip_envc==2);
    const char *want="DYLD_INSERT_LIBRARIES=/usr/local/sweet/lib/libsweet-gles-loader.dylib";
    assert(!strcmp(buf+4,want));size_t n=strlen(want)+1;
    assert(p.ip_argspace==400-(int)n-8 && p.ip_strspace==500-(int)n);
    assert(p.ip_strendp==buf+4+n && !memcmp(buf,"A=B",4));
    assert(!sweet_gles_exec_env(&p,8) && added==1 && p.ip_envc==2);
    strcpy(buf+4,"DYLD_INSERT_LIBRARIES=/other");
    assert(sweet_gles_exec_env(&p,8)==EINVAL && added==1);
    p.ip_envc=1;p.ip_strendp=buf+4;p.ip_argspace=7;
    assert(sweet_gles_exec_env(&p,8)==E2BIG && added==1);
    p.ip_argspace=400;injected_error=EFAULT;
    assert(sweet_gles_exec_env(&p,8)==EFAULT && p.ip_envc==1);
    injected_error=0;p.ip_argspace=n+7;
    assert(sweet_gles_exec_env(&p,8)==E2BIG && p.ip_envc==1);
}
''')

    def test_amfi_90_uses_output_pointer_and_propagates_errors(self):
        self.compile_run(r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#define printf(...) ((void)0)
#ifndef ENOPOLICY
#define ENOPOLICY 103
#endif
struct proc { const char *name;int is64; };
typedef struct proc *proc_t;
#define user_addr_t uintptr_t
static proc_t current;
static uint32_t sweet_gles_dyld_enabled;
static int reads,writes,in_error,out_error;
static int proc_is64bit_data(proc_t p){return p->is64;}
static int proc_pid(proc_t p){assert(p==current);return 56;}
static void proc_name(int pid,char *out,int size){assert(pid==56 && size==32);strcpy(out,current->name);}
static int copyin(user_addr_t addr,void*out,size_t size){
    reads++;assert(size==16);if(in_error)return in_error;
    memcpy(out,(void*)addr,size);return 0;
}
static int copyout(const void *src,user_addr_t addr,size_t size){
    writes++;assert(size==8);if(out_error)return out_error;
    memcpy((void*)addr,src,size);return 0;
}
''' + added_function('sweet_amfi_policy_syscall') + r'''
int main(void) {
    struct proc p={"backboardd",1};current=&p;
    uint64_t output=0x12345678;
    struct {uint64_t in;user_addr_t out;} args={6,(uintptr_t)&output};
    assert(sweet_amfi_policy_syscall(&p,90,(uintptr_t)&args)==ENOPOLICY && reads==0);
    sweet_gles_dyld_enabled=1;
    assert(sweet_amfi_policy_syscall(&p,96,(uintptr_t)&args)==ENOPOLICY && reads==0);
    p.is64=0;assert(sweet_amfi_policy_syscall(&p,90,0)==ENOPOLICY && reads==0);
    p.is64=1;p.name="SpringBoard";
    assert(sweet_amfi_policy_syscall(&p,90,0)==ENOPOLICY && reads==0);
    p.name="backboardd";
    assert(!sweet_amfi_policy_syscall(&p,90,(uintptr_t)&args));
    assert(output==0x12 && args.in==6 && reads==1 && writes==1);
    output=7;in_error=EFAULT;
    assert(sweet_amfi_policy_syscall(&p,90,0)==EFAULT && output==7 && writes==1);
    in_error=0;out_error=EFAULT;
    assert(sweet_amfi_policy_syscall(&p,90,(uintptr_t)&args)==EFAULT && output==7);
}
''')


if __name__ == '__main__':
    unittest.main()
