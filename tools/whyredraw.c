/* Freestanding file probe and bounded private-memory test. No dyld/libSystem or file writes. */
typedef unsigned long U;
typedef long S;
static unsigned char data[65536] __attribute__((aligned(16384)));
static unsigned char status_bytes[512] __attribute__((aligned(16)));
static S call6(S number,S a,S b,S c,S d,S e,S f) {
#if defined(__aarch64__)
    register S r0 __asm__("x0")=a,r1 __asm__("x1")=b,r2 __asm__("x2")=c;
    register S r3 __asm__("x3")=d,r4 __asm__("x4")=e,r5 __asm__("x5")=f,r16 __asm__("x16")=number;
    unsigned error;
    __asm__ volatile("svc #0x80\n\tcset %w[err], cs" : "+r"(r0),[err]"=r"(error) : "r"(r1),"r"(r2),"r"(r3),"r"(r4),"r"(r5),"r"(r16) : "memory","cc");
    return error?-r0:r0;
#else
    register S rax __asm__("rax")=number|0x2000000,rdi __asm__("rdi")=a,rsi __asm__("rsi")=b,rdx __asm__("rdx")=c;
    register S r10 __asm__("r10")=d,r8 __asm__("r8")=e,r9 __asm__("r9")=f;
    unsigned char error;
    __asm__ volatile("syscall\n\tsetc %[err]" : "+a"(rax),[err]"=qm"(error) : "D"(rdi),"S"(rsi),"d"(rdx),"r"(r10),"r"(r8),"r"(r9) : "rcx","r11","memory","cc");
    return error?-rax:rax;
#endif
}
static U length(const char *s){U n=0;while(s[n])n++;return n;}
static void write_all(const char *s,U n){while(n){S r=call6(4,1,(S)s,n,0,0,0);if(r<=0)return;s+=r;n-=(U)r;}}
static void text(const char *s){write_all(s,length(s));}
static void value(const char *name,S n){char b[32];U x=n<0?(U)(-n):(U)n,i=32;do{b[--i]=(char)('0'+x%10);x/=10;}while(x);if(n<0)b[--i]='-';text(name);write_all(b+i,32-i);text("\n");}
static void hex(const char *name,U n){char b[16];for(int i=15;i>=0;i--){unsigned v=n&15;n>>=4;b[i]=(char)(v<10?'0'+v:'a'+v-10);}text(name);write_all(b,16);text("\n");}
static U number(const char *s){U n=0,base=10;if(s[0]=='0'&&s[1]=='x'){s+=2;base=16;}for(;*s;s++){unsigned v=*s>='0'&&*s<='9'?(unsigned)(*s-'0'):*s>='a'&&*s<='f'?(unsigned)(*s-'a'+10):99;if(v>=base||n>(~0UL-v)/base)return ~0UL;n=n*base+v;}return n;}
static U digest(const volatile unsigned char *p,U n){U h=14695981039346656037UL;for(U i=0;i<n;i++){h^=p[i];h*=1099511628211UL;}return h;}
/* Touch only this process's anonymous pages; the kernel frees them on any exit. */
static int same(const char *a,const char *b){while(*a&&*a==*b){a++;b++;}return *a==*b;}
static S pressure(const char *mib_arg,const char *seconds_arg){
    U mib=number(mib_arg),seconds=number(seconds_arg);
    if(!mib||mib>96||!seconds||seconds>15)return 2;
    U size=mib*1024*1024;
    S address=call6(197,0,size,3,0x1002,-1,0);
    value("pressure_mib=",mib);hex("pressure_map=",(U)address);if(address<0)return 1;
    volatile U *words=(volatile U*)(U)address;U state=0x9e3779b97f4a7c15UL;
    for(U i=0;i<size/sizeof(U);i++){state^=state<<13;state^=state>>7;state^=state<<17;words[i]=state;}
    U before=digest((const volatile unsigned char*)(U)address,size);
    hex("pressure_before_fnv1a64=",before);value("pressure_hold_seconds=",seconds);
    S tv[2]={(S)seconds,0};S waited=call6(93,0,0,0,0,(S)tv,0);value("pressure_wait=",waited);
    U after=digest((const volatile unsigned char*)(U)address,size);
    hex("pressure_after_fnv1a64=",after);S released=call6(73,address,size,0,0,0,0);value("pressure_unmap=",released);
    text("WHYRED RAW: pressure done\n");return waited<0||released<0||before!=after?1:0;
}
S raw_main(U *stack) __attribute__((used));
S raw_main(U *stack){
    U argc=stack[0];char **argv=(char**)(stack+1);text("WHYRED RAW: entered without dyld\n");
    if(argc==4&&same(argv[1],"pressure"))return pressure(argv[2],argv[3]);
    if(argc!=5&&argc!=6){text("usage: raw PATH OFFSET LENGTH MAP(0|1) [NOCACHE(0|1)] | pressure MIB(1..96) SECONDS(1..15)\n");return 2;}
    U offset=number(argv[2]),size=number(argv[3]),map=number(argv[4]),nocache=argc==6?number(argv[5]):0;
    if(!size||size>65536||offset>0x7fffffffffffffffUL-size||map>1||nocache>1)return 2;
    S fd=call6(5,(S)argv[1],0,0,0,0,0);value("open=",fd);if(fd<0)return 1;
    if(nocache){S flag=call6(92,fd,48,1,0,0,0);value("fcntl_nocache=",flag);if(flag<0){call6(6,fd,0,0,0,0,0);return 1;}}
    S st=call6(339,fd,(S)status_bytes,0,0,0,0);value("fstat=",st);
    if(!st){value("uid=",*(unsigned*)(status_bytes+16));value("mode=",*(unsigned short*)(status_bytes+4));value("file_size=",*(S*)(status_bytes+96));}
    S n=call6(153,fd,(S)data,size,offset,0,0);value("pread=",n);if(n>=0)hex("pread_fnv1a64=",digest(data,(U)n));
    if(map){
#if defined(__aarch64__)
        U page=16384;
#else
        U page=4096;
#endif
        U aligned=offset&~(page-1),delta=offset-aligned,total=delta+size;
        S address=call6(197,0,total,1,2,fd,aligned);hex("mmap=",(U)address);
        if(address>=0){text("mapped_read_begin\n");hex("mapped_fnv1a64=",digest((const volatile unsigned char*)((U)address+delta),size));call6(73,address,total,0,0,0,0);}
    }
    call6(6,fd,0,0,0,0,0);text("WHYRED RAW: done\n");return n<0?1:0;
}
#if defined(__aarch64__)
__attribute__((naked,noreturn)) void start(void){__asm__ volatile("mov x0, sp\n\tand x9, x0, #-16\n\tmov sp, x9\n\tbl _raw_main\n\tmov x16, #1\n\tsvc #0x80\n\tb .");}
#else
__attribute__((naked,noreturn)) void start(void){__asm__ volatile("movq %rsp, %rdi\n\tandq $-16, %rsp\n\tcallq _raw_main\n\tmovq %rax, %rdi\n\tmovq $0x2000001, %rax\n\tsyscall\n\tjmp .");}
#endif
