/* Kernel service adapters. Exact driver functions are inserted by the generator. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <stdatomic.h>
#include <setjmp.h>
#include <sys/socket.h>
#include <sys/uio.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include "whyred_usb_hw.h"
#ifndef __unused
#define __unused __attribute__((unused))
#endif
#define PAGE_MASK 0x3fffULL
#define KERN_SUCCESS 0
#define KMA_DATA 1
#define KMA_ZERO 2
#define KMA_PERMANENT 4
#define VM_KERN_MEMORY_IOKIT 1
#define ETHER_HDR_LEN 14u
#define ETHER_MAX_LEN 1518u
#define ETHER_CRC_LEN 4u
#define ETHER_ADDR_LEN 6u
#define MBUF_DONTWAIT 0
#define MBUF_TYPE_DATA 0
#define MBUF_EXT 1
#ifndef KEV_DL_SUBCLASS
#define KEV_DL_SUBCLASS 2
#define KEV_DL_LINK_ON 13
#define KEV_DL_LINK_OFF 12
#endif
#define FALSE false
#define MAX(a,b) ((a)>(b)?(a):(b))
#define MIN(a,b) ((a)<(b)?(a):(b))
#ifndef bzero
#define bzero(p,n) memset(p,0,n)
#endif
typedef uintptr_t vm_offset_t;
typedef uint64_t ppnum_t;
typedef uint64_t addr64_t;
typedef int wait_result_t;
typedef uintptr_t thread_t;
typedef void (*thread_continue_t)(void *, wait_result_t);
typedef int lck_mtx_t;
typedef void *ifnet_t;
typedef int errno_t;
struct host_mbuf { unsigned char bytes[2048]; size_t offset, len, packet; unsigned flags; };
typedef struct host_mbuf *mbuf_t;
typedef void *socket_t;
struct ifnet_stat_increment_param { uint64_t packets_in, bytes_in; };
/* ACTUAL CONSTANTS */
/* ACTUAL DECLARATIONS */
static void ud_rx_arm(void);
static void ud_tx_kick_locked(void);
static void ud_link_event(bool);
static void ud_data_stop(bool);
static void sweet_usb_gadget_start(vm_offset_t);
static uint32_t sweet_log_copy(uint64_t *, char *, uint32_t);
static uint64_t sweet_log_position(void);
#define SWEET_LOG_SIZE (4u << 20)
static char sweet_log_ring[SWEET_LOG_SIZE];
static _Atomic uint64_t sweet_log_total;
static unsigned checks, held, mbufs, received, links_up, links_down, sleep_count, sleep_limit;
static unsigned sends, send_failures, sent_lengths[32], thread_calls, setup_stalls;
static char first_send[1400], second_send[1400];
static jmp_buf thread_exit;
static struct {
    uint32_t gcc[WHYRED_USB_GCC_SIZE/4], dwc[WHYRED_USB_DWC_SIZE/4], phy[WHYRED_USB_PHY_SIZE/4], qs[WHYRED_USB_QS_SIZE/4];
    _Alignas(128) unsigned char dma[UD_SIZE];
    unsigned snapshot_lines, dwc_reads, dwc_writes, deadlines;
    uint64_t now;
    unsigned maps, reads, writes, delays, fail_map, stuck_clock, clock_delay;
    bool reject_mux, stuck_command, command_error, missing_resource, stuck_stop, stuck_reset, stuck_run;
    bool fail_dma, fail_ifnet, fail_thread, fail_mbuf, log_enabled, dma_clean;
    bool replicate_phy_byte, stuck_phy_pll, reject_phy_power, phy_resume_active;
    bool reject_test_release, corrupt_test_release;
    unsigned test_writes, dma_allocations;
    unsigned phy_writes, phy_resume_at, phy_lock_delay;
    bool zero_control_resource, late_result_error, result_reactivates;
    unsigned delayed_index, index_reads_left[6], pending_index[6], start_reads[6];
    uint64_t physical_page;
    int boot_mode, lock;
    unsigned commands, starts, ends;
} model;
static struct whyred_usb_hw usb_hw;
static uint32_t usb_attempted;
static void *kernel_map, *kernel_pmap;
static bool cmpxchg(uint32_t *p,uint32_t old,uint32_t value) { if (*p!=old) return false; *p=value; return true; }
#define os_atomic_cmpxchg(p,o,n,order) cmpxchg(p,o,n)
#define os_atomic_load(p,order) (*(p))
#define os_atomic_add_orig(p,n,order) atomic_fetch_add(p,n)
static void host_barrier(void) {}
static bool clocks_ready(void) {
    if (!(model.gcc[WHYRED_USB_GDSCR/4] & (1u<<31)) || (model.gcc[WHYRED_USB_BCR/4]&1)) return false;
    for (unsigned i=0;i<WHYRED_USB_CLOCKS;i++) if (model.gcc[whyred_usb_clocks[i]/4] & WHYRED_USB_CLK_OFF) return false;
    return true;
}
static uintptr_t hw_map(void *ctx,uintptr_t pa,size_t size) {
    (void)ctx; model.maps++;
    if (pa==model.fail_map) return 0;
    if (pa==WHYRED_USB_GCC_PA) {assert(size==sizeof(model.gcc)); return (uintptr_t)model.gcc;}
    assert(clocks_ready());
    if (pa==WHYRED_USB_PHY_PA) {assert(size==sizeof(model.phy)); return (uintptr_t)model.phy;}
    if (pa==WHYRED_USB_DWC_PA) {assert(size==sizeof(model.dwc)); return (uintptr_t)model.dwc;}
    if (pa==WHYRED_USB_QS_PA) {assert(size==sizeof(model.qs)); return (uintptr_t)model.qs;}
    abort();
}
static uint32_t hw_read(void *ctx,uintptr_t base,uint32_t off) {
    (void)ctx; model.reads++; assert(!(off&3));
    if (base==(uintptr_t)model.gcc) {
        assert(off<sizeof(model.gcc));
        for (unsigned i=0;i<WHYRED_USB_CLOCKS;i++) if (off==whyred_usb_clocks[i] && (model.gcc[off/4]&1)) {
            if (model.stuck_clock!=i+1 && !model.clock_delay) model.gcc[off/4]&=~WHYRED_USB_CLK_OFF;
            else if (model.clock_delay) model.clock_delay--;
        }
        return model.gcc[off/4];
    }
    assert(clocks_ready());
    if (base==(uintptr_t)model.phy) {
        assert(off<sizeof(model.phy));
        if (off==WHYRED_USB_PHY_PLL_STATUS && model.phy_resume_active && !model.stuck_phy_pll &&
            model.delays-model.phy_resume_at>=WHYRED_USB_PHY_SETTLE_US+model.phy_lock_delay)
            model.phy[off/4]|=WHYRED_USB_PLL_LOCK;
        return model.phy[off/4];
    }
    if (base==(uintptr_t)model.qs) {assert(off<sizeof(model.qs)); return model.qs[off/4];}
    if (base==(uintptr_t)model.dwc) {assert(off<sizeof(model.dwc)); return model.dwc[off/4];}
    abort();
}
static void hw_write(void *ctx,uintptr_t base,uint32_t off,uint32_t value) {
    (void)ctx; model.writes++;
    if (base==(uintptr_t)model.gcc) {
        bool known=false; for (unsigned i=0;i<WHYRED_USB_CLOCKS;i++) known|=off==whyred_usb_clocks[i];
        assert(known); /* No reset, source/PLL, GDSC, PHY, PMIC or SMMU writes. */
        model.gcc[off/4]=value;
        if (!(value&1)) {assert(!model.phy_resume_active);model.gcc[off/4]|=WHYRED_USB_CLK_OFF;}
        return;
    }
    if (base==(uintptr_t)model.phy) {
        if (off==WHYRED_USB_PHY_UTMI_CTRL2) {
            assert(clocks_ready() && !(model.dwc[DCTL/4]&DCTL_RUN_STOP));
            assert(model.dwc[DSTS/4]&DSTS_DEVCTRLHLT);
            assert(!model.dma_allocations && !model.starts && !thread_calls);
            assert(value<=0xffu);
            model.test_writes++;
            if (model.reject_test_release && !(value&WHYRED_USB_UTMI_TEST_MUX)) return;
            if (model.corrupt_test_release && !(value&WHYRED_USB_UTMI_TEST_MUX)) value^=0x80u;
            model.phy[off/4]=model.replicate_phy_byte?value*0x01010101u:value;
            return;
        }
        assert(clocks_ready() && off==WHYRED_USB_PHY_POWERDOWN && (value==0x22 || value==0x23));
        assert(!(model.gcc[WHYRED_USB_QUSB_BCR/4]&1) && !(model.gcc[WHYRED_USB_AHB2PHY_BCR/4]&1));
        model.phy_writes++;
        if (value==0x22 && model.reject_phy_power) return;
        model.phy[off/4]=model.replicate_phy_byte?value*0x01010101u:value;
        model.phy_resume_active=value==0x22;
        if (model.phy_resume_active) {assert(model.gcc[0x88018/4]&1);model.phy_resume_at=model.delays;}
        else model.phy[WHYRED_USB_PHY_PLL_STATUS/4]&=~WHYRED_USB_PLL_LOCK;
        return;
    }
    assert(base==(uintptr_t)model.qs && off==8 && clocks_ready());
    model.qs[off/4]=model.reject_mux ? value & ~1u : value;
}
static void delay(unsigned us) { model.delays+=us; }
static void hw_delay(void *ctx,unsigned us) { (void)ctx; delay(us); }
static const struct whyred_usb_io usb_io={.map=hw_map,.read=hw_read,.write=hw_write,.delay_us=hw_delay};
static uint32_t usb_rd(vm_offset_t base,uint32_t off) { return hw_read(NULL,base,off); }
static uint32_t dwc_rd(uint32_t off) {
    model.dwc_reads++;
    assert(clocks_ready() && off<sizeof(model.dwc));
    if (off>=DEPCMD(0) && off<=DEPCMD(5) && ((off-DEPCMD(0))%16)==0) {
        unsigned ep=(off-DEPCMD(0))/16;
        if ((model.dwc[off/4]&15)==DEPCMD_STARTTRANSFER) {
            if (model.index_reads_left[ep] && !--model.index_reads_left[ep])
                model.dwc[off/4]|=model.pending_index[ep]<<16;
            if (++model.start_reads[ep]>=2) {
                if (model.late_result_error) model.dwc[off/4]|=1u<<12;
                if (model.result_reactivates) model.dwc[off/4]|=DEPCMD_CMDACT;
            }
        }
    }
    return model.dwc[off/4];
}
static void dwc_wr(uint32_t off,uint32_t value) {
    model.dwc_writes++;
    assert(clocks_ready() && off<sizeof(model.dwc));
    if (off==GEVNTADRLO) assert(model.dma_clean); /* KMA_ZERO dirties event-ring cache lines. */
    model.dwc[off/4]=value;
    if (off==DCTL) {
        if (value&DCTL_CSFTRST) { if (!model.stuck_reset) model.dwc[off/4]&=~DCTL_CSFTRST; }
        if (value&DCTL_RUN_STOP) {if (!model.stuck_run) model.dwc[DSTS/4]&=~DSTS_DEVCTRLHLT;}
        else if (!model.stuck_stop) model.dwc[DSTS/4]|=DSTS_DEVCTRLHLT;
    }
    if (off>=DEPCMD(0) && off<=DEPCMD(5) && ((off-DEPCMD(0))%16)==0) {
        unsigned ep=(off-DEPCMD(0))/16,cmd=value&15; model.commands++;
        model.start_reads[ep]=model.index_reads_left[ep]=model.pending_index[ep]=0;
        if (cmd==DEPCMD_SETSTALL) setup_stalls++;
        if (model.stuck_command) return;
        model.dwc[off/4]=value & ~DEPCMD_CMDACT;
        if (model.command_error) model.dwc[off/4]|=1u<<12;
        if (cmd==DEPCMD_STARTTRANSFER) {
            assert(model.dma_clean);
            model.starts++;
            unsigned index=model.missing_resource || (model.zero_control_resource && ep<2) ? 0 : ep+1;
            model.dwc[off/4]=(model.dwc[off/4]&0xffffu)|(index<<16);
            if (index && model.delayed_index) {
                model.pending_index[ep]=index;model.index_reads_left[ep]=model.delayed_index;
                model.dwc[off/4]&=0xffffu;
            }
        }
        if (cmd==DEPCMD_ENDTRANSFER) model.ends++;
    }
    if (off==GEVNTCOUNT) model.dwc[off/4]=0;
}
static void ud_sync(uint32_t off,uint32_t len) {
    assert(off<=UD_SIZE && len<=UD_SIZE-off);
    if (!off && len==UD_SIZE) model.dma_clean=true;
}
static int host_printf(const char *fmt,...) __attribute__((format(printf,1,2)));
static char snapshot_output[4][512];
static int host_printf(const char *fmt,...)
{
    if (!strncmp(fmt,"WHYRED USB: snapshot=",21)) {
        va_list args; va_start(args,fmt);
        int count=vsnprintf(snapshot_output[model.snapshot_lines%4],512,fmt,args);
        va_end(args); assert(count>0 && count<512); model.snapshot_lines++;
    }
    return 0;
}
#define printf host_printf
static void lck_mtx_lock(lck_mtx_t *p) { assert(p && held++==0); }
static void lck_mtx_unlock(lck_mtx_t *p) { assert(p && held--==1); }
static int PE_parse_boot_argn(const char *name,void *p,int size) {
    assert(size==sizeof(int));
    if (!strcmp(name,"whyred-usb")) {*(int *)p=model.boot_mode;return 1;}
    if (!strcmp(name,"sweetusblog")) {*(int *)p=model.log_enabled;return 1;}
    return 0;
}
#define NSEC_PER_SEC 1000000000u
static uint64_t mach_absolute_time(void) { return model.now; }
static void clock_interval_to_deadline(unsigned interval,unsigned scale,uint64_t *out)
{ assert(interval==1 && scale==NSEC_PER_SEC); model.deadlines++; *out=model.now+(uint64_t)interval*scale; }
static void ud_sleep_ms(unsigned ms) { model.now+=(uint64_t)ms*1000000; if (++sleep_count>sleep_limit) longjmp(thread_exit,1); }
static int kmem_alloc_contig(void *map,vm_offset_t *p,size_t n,uint64_t mask,int a,int b,int flags,int tag) {
    (void)map;(void)mask;(void)a;(void)b;(void)flags;(void)tag;assert(n==UD_SIZE);
    assert(!(model.phy[WHYRED_USB_PHY_UTMI_CTRL2/4]&WHYRED_USB_UTMI_TEST_MUX));
    model.dma_allocations++;
    if (model.fail_dma) return 3; *p=(uintptr_t)model.dma; memset(model.dma,0,sizeof(model.dma));model.dma_clean=false;return 0;
}
static ppnum_t pmap_find_phys(void *map,addr64_t address) { (void)map;assert(address==(uintptr_t)model.dma);return model.physical_page?model.physical_page:0xb0000000ULL>>14; }
#define ptoa_64(n) ((uint64_t)(n)<<14)
static int ud_if_create(void) { if(model.fail_ifnet)return -1;ud.ifp=(void *)1;ud.lock=&model.lock;return 0; }
static int kernel_thread_start(thread_continue_t f,void *arg,thread_t *thread) {
    (void)f;(void)arg;thread_calls++;*thread=1;return model.fail_thread?3:0;
}
static void thread_deallocate(thread_t thread) { assert(thread==1); }
static void ifnet_set_baudrate(ifnet_t ifp,uint64_t rate) {(void)ifp;assert(rate==12000000||rate==480000000);}
static int mbuf_gethdr(int wait,int type,mbuf_t *m) {
    (void)wait;(void)type;if(model.fail_mbuf)return 12;*m=calloc(1,sizeof(**m));mbufs++;return 0;
}
static int mbuf_mclget(int wait,int type,mbuf_t *m) {(void)wait;(void)type;(*m)->flags|=MBUF_EXT;return 0;}
static unsigned mbuf_flags(mbuf_t m) {return m->flags;}
static size_t mbuf_maxlen(mbuf_t m) {(void)m;return 2048;}
static void *mbuf_data(mbuf_t m) {return m->bytes+m->offset;}
static void mbuf_setlen(mbuf_t m,size_t n) {m->len=n;}
static void mbuf_pkthdr_setlen(mbuf_t m,size_t n) {m->packet=n;}
static void mbuf_pkthdr_setrcvif(mbuf_t m,ifnet_t ifp) {(void)m;(void)ifp;}
static void mbuf_pkthdr_setheader(mbuf_t m,void *p) {(void)m;(void)p;}
static void mbuf_pkthdr_adjustlen(mbuf_t m,int n) {m->packet=(size_t)((int64_t)m->packet+n);}
static size_t mbuf_len(mbuf_t m) {return m->len;}
static size_t mbuf_pkthdr_len(mbuf_t m) {return m->packet;}
static int mbuf_setdata(mbuf_t m,void *data,size_t len) {m->offset=(unsigned char *)data-m->bytes;m->len=len;return 0;}
static void mbuf_freem(mbuf_t m) {assert(mbufs);mbufs--;free(m);}
static int mbuf_copydata(mbuf_t m,size_t off,size_t n,void *out) {
    if(off>m->len||n>m->len-off)return 22;memcpy(out,m->bytes+m->offset+off,n);return 0;
}
static int ifnet_input(ifnet_t ifp,mbuf_t m,struct ifnet_stat_increment_param *s) {
    (void)ifp;assert(m->offset==14 && m->len==m->packet && s->packets_in==1);received++;mbuf_freem(m);return 0;
}
static void ifnet_stat_increment_out(ifnet_t ifp,uint64_t packets,uint64_t bytes,uint64_t errors) {(void)ifp;(void)packets;(void)bytes;(void)errors;}
static int dlil_post_msg(ifnet_t ifp,int cls,int ev,void *data,int len,bool locked) {
    (void)ifp;(void)cls;(void)data;(void)len;(void)locked;assert(!held);if(ev==KEV_DL_LINK_ON)links_up++;else links_down++;return 0;
}
static int sock_socket(int family,int type,int protocol,void *a,void *b,socket_t *so) {
    (void)a;(void)b;assert(family==PF_INET&&type==SOCK_DGRAM&&protocol==IPPROTO_UDP);*so=(void *)1;return 0;
}
static void sock_close(socket_t so) {assert(so);}
static int sock_send(socket_t so,struct msghdr *msg,int flags,size_t *sent) {
    assert(so && flags==MSG_DONTWAIT && msg->msg_iovlen==1);assert(!held);
    struct sockaddr_in *to=msg->msg_name;assert(to->sin_addr.s_addr==htonl(0xc0a80701)&&to->sin_port==htons(5140));
    size_t n=msg->msg_iov[0].iov_len;assert(n<=1400);
    if(sends<32)sent_lengths[sends]=(unsigned)n;
    if(sends==0)memcpy(first_send,msg->msg_iov[0].iov_base,n);
    if(sends==1)memcpy(second_send,msg->msg_iov[0].iov_base,n);
    sends++;if(send_failures){send_failures--;*sent=0;return 55;}*sent=n;return 0;
}
/* ACTUAL FUNCTIONS */
#undef printf
#define CHECK(c) do {checks++;if(!(c)){fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#c);return 1;}}while(0)
static void reset_model(void) {
    assert(!mbufs && !held);memset(&model,0,sizeof(model));memset(&ud,0,sizeof(ud));usb_attempted=0;
    model.gcc[WHYRED_USB_GDSCR/4]=1u<<31;model.phy[WHYRED_USB_PHY_POWERDOWN/4]=0x22;
    model.phy[WHYRED_USB_PHY_PLL_STATUS/4]=WHYRED_USB_PLL_LOCK;
    model.dwc[0xc120/4]=0x5533250a;model.dwc[GCTL/4]=0x2400;model.dwc[DCTL/4]=DCTL_RUN_STOP;
    model.qs[8/4]=0x100040;model.log_enabled=true;
    for(unsigned i=0;i<WHYRED_USB_CLOCKS;i++)model.gcc[whyred_usb_clocks[i]/4]=0x200001;
    links_up=links_down=received=setup_stalls=thread_calls=sleep_count=sends=send_failures=0;
    sweet_log_total=0;
}
static void start_driver(void) {model.boot_mode=2;sweet_usb_probe();}
static void shutdown_handoff(void) {
    reset_model();model.replicate_phy_byte=true;
    model.phy[WHYRED_USB_PHY_POWERDOWN/4]=0x23232323;
    model.phy[WHYRED_USB_PHY_PLL_STATUS/4]=0x10001000;
    model.gcc[0x88018/4]=model.gcc[0x88014/4]=3;
}
static uint32_t trb_for(unsigned ep) {return ep==0?UD_TRB_OUT:ep==1?UD_TRB_IN:ep==EP_RX?UD_TRB_RX:ep==EP_TX?UD_TRB_TX:UD_TRB_INT;}
static void complete(unsigned ep,uint32_t residual) {
    uint32_t *trb=(uint32_t *)(model.dma+trb_for(ep));trb[2]=residual;trb[3]&=~TRB_HWO;
    ud_event((ep<<1)|(1u<<6));
}
static void setup(uint8_t type,uint8_t req,uint16_t value,uint16_t index,uint16_t length) {
    assert(ud.state==EP0_SETUP && ud.active[0]);
    uint8_t *p=model.dma+UD_SETUP;p[0]=type;p[1]=req;p[2]=(uint8_t)value;p[3]=(uint8_t)(value>>8);
    p[4]=(uint8_t)index;p[5]=(uint8_t)(index>>8);p[6]=(uint8_t)length;p[7]=(uint8_t)(length>>8);
    complete(0,0);
    if(ud.failed||ud.state==EP0_SETUP)return;
    if(ud.state==EP0_DATA)complete(1,0);
    assert(ud.state==EP0_WAIT_STATUS2||ud.state==EP0_WAIT_STATUS3);
    unsigned ep=ud.data_in?0:1;ud_event((ep<<1)|(3u<<6)|(2u<<12));complete(ep,0);
    assert(ud.state==EP0_SETUP);
}
static mbuf_t packet(size_t n,unsigned char value) {
    mbuf_t m=NULL;assert(mbuf_gethdr(0,0,&m)==0);memset(m->bytes,value,MIN(n,sizeof(m->bytes)));m->len=m->packet=n;return m;
}
static void ready(void) {setup(0,5,4,0,0);setup(0,9,1,0,0);setup(0x21,0x43,12,0,0);setup(1,11,1,1,0);}
static void stop_driver(void) {if(ud.lock)ud_data_stop(true);assert(!mbufs&&!held);}
int main(void) {
    struct whyred_usb_hw hw;
    CHECK(WHYRED_USB_PHY_UTMI_CTRL1==0xc0 && WHYRED_USB_PHY_UTMI_CTRL2==0xc4);
    CHECK(WHYRED_USB_UTMI_TEST_MUX==0x40 && WHYRED_USB_UTMI_NONDRIVE_FS==0x15);
    reset_model();hw=(struct whyred_usb_hw){0};CHECK(!whyred_usb_hw_release_test(&usb_io,&hw));
    CHECK(!model.reads&&!model.writes);
    reset_model();CHECK(whyred_usb_hw_prepare(&usb_io,2,&hw)==WHYRED_USB_HW_OK);
    CHECK(!whyred_usb_hw_release_test(&usb_io,&hw));CHECK(!model.test_writes); /* Still RUN. */
    model.dwc[DCTL/4]=0;CHECK(!whyred_usb_hw_release_test(&usb_io,&hw)); /* Halt not acknowledged. */
    model.dwc[DSTS/4]=DSTS_DEVCTRLHLT;CHECK(whyred_usb_hw_release_test(&usb_io,&hw));
    CHECK(!model.test_writes&&!hw.utmi_release_attempted);
    for(unsigned bits=0;bits<256;bits++)if(bits&WHYRED_USB_UTMI_TEST_MUX) {
        reset_model();model.replicate_phy_byte=true;
        model.phy[0xc0/4]=0x35353535;model.phy[0xc4/4]=bits*0x01010101u;
        start_driver();CHECK(!ud.failed&&model.test_writes==1&&model.dma_allocations==1);
        CHECK(model.phy[0xc0/4]==0x35353535);
        CHECK(model.phy[0xc4/4]==(bits&~WHYRED_USB_UTMI_TEST_MUX)*0x01010101u);
        CHECK(usb_hw.utmi_release_attempted&&usb_hw.utmi_release_changed&&!usb_hw.utmi_release_restored);
        CHECK(model.phy[WHYRED_USB_PHY_POWERDOWN/4]==0x22&&model.phy[WHYRED_USB_PHY_PLL_STATUS/4]==0x20);
        stop_driver();
    }
    reset_model();model.phy[0xc0/4]=0x35;model.phy[0xc4/4]=0x40;
    model.reject_test_release=true;start_driver();
    CHECK(ud.failed&&model.test_writes==2&&!model.dma_allocations&&!model.starts&&!thread_calls);
    CHECK(usb_hw.utmi_release_restored&&model.phy[0xc4/4]==0x40);
    reset_model();model.phy[0xc0/4]=0x35;model.phy[0xc4/4]=0x40;
    model.corrupt_test_release=true;start_driver();
    CHECK(ud.failed&&model.test_writes==2&&!model.dma_allocations&&!thread_calls);
    CHECK(!usb_hw.utmi_release_restored&&model.phy[0xc4/4]==0xc0); /* Retain non-owned sampled bits. */
    const unsigned unknown_overrides[]={0,0x14,0x11,0x05,0x37,0x3d};
    for(unsigned i=0;i<sizeof(unknown_overrides)/sizeof(unknown_overrides[0]);i++) {
        reset_model();model.phy[0xc0/4]=unknown_overrides[i];model.phy[0xc4/4]=0x40;
        start_driver();CHECK(ud.failed&&!model.test_writes&&!model.dma_allocations&&!thread_calls);
    }
    reset_model();model.boot_mode=1;model.phy[0xc0/4]=0x35;model.phy[0xc4/4]=0x40;
    sweet_usb_probe();CHECK(!model.writes&&!model.test_writes&&!model.dma_allocations&&!thread_calls);
    reset_model();model.stuck_stop=true;model.phy[0xc0/4]=0x35;model.phy[0xc4/4]=0x40;
    start_driver();CHECK(ud.failed&&!model.test_writes&&!model.dma_allocations);
    CHECK(ud_phone_mac[0]==2&&ud_phone_mac[5]==2);
    CHECK(WHYRED_USB_GCC_PA==0x00100000&&WHYRED_USB_GDSCR==0xf004&&WHYRED_USB_BCR==0xf000);
    CHECK(WHYRED_USB_DWC_PA==0x0a800000&&WHYRED_USB_DWC_SIZE==0xd000);
    CHECK(WHYRED_USB_PHY_PA==0x0c012000&&WHYRED_USB_PHY_SIZE==0x180);
    CHECK(WHYRED_USB_QS_PA==0x0a8f8800&&WHYRED_USB_QS_SIZE==0x100);
    CHECK(WHYRED_USB_PHY_POWERDOWN==0xb4&&WHYRED_USB_PHY_PLL_STATUS==0x38&&WHYRED_USB_PLL_LOCK==0x20);
    CHECK(WHYRED_USB_QUSB_BCR==0x12000 && WHYRED_USB_AHB2PHY_BCR==0x6a000);
    const uint32_t expected_clocks[]={0xf008,0xf00c,0xf010,0x5018,0xf03c,0x6a004};
    CHECK(sizeof(expected_clocks)==sizeof(whyred_usb_clocks));
    for(unsigned i=0;i<WHYRED_USB_CLOCKS;i++)CHECK(whyred_usb_clocks[i]==expected_clocks[i]);
    for(int mode=-1;mode<=3;mode++)if(mode!=1&&mode!=2){reset_model();CHECK(whyred_usb_hw_prepare(&usb_io,mode,&hw)==WHYRED_USB_HW_OFF);CHECK(!model.maps&&!model.reads&&!model.writes);}
    reset_model();model.gcc[WHYRED_USB_GDSCR/4]=0;CHECK(whyred_usb_hw_prepare(&usb_io,2,&hw)==WHYRED_USB_HW_POWER);CHECK(model.maps==1&&!model.writes);
    reset_model();model.gcc[WHYRED_USB_BCR/4]=1;CHECK(whyred_usb_hw_prepare(&usb_io,2,&hw)==WHYRED_USB_HW_RESET);CHECK(model.maps==1&&!model.writes);
    const uintptr_t regions[]={WHYRED_USB_GCC_PA,WHYRED_USB_PHY_PA,WHYRED_USB_DWC_PA,WHYRED_USB_QS_PA};
    for(unsigned i=0;i<4;i++){reset_model();model.fail_map=(unsigned)regions[i];CHECK(whyred_usb_hw_prepare(&usb_io,2,&hw)==WHYRED_USB_HW_MAP);}
    for(unsigned i=0;i<WHYRED_USB_CLOCKS;i++){
        reset_model();model.gcc[whyred_usb_clocks[i]/4]=0x80200000;
        CHECK(whyred_usb_hw_prepare(&usb_io,1,&hw)==WHYRED_USB_HW_CLOCK);CHECK(!model.writes&&model.maps==1);
        CHECK(whyred_usb_hw_prepare(&usb_io,2,&hw)==WHYRED_USB_HW_OK);CHECK(model.writes==1&&hw.changed_clocks==(1u<<i));
        whyred_usb_hw_rollback(&usb_io,&hw);CHECK(model.gcc[whyred_usb_clocks[i]/4]==0x80200000);
        reset_model();for(unsigned j=0;j<=i;j++)model.gcc[whyred_usb_clocks[j]/4]=0x80200000;
        model.stuck_clock=i+1;CHECK(whyred_usb_hw_prepare(&usb_io,2,&hw)==WHYRED_USB_HW_CLOCK);
        CHECK(model.delays==WHYRED_USB_CLOCK_POLLS&&model.maps==1);
        for(unsigned j=0;j<=i;j++)CHECK(model.gcc[whyred_usb_clocks[j]/4]==0x80200000);
    }
    for(unsigned power=0;power<64;power++)if((power&0x23)!=0x22){reset_model();model.phy[WHYRED_USB_PHY_POWERDOWN/4]=power;CHECK(whyred_usb_hw_prepare(&usb_io,2,&hw)==WHYRED_USB_HW_PHY);CHECK(model.maps==2&&!model.writes);}
    reset_model();model.phy[WHYRED_USB_PHY_PLL_STATUS/4]=0;CHECK(whyred_usb_hw_prepare(&usb_io,2,&hw)==WHYRED_USB_HW_PHY);
    reset_model();model.dwc[0xc120/4]=0xffffffff;CHECK(whyred_usb_hw_prepare(&usb_io,2,&hw)==WHYRED_USB_HW_CORE);
    reset_model();model.dwc[GCTL/4]|=1u<<11;CHECK(whyred_usb_hw_prepare(&usb_io,2,&hw)==WHYRED_USB_HW_CORE);
    reset_model();model.dwc[0xc200/4]|=1u<<31;CHECK(whyred_usb_hw_prepare(&usb_io,2,&hw)==WHYRED_USB_HW_CORE);
    reset_model();CHECK(whyred_usb_hw_prepare(&usb_io,1,&hw)==WHYRED_USB_HW_OK);CHECK(!model.writes);
    shutdown_handoff();CHECK(whyred_usb_hw_prepare(&usb_io,1,&hw)==WHYRED_USB_HW_PHY);
    CHECK(!model.writes&&!hw.phy_wake_attempted&&hw.phy_power_before==0x23232323&&hw.phy_pll_before==0x10001000);
    shutdown_handoff();CHECK(whyred_usb_hw_prepare(&usb_io,2,&hw)==WHYRED_USB_HW_OK);
    CHECK(hw.phy_wake_attempted&&hw.phy_wake_changed&&!hw.phy_wake_restored&&model.phy_writes==1);
    CHECK(hw.phy_power==0x22222222&&hw.phy_pll==0x10001020&&model.delays==WHYRED_USB_PHY_SETTLE_US);
    shutdown_handoff();model.phy_lock_delay=750;CHECK(whyred_usb_hw_prepare(&usb_io,2,&hw)==WHYRED_USB_HW_OK);
    CHECK(hw.phy_polls==750&&model.delays==WHYRED_USB_PHY_SETTLE_US+750);
    shutdown_handoff();model.stuck_phy_pll=true;CHECK(whyred_usb_hw_prepare(&usb_io,2,&hw)==WHYRED_USB_HW_PHY_WAKE);
    CHECK(hw.phy_wake_attempted&&hw.phy_wake_restored&&!hw.phy_wake_changed&&hw.phy_polls==WHYRED_USB_PHY_POLLS);
    CHECK(hw.phy_power==0x23232323&&model.phy_writes==2&&model.maps==2&&model.delays==WHYRED_USB_PHY_SETTLE_US+WHYRED_USB_PHY_POLLS);
    shutdown_handoff();model.reject_phy_power=true;CHECK(whyred_usb_hw_prepare(&usb_io,2,&hw)==WHYRED_USB_HW_PHY_WAKE);
    CHECK(hw.phy_wake_restored&&hw.phy_power==0x23232323&&model.maps==2);
    shutdown_handoff();model.gcc[0x88018/4]=0;CHECK(whyred_usb_hw_prepare(&usb_io,2,&hw)==WHYRED_USB_HW_PHY);
    CHECK(!hw.phy_wake_attempted&&!model.phy_writes);
    const unsigned non_shutdown[]={0,1,3,0xa3,0xff};
    for(unsigned i=0;i<sizeof(non_shutdown)/sizeof(non_shutdown[0]);i++) {
        shutdown_handoff();model.phy[WHYRED_USB_PHY_POWERDOWN/4]=non_shutdown[i];
        CHECK(whyred_usb_hw_prepare(&usb_io,2,&hw)==WHYRED_USB_HW_PHY);CHECK(!hw.phy_wake_attempted&&!model.phy_writes);
    }
    const unsigned phy_resets[]={WHYRED_USB_QUSB_BCR,WHYRED_USB_AHB2PHY_BCR};
    for(unsigned i=0;i<2;i++) {
        shutdown_handoff();model.gcc[phy_resets[i]/4]=1;CHECK(whyred_usb_hw_prepare(&usb_io,2,&hw)==WHYRED_USB_HW_RESET);
        CHECK(model.maps==1&&!model.writes);
    }
    shutdown_handoff();model.gcc[whyred_usb_clocks[0]/4]=0x80200000;model.fail_map=WHYRED_USB_DWC_PA;
    CHECK(whyred_usb_hw_prepare(&usb_io,2,&hw)==WHYRED_USB_HW_MAP);
    CHECK(hw.phy_wake_restored&&hw.phy_power==0x23232323&&model.gcc[whyred_usb_clocks[0]/4]==0x80200000);
    shutdown_handoff();model.dwc[0xc120/4]=0;CHECK(whyred_usb_hw_prepare(&usb_io,2,&hw)==WHYRED_USB_HW_CORE);
    CHECK(hw.phy_wake_restored&&model.phy_writes==2);
    reset_model();CHECK(whyred_usb_hw_prepare(&usb_io,1,&hw)==WHYRED_USB_HW_OK);
    CHECK(whyred_usb_hw_select_utmi(&usb_io,&hw));CHECK(model.qs[2]==0x100049&&model.delays==10);
    reset_model();CHECK(whyred_usb_hw_prepare(&usb_io,2,&hw)==WHYRED_USB_HW_OK);model.reject_mux=true;CHECK(!whyred_usb_hw_select_utmi(&usb_io,&hw));CHECK(model.qs[2]==0x100040);
    const unsigned offsets[]={UD_TRB_OUT,UD_TRB_IN,UD_TRB_RX,UD_TRB_TX,UD_TRB_INT,UD_SETUP,UD_DATA,UD_NOTIFY,UD_RX,UD_TX};
    const unsigned sizes[]={16,16,16,16,16,8,512,16,UD_FRAME_MAX,UD_FRAME_MAX};
    for(unsigned i=0;i<10;i++){CHECK(!(offsets[i]&127)&&offsets[i]+sizes[i]<=UD_SIZE);for(unsigned j=i+1;j<10;j++){unsigned end=(offsets[i]+sizes[i]+127)&~127u;CHECK(end<=offsets[j]||offsets[j]+sizes[j]<=offsets[i]);}}
    reset_model();sweet_usb_probe();CHECK(!model.maps&&!thread_calls);
    reset_model();model.boot_mode=1;sweet_usb_probe();CHECK(!model.writes&&!thread_calls);unsigned maps=model.maps;sweet_usb_probe();CHECK(model.maps==maps);
    shutdown_handoff();start_driver();CHECK(!ud.failed&&thread_calls==2&&usb_hw.phy_wake_attempted);stop_driver();
    reset_model();start_driver();CHECK(!ud.failed&&thread_calls==2&&ud.resource[0]&&ud.state==EP0_SETUP);CHECK((dwc_rd(GCTL)&(3u<<12))==(2u<<12));
    CHECK(model.dma_clean);
    CHECK(!(dwc_rd(0xc200)&((1u<<6)|(1u<<8)))&&(dwc_rd(DCTL)&DCTL_RUN_STOP));
    setup(0x80,6,0x100,0,65535);CHECK(model.dma[UD_DATA]==18&&model.dma[UD_DATA+1]==1);
    setup(0x80,6,0x200,0,80);CHECK(model.dma[UD_DATA]==9&&model.dma[UD_DATA+2]==80);
    setup(0x80,6,0x600,0,10);CHECK(model.dma[UD_DATA]==10&&model.dma[UD_DATA+1]==6);
    setup(0x80,6,0x700,0,80);CHECK(model.dma[UD_DATA+1]==7);
    unsigned stalls=setup_stalls;setup(0x21,0x99,0,0,0);CHECK(setup_stalls==stalls+1&&!ud.failed);
    for(unsigned req=12;req<256;req++){stalls=setup_stalls;setup(0,req,0xffff,0xffff,0xffff);CHECK(setup_stalls==stalls+1&&!ud.failed);}
    setup(0,5,127,0,0);CHECK((dwc_rd(DCFG)&(0x7fu<<3))==(127u<<3));
    setup(0,9,1,0,0);CHECK(ud.configured&&!ud.data_alt&&!ud.resource[EP_RX]);
    CHECK(ud_if_output(ud.ifp,packet(60,1))==0&&!mbufs);
    setup(1,11,1,1,0);CHECK(ud.data_alt==1&&ud.resource[EP_RX]&&ud.resource[EP_INT]&&links_up==1);
    CHECK(!ud_link_ready());setup(0x21,0x43,12,0,0);CHECK(ud_link_ready());
    ud_if_output(ud.ifp,packet(512,0xab));CHECK(ud.tx_busy&&ud.resource[EP_TX]);CHECK(((uint32_t *)(model.dma+UD_TRB_TX))[2]==513&&model.dma[UD_TX+512]==0);complete(EP_TX,0);
    memset(model.dma+UD_RX,0x11,60);complete(EP_RX,UD_FRAME_MAX-60);CHECK(received==1&&ud.resource[EP_RX]&&!mbufs);
    ud_if_output(ud.ifp,packet(60,0xa5));ud_if_output(ud.ifp,packet(60,0x5a));CHECK(mbufs==1);
    ud_event(1u);CHECK(!ud.configured&&!ud.data_alt&&!ud.tx_busy&&!mbufs&&model.ends>=2&&links_down>0);
    ready();CHECK(ud_link_ready());setup(1,11,0,1,0);CHECK(ud.configured&&!ud.data_alt&&!ud.packet_filter&&!ud.resource[EP_RX]);
    setup(1,11,1,1,0);setup(0x21,0x43,12,0,0);CHECK(ud_link_ready());
    ud_event(1u);model.dwc[DSTS/4]=1;ud_event((2u<<8)|1u);CHECK(ud.max_packet==64);
    setup(0x80,6,0x200,0,80);for(unsigned at=0;at<80;at+=model.dma[UD_DATA+at])if(model.dma[UD_DATA+at+1]==5&&model.dma[UD_DATA+at+3]==2)CHECK(model.dma[UD_DATA+at+4]==64&&model.dma[UD_DATA+at+5]==0);
    ready();ud_if_output(ud.ifp,packet(64,0xab));CHECK(((uint32_t *)(model.dma+UD_TRB_TX))[2]==65);complete(EP_TX,0);stop_driver();
    reset_model();start_driver();ready();ud_if_output(ud.ifp,packet(60,0xa5));ud_if_output(ud.ifp,packet(60,0x5a));
    ud_event((EP_TX<<1)|(1u<<6));CHECK(ud.failed&&model.dma[UD_TX]==0xa5);stop_driver();
    reset_model();start_driver();ready();complete(EP_RX,UD_FRAME_MAX+1);CHECK(ud.failed&&!received);stop_driver();
    reset_model();start_driver();ready();complete(EP_RX,2u<<28);CHECK(ud.failed&&!received);stop_driver();
    reset_model();start_driver();ready();ud_event((EP_RX<<1)|(1u<<6)|(1u<<12));CHECK(ud.failed&&!received);stop_driver();
    reset_model();start_driver();uint8_t *pending=model.dma+UD_SETUP;pending[0]=0x80;pending[1]=6;pending[3]=1;pending[6]=18;
    complete(0,0);CHECK(ud.state==EP0_DATA&&ud.resource[1]);ud_event(1u);
    CHECK(!ud.failed&&ud.state==EP0_SETUP&&ud.resource[0]&&!ud.resource[1]);stop_driver();
    reset_model();model.stuck_command=true;start_driver();CHECK(ud.failed&&model.delays>=1000&&!(dwc_rd(DCTL)&DCTL_RUN_STOP));stop_driver();
    reset_model();model.command_error=true;start_driver();CHECK(ud.failed);stop_driver();
    reset_model();model.missing_resource=true;start_driver();CHECK(!ud.failed&&ud.active[0]);
    ready();CHECK(ud.failed);stop_driver();
    reset_model();model.zero_control_resource=true;start_driver();
    CHECK(!ud.failed&&ud.active[0]&&!ud.resource[0]&&thread_calls==2);
    CHECK(((uint32_t *)(model.dma+UD_TRB_OUT))[3]&TRB_HWO);
    setup(0x80,6,0x100,0,18);CHECK(!ud.failed&&ud.active[0]&&!ud.resource[0]);
    ready();CHECK(ud_link_ready()&&ud.active[EP_RX]&&ud.resource[EP_RX]);
    ud_if_output(ud.ifp,packet(60,0x51));CHECK(ud.active[EP_TX]);complete(EP_TX,0);
    CHECK(!ud.active[EP_TX]&&!ud.resource[EP_TX]&&!ud.tx_busy);stop_driver();
    reset_model();model.zero_control_resource=true;start_driver();
    unsigned starts_before=model.starts;((uint32_t *)(model.dma+UD_TRB_OUT))[3]&=~TRB_HWO;
    CHECK(ud_start(0,UD_SETUP,8,TRBCTL_SETUP)==-1&&ud.failed&&model.starts==starts_before);stop_driver();
    reset_model();model.zero_control_resource=true;start_driver();
    uint8_t *control=model.dma+UD_SETUP;control[0]=0x80;control[1]=6;control[3]=1;control[6]=18;
    complete(0,0);CHECK(ud.state==EP0_DATA&&ud.active[1]&&!ud.resource[1]);
    ud_event((1u<<8)|1u);CHECK(ud.failed&&(((uint32_t *)(model.dma+UD_TRB_IN))[3]&TRB_HWO));stop_driver();
    reset_model();model.delayed_index=8;start_driver();CHECK(!ud.failed&&ud.resource[0]==1&&ud.active[0]);stop_driver();
    reset_model();model.late_result_error=true;start_driver();CHECK(ud.failed&&!thread_calls);stop_driver();
    reset_model();model.result_reactivates=true;start_driver();CHECK(ud.failed&&!thread_calls&&model.delays<2000);stop_driver();
    reset_model();model.stuck_stop=true;start_driver();CHECK(ud.failed&&model.starts==0&&model.delays==500010);
    reset_model();model.stuck_reset=true;start_driver();CHECK(ud.failed&&model.starts==0);stop_driver();
    reset_model();model.stuck_run=true;start_driver();CHECK(ud.failed);stop_driver();
    reset_model();model.fail_thread=true;start_driver();CHECK(ud.failed);stop_driver();
    reset_model();model.fail_dma=true;start_driver();CHECK(ud.failed&&!model.starts&&!thread_calls);
    reset_model();model.physical_page=0x100000000ULL>>14;start_driver();CHECK(ud.failed&&!model.starts&&!thread_calls);
    reset_model();model.fail_ifnet=true;start_driver();CHECK(ud.failed&&!model.starts&&!thread_calls);
    reset_model();model.log_enabled=false;start_driver();CHECK(!ud.failed&&thread_calls==1);stop_driver();
    reset_model();start_driver();ready();model.dwc[GEVNTCOUNT/4]=UD_EVT_SIZE+4;ud_thread(NULL,0);CHECK(ud.failed);stop_driver();
    reset_model();start_driver();ready();model.dwc[GEVNTCOUNT/4]=3;ud_thread(NULL,0);CHECK(ud.failed);stop_driver();
    reset_model();start_driver();ready();ud_event((11u<<8)|1u);CHECK(ud.failed);stop_driver();
    reset_model();start_driver();ready();const char message[]="whyred UART bytes\n";sweet_log_append(message,(int)sizeof(message)-1);
    send_failures=1;sleep_limit=3;if(!setjmp(thread_exit))ud_log_thread(NULL,0);
    CHECK(sends==2&&sent_lengths[0]==sizeof(message)-1&&sent_lengths[1]==sizeof(message)-1);
    CHECK(!memcmp(first_send,message,sizeof(message)-1)&&!memcmp(second_send,message,sizeof(message)-1));stop_driver();
    reset_model();start_driver();ready();static char long_log[80000];memset(long_log,0x31,sizeof(long_log));sweet_log_append(long_log,sizeof(long_log));
    sleep_limit=1;if(!setjmp(thread_exit))ud_log_thread(NULL,0);CHECK(sends==8);stop_driver();
    reset_model();model.boot_mode=0;sweet_usb_probe();CHECK(!model.snapshot_lines&&!ud.snapshot_reports&&!model.maps);
    reset_model();start_driver();CHECK(ud.snapshot_reports==2&&model.snapshot_lines==8);
    unsigned old_writes=model.writes,old_dwc_writes=model.dwc_writes,old_commands=model.commands;
    model.dwc[GEVNTCOUNT/4]=0x80000004;model.phy[0xc0/4]=0x15151515;model.phy[0xc4/4]=0xc0c0c0c0;
    unsigned old_reads=model.reads+model.dwc_reads;
    ud_snapshot(2);CHECK(ud.snapshot_reports==3&&model.snapshot_lines==12);
    CHECK(model.reads+model.dwc_reads==old_reads+33);
    CHECK(model.writes==old_writes&&model.dwc_writes==old_dwc_writes&&model.commands==old_commands);
    CHECK(model.dwc[GEVNTCOUNT/4]==0x80000004); /* No event ACK during diagnosis. */
    CHECK(strstr(snapshot_output[0],"snapshot=3 stage=2")!=NULL);
    CHECK(strstr(snapshot_output[1],"COUNT=80000004")!=NULL);
    CHECK(strstr(snapshot_output[2],"UTMI1=15151515 UTMI2=c0c0c0c0")!=NULL);
    CHECK(strstr(snapshot_output[3],"BUSERR=")!=NULL);
    ud_snapshot(2);CHECK(ud.snapshot_reports==3&&model.snapshot_lines==12);
    model.dwc[DSTS/4]^=1u<<3;ud_snapshot(2);CHECK(ud.snapshot_reports==3); /* SOF frame only. */
    model.dwc[DSTS/4]^=1u<<18;ud_snapshot(2);CHECK(ud.snapshot_reports==4);
    model.phy[0xf4/4]=1;ud_snapshot(2);CHECK(ud.snapshot_reports==5);
    CHECK(strstr(snapshot_output[2],"LINE=00000001")!=NULL);
    model.dwc[0xc130/4]=0xa4f3c000;ud_snapshot(2);CHECK(ud.snapshot_reports==6);
    CHECK(strstr(snapshot_output[3],"BUSERR=a4f3c000/")!=NULL);
    for(unsigned i=0;i<80;i++){model.phy[0xc4/4]^=1u<<6;ud_snapshot(2);}
    CHECK(ud.snapshot_reports==32&&model.snapshot_lines==128);
    old_reads=model.reads+model.dwc_reads;
    for(unsigned i=0;i<1000;i++){model.phy[0xf4/4]^=1;ud_snapshot(i%3);}
    CHECK(ud.snapshot_reports==32&&model.snapshot_lines==128);
    CHECK(model.reads+model.dwc_reads==old_reads); /* Exhausted budget avoids even MMIO reads. */
    CHECK(model.writes==old_writes&&model.dwc_writes==old_dwc_writes&&model.commands==old_commands);
    stop_driver();
    reset_model();start_driver();sleep_limit=2500;
    if(!setjmp(thread_exit))ud_thread(NULL,0);
    CHECK(!ud.failed&&model.deadlines==3&&model.now==2501000000ULL);
    CHECK(ud.snapshot_reports==3&&model.snapshot_lines==12); /* 1Hz reads, no stable-state log flood. */
    stop_driver();
    CHECK(!mbufs&&!held);printf("PASS: %u actual USB board/core checks (modeled MMIO/kernel services)\n",checks);return 0;
}
