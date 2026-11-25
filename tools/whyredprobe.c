/* Bounded read-only file/VM diagnostics for a developer-owned device. */
#include <mach/mach.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/mount.h>
#include <fcntl.h>
#include <pwd.h>
#include <errno.h>
#include <inttypes.h>
#include <setjmp.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
static sigjmp_buf jump;
static volatile sig_atomic_t armed, caught;
static volatile uintptr_t fault_address;
static void fault(int sig, siginfo_t *info, void *unused) {
    (void)unused;
    if (armed) { caught=sig; fault_address=(uintptr_t)info->si_addr; armed=0; siglongjmp(jump,1); }
    const char msg[]="WHYRED PROBE: fatal signal outside mapped read\n";
    (void)write(2,msg,sizeof(msg)-1);_exit(128+sig);
}
static uint64_t digest(const unsigned char *p,size_t n) {
    uint64_t v=UINT64_C(14695981039346656037);
    for(size_t i=0;i<n;i++){v^=p[i];v*=UINT64_C(1099511628211);}return v;
}
static uint64_t number(const char *s) {
    char *end;errno=0;uint64_t n=strtoull(s,&end,0);
    if(errno||*end||*s=='-'){fprintf(stderr,"invalid number\n");exit(2);}return n;
}
static int file_probe(const char *path,uint64_t offset,size_t length) {
    if(offset>INT64_MAX-length||!length||length>65536)return 2;
    errno=0;int fd=open(path,O_RDONLY|O_CLOEXEC);int e=errno;
    printf("open result=%d errno=%d\n",fd>=0?0:-1,fd>=0?0:e);if(fd<0)return 1;
    struct stat s;struct statfs fs;
    if(fstat(fd,&s)){perror("fstat");close(fd);return 1;}
    printf("stat size=%" PRId64 " uid=%u gid=%u mode=%o\n",(int64_t)s.st_size,s.st_uid,s.st_gid,s.st_mode);
    if(!fstatfs(fd,&fs))printf("fs type=%s flags=0x%x free=%" PRIu64 " block=%u\n",fs.f_fstypename,fs.f_flags,(uint64_t)fs.f_bfree,(unsigned)fs.f_bsize);
    unsigned char bytes[65536];errno=0;ssize_t n=pread(fd,bytes,length,(off_t)offset);e=errno;
    printf("pread offset=%" PRIu64 " requested=%zu result=%zd errno=%d",offset,length,n,n<0?e:0);
    if(n>=0)printf(" fnv1a64=%016" PRIx64,digest(bytes,(size_t)n));putchar('\n');
    if(offset>=(uint64_t)s.st_size||length>(uint64_t)s.st_size-offset){close(fd);return n<0?1:0;}
    long page=sysconf(_SC_PAGESIZE);if(page<=0){close(fd);return 1;}
    uint64_t aligned=offset&~((uint64_t)page-1);size_t delta=(size_t)(offset-aligned),size=delta+length;
    errno=0;void *map=mmap(NULL,size,PROT_READ,MAP_PRIVATE,fd,(off_t)aligned);e=errno;
    printf("mmap result=%d errno=%d\n",map==MAP_FAILED?-1:0,map==MAP_FAILED?e:0);
    if(map!=MAP_FAILED){
        caught=0;fault_address=0;
        if(!sigsetjmp(jump,1)){
            armed=1;volatile const unsigned char *p=(const unsigned char*)map+delta;uint64_t v=UINT64_C(14695981039346656037);
            for(size_t i=0;i<length;i++){v^=p[i];v*=UINT64_C(1099511628211);}armed=0;
            printf("mapped_read bytes=%zu fnv1a64=%016" PRIx64 "\n",length,v);
        }else printf("mapped_read signal=%d address=0x%" PRIxPTR "\n",(int)caught,(uintptr_t)fault_address);
        munmap(map,size);
    }
    close(fd);return n<0||map==MAP_FAILED||caught?1:0;
}
static int memory_probe(pid_t pid,uint64_t address,size_t length) {
    if(pid<=0||!length||length>65536||address>UINT64_MAX-length)return 2;
    task_t task=MACH_PORT_NULL;kern_return_t kr=task_for_pid(mach_task_self(),pid,&task);
    printf("task_for_pid pid=%d kr=%d\n",pid,kr);if(kr)return 1;
    vm_address_t region=(vm_address_t)address;vm_size_t size=0;vm_region_basic_info_data_64_t info;
    mach_msg_type_number_t count=VM_REGION_BASIC_INFO_COUNT_64;mach_port_t object=MACH_PORT_NULL;
    kr=vm_region_64(task,&region,&size,VM_REGION_BASIC_INFO_64,(vm_region_info_t)&info,&count,&object);
    printf("vm_region kr=%d",kr);if(!kr)printf(" start=0x%" PRIx64 " size=0x%" PRIx64 " prot=%d/%d",(uint64_t)region,(uint64_t)size,info.protection,info.max_protection);putchar('\n');
    if(object)mach_port_deallocate(mach_task_self(),object);
    unsigned char data[65536];vm_size_t got=0;
    kr=vm_read_overwrite(task,(vm_address_t)address,length,(vm_address_t)data,&got);
    printf("vm_read address=0x%" PRIx64 " requested=%zu kr=%d bytes=%" PRIu64,address,length,kr,(uint64_t)got);
    if(!kr&&got==length)printf(" fnv1a64=%016" PRIx64,digest(data,length));putchar('\n');
    mach_port_deallocate(mach_task_self(),task);return kr?1:0;
}
int main(int argc,char **argv) {
    struct sigaction action;memset(&action,0,sizeof(action));action.sa_sigaction=fault;action.sa_flags=SA_SIGINFO;sigemptyset(&action.sa_mask);
    if(sigaction(SIGBUS,&action,NULL)||sigaction(SIGSEGV,&action,NULL)){perror("sigaction");return 1;}
    if(argc==2&&!strcmp(argv[1],"account")){
        errno=0;struct passwd *p=getpwnam("root");int e=errno;
        printf("getpwnam root found=%d errno=%d",p!=NULL,e);if(p)printf(" uid=%u gid=%u shell=%s home=%s",p->pw_uid,p->pw_gid,p->pw_shell,p->pw_dir);putchar('\n');return p?0:1;
    }
    if(argc==5&&!strcmp(argv[1],"file"))return file_probe(argv[2],number(argv[3]),(size_t)number(argv[4]));
    if(argc==5&&!strcmp(argv[1],"memory")){uint64_t pid=number(argv[2]);if(pid>INT32_MAX)return 2;return memory_probe((pid_t)pid,number(argv[3]),(size_t)number(argv[4]));}
    fprintf(stderr,"usage: whyredprobe account | file PATH OFFSET LENGTH | memory PID ADDRESS LENGTH (max65536)\n");return 2;
}
