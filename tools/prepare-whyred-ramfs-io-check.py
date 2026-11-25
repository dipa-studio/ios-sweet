#!/usr/bin/env python3
"""Extract actual RAMFS namespace/readdir/sync functions into a host harness.

Kernel allocators, mutexes, uio and vnode identity are adapted. This tests
operation results and ABI records, not kernel scheduling, UBC or hardware.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


def function(text, name):
    match = re.search(r'^' + name + r'\(', text, re.M)
    start = text.rfind('\nstatic ', 0, match.start()) + 1
    begin = text.index('{', match.start())
    depth, end = 1, begin + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


ADAPTERS = r'''
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#ifndef __unused
#define __unused
#endif
#define PAGE_SIZE 16384
#define MAX(a,b) ((a)>(b)?(a):(b))
#define MIN(a,b) ((a)<(b)?(a):(b))
#define WHYRED_RAMFS_MAX_NODES 32768
#define RAMFS_MAX_NAME 255
#define Z_WAITOK 0
#define Z_ZERO 0
#define Z_NOFAIL 0
#define kalloc_type(t,f) ((t *)calloc(1,sizeof(t)))
#define kalloc_data(n,f) calloc(1,n)
#define kfree_type(t,p) free(p)
#define kfree_data(p,n) free(p)
#ifndef bzero
#define bzero(p,n) memset(p,0,n)
#endif
#ifndef ENOTSUP
#define ENOTSUP 45
#endif
#define TAILQ_HEAD(n,t) struct n {struct t *tqh_first; struct t **tqh_last;}
#define TAILQ_ENTRY(t) struct {struct t *tqe_next;struct t **tqe_prev;}
#define TAILQ_INIT(h) do{(h)->tqh_first=NULL;(h)->tqh_last=&(h)->tqh_first;}while(0)
#define TAILQ_FIRST(h) ((h)->tqh_first)
#define TAILQ_NEXT(e,f) ((e)->f.tqe_next)
#define TAILQ_FOREACH(e,h,f) for((e)=TAILQ_FIRST(h);(e);(e)=TAILQ_NEXT(e,f))
#define TAILQ_INSERT_TAIL(h,e,f) do{(e)->f.tqe_next=NULL;(e)->f.tqe_prev=(h)->tqh_last;*(h)->tqh_last=(e);(h)->tqh_last=&(e)->f.tqe_next;}while(0)
#define TAILQ_REMOVE(h,e,f) do{if((e)->f.tqe_next)(e)->f.tqe_next->f.tqe_prev=(e)->f.tqe_prev;else(h)->tqh_last=(e)->f.tqe_prev;*(e)->f.tqe_prev=(e)->f.tqe_next;}while(0)
enum vtype {VREG=1,VDIR=2,VLNK=5};
#define off_t host_off_t
#define ino_t host_ino_t
typedef int64_t off_t;
typedef uint32_t ino_t;
typedef int64_t user_ssize_t;
typedef unsigned int vfs_rename_flags_t;
#define VFS_RENAME_SECLUDE 1
#define VFS_RENAME_SWAP 2
#define VFS_RENAME_EXCL 4
#define VNODE_UPDATE_PARENT 1
#define VNODE_UPDATE_NAME 2
#define VNODE_UPDATE_CACHE 4
#define VNODE_READDIR_EXTENDED 1
#define VNODE_READDIR_REQSEEKOFF 2
#define DT_DIR 4
#define VTTOIF(t) ((t)==VDIR ? 0040000 : ((t)==VLNK ? 0120000 : 0100000))
#define IFTODT(t) (((t)&0170000)>>12)
#define F_FULLFSYNC 51
#define F_BARRIERFSYNC 85
#define UBC_PUSHDIRTY 1
#define UBC_SYNC 8
struct ramfs_node;
struct ramfs_dirent {TAILQ_ENTRY(ramfs_dirent) rd_link;struct ramfs_node *rd_node;char *rd_name;uint32_t rd_namelen;};
struct ramfs_mount {int rm_lock;struct ramfs_node *rm_root;uint64_t rm_logd_file_limit;};
struct ramfs_node {struct ramfs_mount *rn_mount;uint64_t rn_ino;enum vtype rn_type;uint32_t rn_nlink;
    struct ramfs_node *rn_parent;TAILQ_HEAD(,ramfs_dirent) rn_entries;uint32_t rn_nentries;
    bool rn_mapped_write,rn_logd_dsc;uint8_t rn_logd_role;off_t host_size;struct ramfs_node *host_parent;char host_name[256];unsigned host_identity_updates;};
typedef struct ramfs_node *vnode_t;
#define RAMFS_NODE(vp) (vp)
struct componentname {const char *cn_nameptr;int cn_namelen;uint32_t cn_hash;};
struct vnop_rename_args {vnode_t a_fdvp,a_fvp;struct componentname *a_fcnp;vnode_t a_tdvp,a_tvp;struct componentname *a_tcnp;};
struct vnop_renamex_args {vnode_t a_fdvp,a_fvp;struct componentname *a_fcnp;vnode_t a_tdvp,a_tvp;struct componentname *a_tcnp;vfs_rename_flags_t a_flags;};
struct uio {off_t offset;user_ssize_t resid;char *buf;size_t used;};
struct vnop_readdir_args {vnode_t a_vp;struct uio *a_uio;int a_flags;int *a_eofflag,*a_numdirent;};
struct vnop_fsync_args {vnode_t a_vp;};
struct vnop_ioctl_args {vnode_t a_vp;unsigned long a_command;};
#pragma pack(push,4)
struct dirent {uint32_t d_fileno;uint16_t d_reclen;uint8_t d_type,d_namlen;char d_name[256];};
#pragma pack(pop)
struct direntry {uint64_t d_fileno,d_seekoff;uint16_t d_reclen,d_namlen;uint8_t d_type;char d_name[1024];};
static unsigned held;
static void lck_mtx_lock(int *p){(void)p;if(held++)abort();}
static void lck_mtx_unlock(int *p){(void)p;if(!held--)abort();}
static void ramfs_touch(struct ramfs_node *n,bool m){(void)n;(void)m;}
static void vnode_update_identity(vnode_t n,vnode_t parent,const char *name,int len,uint32_t hash,int flags){
    (void)hash;(void)flags;if(held)abort();n->host_identity_updates++;n->host_parent=parent;memcpy(n->host_name,name,len);n->host_name[len]=0;}
static off_t uio_offset(struct uio *u){return u->offset;}
static user_ssize_t uio_resid(struct uio *u){return u->resid;}
static void uio_setoffset(struct uio *u,off_t o){u->offset=o;}
static int uiomove(const void *buf,int n,struct uio *u){if(held || n>u->resid)abort();memcpy(u->buf+u->used,buf,n);u->used+=n;u->resid-=n;u->offset+=n;return 0;}
static unsigned sync_calls;static int sync_error;static off_t sync_length;static int sync_flags;
static off_t ubc_getsize(vnode_t v){return v->host_size;}
static int ubc_msync(vnode_t v,off_t a,off_t b,off_t *r,int f){(void)v;(void)r;if(held || a)abort();sync_calls++;sync_length=b;sync_flags=f;return sync_error;}
'''

CHECKS = r'''
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"check %u failed: %s (line %d)\n",checks,#x,__LINE__);exit(1);}}while(0)
static void init(struct ramfs_node *n,struct ramfs_mount *m,enum vtype t,uint64_t ino){
    memset(n,0,sizeof(*n));n->rn_mount=m;n->rn_type=t;n->rn_ino=ino;n->rn_nlink=t==VDIR?2:1;TAILQ_INIT(&n->rn_entries);}
static void add(struct ramfs_node *d,const char *name,struct ramfs_node *n){ramfs_dir_add(d,ramfs_dirent_alloc(name,strlen(name)),n);if(n->rn_type==VDIR){n->rn_parent=d;d->rn_nlink++;}}
static struct ramfs_node *find(struct ramfs_node *d,const char *name){struct ramfs_dirent *de=ramfs_dir_find(d,name,strlen(name));return de?de->rd_node:NULL;}
static int ren(struct ramfs_node *d,const char *from,struct ramfs_node *t,const char *to,unsigned flags){
    struct componentname f={from,(int)strlen(from),0},c={to,(int)strlen(to),0};
    struct vnop_renamex_args a={d,find(d,from),&f,t,find(t,to),&c,flags};
    return ramfs_renamex(&a);}
static int read_dir(struct ramfs_node *d,off_t start,size_t size,int flags,char *buf,struct uio *u,int *eof,int *count){
    *u=(struct uio){start,(user_ssize_t)size,buf,0};struct vnop_readdir_args a={d,u,flags,eof,count};return ramfs_readdir(&a);}
int main(void){
    struct ramfs_mount m={0},other={0};struct ramfs_node root,a,b,left,right,sub,deep,empty,full,wide;
    init(&root,&m,VDIR,2);m.rm_root=&root;root.rn_parent=&root;
    init(&a,&m,VREG,3);init(&b,&m,VREG,4);add(&root,"state",&a);add(&root,"temporary",&b);
    a.host_size=7;b.host_size=99;
    CHECK(ren(&root,"state",&root,"temporary",VFS_RENAME_SWAP)==0);
    CHECK(find(&root,"state")==&b && find(&root,"temporary")==&a);
    CHECK(a.host_size==7 && b.host_size==99 && a.rn_nlink==1 && b.rn_nlink==1);
    CHECK(!strcmp(a.host_name,"temporary") && !strcmp(b.host_name,"state"));
    CHECK(a.host_identity_updates==1 && b.host_identity_updates==1 && root.rn_nentries==2);
    CHECK(ren(&root,"temporary",&root,"state",VFS_RENAME_EXCL)==EEXIST);
    CHECK(find(&root,"state")==&b && find(&root,"temporary")==&a);
    CHECK(ren(&root,"temporary",&root,"absent",VFS_RENAME_SWAP)==ENOENT);
    CHECK(ren(&root,"temporary",&root,"state",VFS_RENAME_SWAP|VFS_RENAME_EXCL)==EINVAL);
    CHECK(ren(&root,"temporary",&root,"state",VFS_RENAME_SECLUDE)==ENOTSUP);
    CHECK(ren(&root,"temporary",&root,"new",VFS_RENAME_EXCL)==0);
    CHECK(!find(&root,"temporary") && find(&root,"new")==&a && root.rn_nentries==2);
    add(&root,"alias",&a);a.rn_nlink++;
    unsigned id=a.host_identity_updates;
    CHECK(ren(&root,"new",&root,"alias",0)==0);
    CHECK(a.rn_nlink==2 && a.host_identity_updates==id && find(&root,"new")==&a);
    CHECK(ren(&root,"new",&root,"alias",VFS_RENAME_SWAP)==0);
    CHECK(a.rn_nlink==2 && a.host_identity_updates==id);
    struct componentname fc={"new",3,0},tc={"state",5,0};
    CHECK(ramfs_rename_common(&root,&a,&fc,&root,NULL,&tc,0)==ENOENT);
    CHECK(find(&root,"state")==&b);
    init(&left,&m,VDIR,5);init(&right,&m,VDIR,6);add(&root,"left",&left);add(&root,"right",&right);
    CHECK(ren(&root,"new",&left,"moved",0)==0);
    CHECK(find(&left,"moved")==&a && !find(&root,"new") && a.rn_nlink==2);
    CHECK(ren(&left,"moved",&root,"state",VFS_RENAME_SWAP)==0);
    CHECK(find(&left,"moved")==&b && find(&root,"state")==&a && b.host_parent==&left);
    CHECK(ren(&left,"moved",&root,"state",0)==0);
    CHECK(find(&root,"state")==&b && a.rn_nlink==1 && !find(&left,"moved"));
    init(&sub,&m,VDIR,7);init(&deep,&m,VDIR,8);add(&left,"sub",&sub);add(&sub,"deep",&deep);
    CHECK(ren(&left,"sub",&deep,"bad",0)==EINVAL);
    CHECK(find(&left,"sub")==&sub && sub.rn_parent==&left);
    add(&deep,"file",&a);a.rn_nlink++;
    CHECK(ren(&left,"sub",&deep,"file",VFS_RENAME_SWAP)==EINVAL);
    unsigned ll=left.rn_nlink,rl=right.rn_nlink;
    CHECK(ren(&left,"sub",&right,"sub",0)==0);
    CHECK(sub.rn_parent==&right && left.rn_nlink==ll-1 && right.rn_nlink==rl+1);
    add(&left,"file",&b);b.rn_nlink++;
    ll=left.rn_nlink;rl=right.rn_nlink;
    CHECK(ren(&left,"file",&right,"sub",VFS_RENAME_SWAP)==0);
    CHECK(find(&left,"file")==&sub && sub.rn_parent==&left && left.rn_nlink==ll+1 && right.rn_nlink==rl-1);
    init(&empty,&m,VDIR,9);add(&right,"empty",&empty);
    CHECK(ren(&left,"file",&right,"empty",0)==0);
    CHECK(empty.rn_nlink==0 && !empty.rn_parent && sub.rn_parent==&right);
    init(&full,&m,VDIR,10);add(&left,"full",&full);add(&full,"entry",&a);a.rn_nlink++;
    CHECK(ren(&right,"empty",&left,"full",0)==ENOTEMPTY);
    CHECK(find(&right,"empty")==&sub && find(&left,"full")==&full);
    CHECK(ren(&root,"state",&left,"full",0)==EISDIR);
    CHECK(ren(&left,"full",&root,"state",0)==ENOTDIR);
    struct ramfs_node foreign;init(&foreign,&other,VDIR,11);
    struct componentname missing={"missing",7,0};
    CHECK(ramfs_rename_common(&root,&b,&tc,&foreign,NULL,&missing,0)==EXDEV);
    struct vnop_rename_args ordinary={&root,&b,&tc,&right,NULL,&missing};
    CHECK(ramfs_rename(&ordinary)==0 && find(&right,"missing")==&b);
#ifdef RAMFS_LOGD_DSC
    /* Actual rename/rename-swap must retain root-created DSC classification. */
    struct ramfs_mount cache={.rm_logd_file_limit=8388608};
    struct ramfs_node cr,db,uuid,dsc,stage,source,target;
    init(&cr,&cache,VDIR,100);cache.rm_root=&cr;cr.rn_parent=&cr;
    init(&db,&cache,VDIR,101);init(&uuid,&cache,VDIR,102);init(&dsc,&cache,VDIR,103);
    init(&stage,&cache,VDIR,104);init(&source,&cache,VREG,105);init(&target,&cache,VREG,106);
    add(&cr,"db",&db);add(&db,"uuidtext",&uuid);add(&uuid,"dsc",&dsc);add(&cr,"stage",&stage);
    add(&stage,"temp",&source);add(&dsc,"cache",&target);
    CHECK(!source.rn_logd_dsc&&target.rn_logd_dsc);
    CHECK(ren(&stage,"temp",&dsc,"cache",VFS_RENAME_SWAP)==0);
    CHECK(source.rn_logd_dsc&&target.rn_logd_dsc&&find(&dsc,"cache")==&source);
    CHECK(ren(&dsc,"cache",&stage,"outside",0)==0&&source.rn_logd_dsc);
    CHECK(ren(&cr,"db",&cr,"renamed-db",0)==0&&dsc.rn_logd_role==RAMFS_LOGD_DSC);
    CHECK(ren(&stage,"outside",&dsc,"new-cache",0)==0&&source.rn_logd_dsc);
    struct ramfs_node replace;init(&replace,&cache,VREG,107);add(&stage,"atomic-temp",&replace);
    CHECK(!replace.rn_logd_dsc);
    CHECK(ren(&stage,"atomic-temp",&dsc,"new-cache",0)==0&&replace.rn_logd_dsc);
    CHECK(find(&dsc,"new-cache")==&replace&&source.rn_logd_dsc&&!source.rn_nlink);
#endif
    /* getdirentries64 records, next cookies, small buffers and classic ABI. */
    struct ramfs_node dir;init(&dir,&m,VDIR,20);dir.rn_parent=&root;
    init(&wide,&m,VREG,0x100000123ULL);add(&dir,"large-inode",&wide);
    char longname[256];memset(longname,'z',255);longname[255]=0;add(&dir,longname,&a);
    char buf[16384]={0};struct uio u;int eof,count;
    CHECK(offsetof(struct direntry,d_name)==21 && offsetof(struct dirent,d_name)==8);
    CHECK(read_dir(&dir,0,sizeof(buf),VNODE_READDIR_EXTENDED|VNODE_READDIR_REQSEEKOFF,buf,&u,&eof,&count)==0);
    CHECK(eof && count==4 && (off_t)u.used==u.offset);
    size_t at=0;unsigned n=0;
    while(at<u.used){struct direntry *d=(void *)(buf+at);CHECK(d->d_reclen%8==0 && d->d_seekoff==at+d->d_reclen && !d->d_name[d->d_namlen]);
        if(n==2)CHECK(d->d_fileno==0x100000123ULL && !strcmp(d->d_name,"large-inode"));
        if(n==3)CHECK(d->d_namlen==255 && d->d_reclen==280 && !strcmp(d->d_name,longname));
        n++;at+=d->d_reclen;}
    CHECK(n==4 && at==u.used);
    CHECK(read_dir(&dir,0,24,VNODE_READDIR_EXTENDED,buf,&u,&eof,&count)==0 && count==1 && !eof && u.offset==24);
    CHECK(read_dir(&dir,u.offset,24,VNODE_READDIR_EXTENDED,buf,&u,&eof,&count)==0 && count==1 && u.offset==48 && !strcmp(((struct direntry *)buf)->d_name,".."));
    CHECK(read_dir(&dir,0,8,VNODE_READDIR_EXTENDED,buf,&u,&eof,&count)==EINVAL && u.offset==0 && !u.used && !count);
    CHECK(read_dir(&dir,0,sizeof(buf),0,buf,&u,&eof,&count)==0 && eof && count==4);
    CHECK(((struct dirent *)buf)->d_fileno==20 && !strcmp(((struct dirent *)buf)->d_name,"."));
    CHECK(read_dir(&dir,0,sizeof(buf),VNODE_READDIR_REQSEEKOFF,buf,&u,&eof,&count)==EINVAL);
    CHECK(read_dir(&dir,-1,sizeof(buf),VNODE_READDIR_EXTENDED,buf,&u,&eof,&count)==EINVAL);
    CHECK(read_dir(&dir,9000,sizeof(buf),VNODE_READDIR_EXTENDED,buf,&u,&eof,&count)==0 && eof && u.offset==9000 && !count);
    CHECK(read_dir(&dir,0,0,VNODE_READDIR_EXTENDED,buf,&u,&eof,&count)==0 && !count && !u.used);
    CHECK(read_dir(&a,0,sizeof(buf),VNODE_READDIR_EXTENDED,buf,&u,&eof,&count)==ENOTDIR);
    /* Fsync must push mapped writes without the namespace lock and return errors. */
    struct vnop_fsync_args fs={&a};struct vnop_ioctl_args io={&a,F_BARRIERFSYNC};
    CHECK(ramfs_fsync(&fs)==0 && !sync_calls);
    a.rn_mapped_write=true;a.host_size=4096;
    CHECK(ramfs_ioctl(&io)==0 && sync_calls==1 && sync_length==4096 && sync_flags==(UBC_PUSHDIRTY|UBC_SYNC));
    sync_error=EIO;io.a_command=F_FULLFSYNC;
    CHECK(ramfs_ioctl(&io)==EIO && sync_calls==2);
    CHECK(ramfs_fsync(&fs)==EIO && sync_calls==3);
    io.a_command=0xdead;CHECK(ramfs_ioctl(&io)==ENOTTY && sync_calls==3);
    a.host_size=0;CHECK(ramfs_fsync(&fs)==0 && sync_calls==3);
    io.a_vp=&dir;io.a_command=F_BARRIERFSYNC;CHECK(ramfs_ioctl(&io)==0 && sync_calls==3);
    printf("PASS: %u actual RAMFS namespace/readdir64/sync checks\n",checks);return 0;
}
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source', type=Path)
    ap.add_argument('output', type=Path)
    args = ap.parse_args()
    s = args.source.read_text(encoding='utf-8')
    names = ['ramfs_dirent_alloc', 'ramfs_dirent_free', 'ramfs_dir_find',
             'ramfs_dir_add', 'ramfs_dir_remove', 'ramfs_rename_cycle',
             'ramfs_rename_common', 'ramfs_rename', 'ramfs_renamex',
             'ramfs_readdir', 'ramfs_sync_file', 'ramfs_fsync', 'ramfs_ioctl']
    # The separate 0145 regression workflow intentionally checks its pinned old
    # artifact. Execute the new classification only when present in the source.
    if re.search(r'^ramfs_logd_classify_locked\(', s, re.M):
        names.insert(names.index('ramfs_dir_add'), 'ramfs_logd_classify_locked')
    functions = {n: function(s, n) for n in names}
    assert '.opve_impl = (VOPFUNC)ramfs_renamex' in s
    assert '.opve_impl = (VOPFUNC)ramfs_fsync' in s
    args.output.mkdir(parents=True, exist_ok=True)
    constants = '\n'.join(re.findall(r'^#define RAMFS_LOGD_.*$', s, re.M)) + '\n'
    (args.output / 'ramfs-io.c').write_text(ADAPTERS+constants+'\n\n'.join(functions.values())+CHECKS,
                                           encoding='utf-8', newline='\n')
    (args.output / 'source-proof.json').write_text(json.dumps(dict(
        source_sha256=hashlib.sha256(args.source.read_bytes()).hexdigest(),
        functions={n: hashlib.sha256(f.encode()).hexdigest() for n,f in functions.items()},
        hardware_emulated=False, kernel_scheduling_emulated=False),indent=2)+'\n',encoding='utf-8')
    print(args.output / 'ramfs-io.c')


if __name__ == '__main__':
    main()

