#!/usr/bin/env python3
"""Fault-inject actual read/pagein/transport functions without a device or image."""
import argparse,json,os,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('xnu',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
def function(text,name):
 at=text.index(name+'(');begin=text.rfind('\n',0,text.rfind('\n',0,at))+1
 start=text.index('{',at);depth=1;end=start+1
 while depth:
  depth+=(text[end]=='{')-(text[end]=='}');end+=1
 return text[begin:end]+'\n'
v=(a.xnu/'bsd/miscfs/apfs/apfs_vnops.c').read_text();f=(a.xnu/'bsd/miscfs/apfs/apfs_vfsops.c').read_text()
head=r'''
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <errno.h>
#include <limits.h>
#define MIN(a,b) ((a)<(b)?(a):(b))
#define MAX(a,b) ((a)>(b)?(a):(b))
#define PAGE_SIZE 16384
#define PAGE_MASK 16383
#define PAGE_MASK_64 16383ULL
#define APFS_FILL_ALIGN 65536
#define APFS_FILL_MAX 1048576
#define UPL_SET_LITE 1
#define VM_KERN_MEMORY_FILE 1
#define KERN_SUCCESS 0
#define UPL_ABORT_FREE_ON_EMPTY 1
#define UPL_ABORT_ERROR 2
#define UPL_COMMIT_FREE_ON_EMPTY 1
#define UPL_COMMIT_INACTIVATE 2
#define UPL_COMMIT_CLEAR_DIRTY 4
#define UPL_COMMIT_WRITTEN_BY_KERNEL 8
#define UPL_NOCOMMIT 16
#define IO_NOCACHE 0x100
#define UBCINFOEXISTS(vp) ((vp)->ubc)
#define os_atomic_load(p,order) (*(p))
#define os_atomic_inc(p,order) (++*(p))
#define os_atomic_inc_orig(p,order) ((*(p))++)
#define os_atomic_dec(p,order) (--*(p))
#define os_atomic_add(p,v,order) (*(p)+=(v))
#define os_atomic_store(p,v,order) (*(p)=(v))
#define round_page_64(x) (((x)+PAGE_MASK)&~(uint64_t)PAGE_MASK)
typedef int kern_return_t;
typedef uintptr_t vm_offset_t;
typedef unsigned upl_size_t,upl_offset_t;
typedef int *upl_t;
typedef int upl_page_info_t;
struct apfs_inode {uint64_t obj_id;};
struct apfs_lock_proc {uint64_t read_calls,read_bytes,read_ticks,pagein_calls,pagein_bytes,pagein_ticks;};
struct apfs_mount {struct {int requests;} am_nx;int am_vol;bool am_ubc_read;uint64_t am_read_calls,am_read_bytes,am_read_ticks,am_read_cached,am_read_filled,am_pagein_calls,am_pagein_ticks,am_pagein_bytes;};
struct apfs_node {struct apfs_mount *am;struct apfs_inode an_ino;uint64_t an_id,an_size,an_read_next;uint32_t an_read_window;int an_cf;};
struct vnode {struct apfs_node node;bool ubc;int kind;};
typedef struct vnode *vnode_t;
#define APFS_VP(vp) (&(vp)->node)
#define APFS_VP_MOUNT(vp) ((vp)->node.am)
struct uio {off_t pos;long resid;};
#define uio_resid(u) ((u)->resid)
#define uio_offset(u) ((u)->pos)
struct vnop_read_args {vnode_t a_vp;struct uio *a_uio;int a_ioflag;};
struct vnop_pagein_args {vnode_t a_vp;upl_t a_pl;upl_offset_t a_pl_offset;off_t a_f_offset;long a_size;int a_flags;};
enum {NONE,CACHE_COPY,CREATE,MAP,FILE_ERROR,FILE_EMPTY,UPL_COPY,NO_PROGRESS,DEV_ALLOC,DEV_STRATEGY,DEV_WAIT,DEV_SHORT,DEV_VNODE};
static int fault,aborts,commits,maps,unmaps,abort_flags,emitted,last_error,last_detail;
static const char *last_stage;
static unsigned char memory[APFS_FILL_MAX];static int pages[64],upl_object;
static unsigned int vm_page_free_count=2100,vm_page_wire_count=18000;
static int apfs_error_trace=1;static uint32_t apfs_error_sequence;
static int trace_printf(const char *fmt,...) {if(strncmp(fmt,"WHYRED APFS ERROR:",18))return 0;va_list ap;va_start(ap,fmt);(void)va_arg(ap,unsigned);last_stage=va_arg(ap,const char *);for(int i=0;i<3;i++)(void)va_arg(ap,unsigned long long);last_error=va_arg(ap,int);last_detail=(int)va_arg(ap,unsigned);va_end(ap);emitted++;return 0;}
#define printf trace_printf
static uint64_t apfs_ticks(void){return 0;}
static struct apfs_lock_proc counters;
static struct apfs_lock_proc *lock_proc(struct apfs_mount *am){(void)am;return &counters;}
static void apfs_lock(struct apfs_mount *am){(void)am;}
static void apfs_unlock(struct apfs_mount *am){(void)am;}
static int apfs_read_file(void *v,struct apfs_inode *i,void *cf,uint64_t at,void *dst,size_t want,size_t *got){(void)v;(void)i;(void)cf;(void)at;*got=0;if(fault==FILE_ERROR)return EIO;if(fault==FILE_EMPTY)return 0;memset(dst,0x5a,want);*got=want;return 0;}
static int cluster_copy_ubc_data(vnode_t vp,struct uio *u,int *resid,int flag){(void)vp;(void)u;(void)resid;(void)flag;return fault==CACHE_COPY?EIO:0;}
static int ubc_create_upl_kernel(vnode_t vp,off_t off,int size,upl_t *upl,upl_page_info_t **pl,int flag,int tag){(void)vp;(void)off;(void)size;(void)flag;(void)tag;if(fault==CREATE)return 3;*upl=&upl_object;*pl=pages;return 0;}
static int ubc_upl_map(upl_t upl,vm_offset_t *address){(void)upl;maps++;if(fault==MAP)return 3;*address=(uintptr_t)memory;return 0;}
static int ubc_upl_unmap(upl_t upl){(void)upl;unmaps++;return 0;}
static int ubc_upl_abort_range(upl_t upl,unsigned off,unsigned len,int flags){(void)upl;(void)off;(void)len;aborts++;abort_flags=flags;return 0;}
static int ubc_upl_commit_range(upl_t upl,unsigned off,unsigned len,int flags){(void)upl;(void)off;(void)len;(void)flags;commits++;return 0;}
static bool upl_valid_page(upl_page_info_t *pl,int i){return pl[i]!=0;}
static int cluster_copy_upl_data(struct uio *u,upl_t upl,int off,int *resid){(void)upl;(void)off;if(fault==UPL_COPY)return EFAULT;if(fault==NO_PROGRESS)return 0;u->pos+=*resid;u->resid-=*resid;*resid=0;return 0;}
static bool vnode_isdir(vnode_t vp){return vp->kind==1;}
static bool vnode_isreg(vnode_t vp){return vp->kind==0;}
static int direct_calls;
static int apfs_read_direct(struct vnop_read_args *ap){(void)ap;direct_calls++;return 731;}
'''
transport=r'''
typedef long daddr64_t;
#define B_READ 1
struct fakebuf {unsigned count,resid;void *ptr;};typedef struct fakebuf *buf_t;
struct apfs_devctx {vnode_t vp;uint64_t size;uint32_t block;};
static struct fakebuf buffer;static int vnode_gets,vnode_puts,frees,strategies,waits;
static int vnode_getwithref(vnode_t vp){(void)vp;if(fault==DEV_VNODE)return ENOENT;vnode_gets++;return 0;}
static void vnode_put(vnode_t vp){(void)vp;vnode_puts++;}
static buf_t buf_alloc(vnode_t vp){(void)vp;return fault==DEV_ALLOC?NULL:&buffer;}
static void buf_reset(buf_t bp,int flags){(void)flags;memset(bp,0,sizeof(*bp));}
static void buf_setblkno(buf_t bp,daddr64_t n){(void)bp;(void)n;}
static void buf_setlblkno(buf_t bp,daddr64_t n){(void)bp;(void)n;}
static void buf_setcount(buf_t bp,uint32_t n){bp->count=n;}
static void buf_setdataptr(buf_t bp,uintptr_t n){bp->ptr=(void*)n;}
static unsigned buf_resid(buf_t bp){return bp->resid;}
static unsigned buf_count(buf_t bp){return bp->count;}
static int VNOP_STRATEGY(buf_t bp){(void)bp;strategies++;return fault==DEV_STRATEGY?EIO:0;}
static int buf_biowait(buf_t bp){waits++;if(fault==DEV_WAIT)return EIO;if(fault==DEV_SHORT)bp->resid=512;return 0;}
static void buf_free(buf_t bp){(void)bp;frees++;}
'''
main=r'''
static void reset(int mode){fault=mode;aborts=commits=maps=unmaps=abort_flags=emitted=last_error=last_detail=0;last_stage="";apfs_error_sequence=0;apfs_error_trace=1;vnode_gets=vnode_puts=frees=strategies=waits=0;memset(memory,0xcc,sizeof(memory));memset(pages,0,sizeof(pages));}
static void stage(const char *s,int error,int detail){assert(emitted==1);assert(!strcmp(last_stage,s));assert(last_error==error);assert(last_detail==detail);}
int main(void){
 struct apfs_mount am={.am_ubc_read=true};struct vnode vnode={.node={.am=&am,.an_ino={.obj_id=17},.an_id=17,.an_size=65536},.ubc=true};struct uio u;uint64_t cached,filled;
 int modes[]={CACHE_COPY,CREATE,MAP,FILE_ERROR,FILE_EMPTY,UPL_COPY,NO_PROGRESS};
 const char *stages[]={"read-cache-copy","read-upl-create","read-upl-map","fill-file","fill-empty","read-upl-copy","read-no-progress"};
 for(unsigned i=0;i<sizeof(modes)/sizeof(*modes);i++){
  reset(modes[i]);u=(struct uio){.pos=0,.resid=512};cached=filled=0;
  int err=apfs_read_cached(&am,&vnode,&u,&vnode.node.an_ino,65536,&cached,&filled);
  assert(err==(modes[i]==UPL_COPY?EFAULT:EIO));assert(emitted==1&&!strcmp(last_stage,stages[i]));assert(u.resid==512);
  if(modes[i]==MAP||modes[i]==FILE_ERROR||modes[i]==FILE_EMPTY)assert(aborts==1&&commits==0);
  assert(unmaps==(modes[i]==FILE_ERROR||modes[i]==FILE_EMPTY||modes[i]==UPL_COPY||modes[i]==NO_PROGRESS));
 }
 reset(NONE);u=(struct uio){.pos=0,.resid=512};cached=filled=0;assert(!apfs_read_cached(&am,&vnode,&u,&vnode.node.an_ino,65536,&cached,&filled));assert(u.resid==0&&filled==65536&&commits==1&&!aborts&&!emitted);
 struct vnop_read_args read={.a_vp=&vnode,.a_uio=&u,.a_ioflag=IO_NOCACHE};reset(NONE);direct_calls=0;assert(apfs_vnop_read(&read)==731&&direct_calls==1);read.a_ioflag=0;u=(struct uio){.pos=0,.resid=512};assert(apfs_vnop_read(&read)==0&&direct_calls==1&&u.resid==0);
 struct vnop_pagein_args in={.a_vp=&vnode,.a_pl=&upl_object,.a_size=32768};
 reset(MAP);assert(apfs_vnop_pagein(&in)==ENOMEM);stage("pagein-upl-map",ENOMEM,3);assert(aborts==1&&abort_flags==(UPL_ABORT_ERROR|UPL_ABORT_FREE_ON_EMPTY)&&!unmaps);
 in.a_flags=UPL_NOCOMMIT;reset(MAP);assert(apfs_vnop_pagein(&in)==ENOMEM&&!aborts&&!commits);in.a_flags=0;
 reset(FILE_ERROR);assert(apfs_vnop_pagein(&in)==EIO);stage("pagein-file",EIO,0);assert(unmaps==1&&aborts==1&&!commits);
 reset(FILE_EMPTY);assert(apfs_vnop_pagein(&in)==EIO);stage("pagein-empty",EIO,0);assert(unmaps==1&&aborts==1&&!commits);
 reset(NONE);vnode.node.an_size=8;assert(!apfs_vnop_pagein(&in));assert(commits==1&&!aborts&&!emitted);for(int i=0;i<8;i++)assert(memory[i]==0x5a);for(int i=8;i<32768;i++)assert(memory[i]==0);
 struct apfs_devctx dc={.vp=&vnode,.size=1048576,.block=512};
 int dm[]={DEV_VNODE,DEV_ALLOC,DEV_STRATEGY,DEV_WAIT,DEV_SHORT};const char *ds[]={"dev-vnode","dev-buf-alloc","dev-strategy","dev-biowait","dev-short"};
 for(unsigned i=0;i<sizeof(dm)/sizeof(*dm);i++){reset(dm[i]);assert(apfs_dev_read(&dc,0,memory,512)!=0);assert(emitted==1&&!strcmp(last_stage,ds[i]));assert(vnode_gets==vnode_puts);assert(frees==(dm[i]>=DEV_STRATEGY&&dm[i]<=DEV_SHORT));}
 reset(NONE);assert(!apfs_dev_read(&dc,0,memory,131072));assert(strategies==2&&waits==2&&frees==2&&vnode_gets==1&&vnode_puts==1&&!emitted);
 reset(NONE);assert(apfs_dev_read(&dc,1048576,memory,512)==EIO&&!strategies);stage("dev-bounds",EIO,512);
 reset(NONE);apfs_error_trace=0;apfs_read_error("off",0,0,0,EIO,3);assert(!emitted);apfs_error_trace=1;apfs_read_error("ok",0,0,0,0,3);assert(!emitted);for(int i=0;i<10000;i++)apfs_read_error("bounded",0,0,0,EIO,3);assert(emitted==32&&apfs_error_sequence==32);
 puts("PASS: actual read/pagein/transport fault paths, cleanup, EOF zeroing, IO_NOCACHE dispatch and 32-record budget");return 0;
}
'''
code=head+function(f,'apfs_read_error')
for name in ['apfs_fill','apfs_read_cached','apfs_vnop_read','apfs_vnop_pagein']:code+=function(v,name)
code+=transport+function(f,'apfs_dev_read')+main
c=a.output/'apfs-errors-host.c';c.write_text(code);exe=a.output/'apfs-errors-host'
# build.sh exports SDKROOT for the kernel; this executable runs on the host.
host_env=os.environ.copy();host_env.pop('SDKROOT',None)
compiler=['clang']
if sys.platform=='darwin':
 sdk=subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],text=True,env=host_env).strip()
 compiler+=['-isysroot',sdk]
subprocess.run(compiler+['-std=c11','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(c),'-o',str(exe)],check=True,env=host_env)
r=subprocess.run([str(exe)],capture_output=True,text=True,env=host_env);(a.output/'result.txt').write_text(r.stdout+r.stderr);print(r.stdout+r.stderr,end='');assert r.returncode==0
(a.output/'report.json').write_text(json.dumps({'passed':True,'actual_kernel_functions_extracted':True,'fault_paths':17,'device_access':False,'limitation':'Mock UPL/transport APIs; does not exercise physical VM pressure or eMMC.'},indent=2)+'\n')
