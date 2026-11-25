/* Deterministic register/card model for the actual extracted driver functions.
 * This exercises ordering, bounds and recovery; it is not a SDCC timing model. */
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include "kernel-defines.h"

void *memset(void *p, int c, size_t n) { unsigned char *b=p; while(n--) *b++=(unsigned char)c; return p; }
void *memcpy(void *p, const void *q, size_t n) { unsigned char *d=p; const unsigned char *s=q; while(n--) *d++=*s++; return p; }
int memcmp(const void *p,const void *q,size_t n) { const unsigned char *a=p,*b=q; while(n--) { if(*a!=*b) return *a-*b; a++;b++; } return 0; }
int strcmp(const char *p,const char *q) { while(*p && *p==*q) {p++;q++;}return (unsigned char)*p-(unsigned char)*q; }
static void test_log(const char *s,...) {(void)s;}
#define printf test_log
#define __unused __attribute__((unused))
#define EIO 5
#define EINVAL 22
#define ENXIO 6
#define EROFS 30
#define B_READ 1
typedef uintptr_t vm_offset_t;
typedef uint32_t dev_t;
typedef char *caddr_t;
#define minor(x) ((x)&0xffffffU)
struct whyred_gpt_io {volatile uint8_t *base;uint32_t sectors;};
struct whyred_gpt_partition {uint64_t first,last;uint8_t guid[16];uint32_t index;char name[37];};
static struct whyred_gpt_partition whyred_gpt_parts[256];
static uint32_t whyred_gpt_part_count,whyred_emmc_sector_count;
static struct whyred_gpt_io whyred_emmc_live_io;
static int whyred_emmc_lock;
struct test_buf {uint32_t count,flags,resid;int64_t blkno;dev_t device;uint8_t *data;int error,done;};
typedef struct test_buf *buf_t;
#define buf_count(p) ((p)->count)
#define buf_flags(p) ((p)->flags)
#define buf_device(p) ((p)->device)
#define buf_blkno(p) ((p)->blkno)
#define buf_setresid(p,x) ((p)->resid=(x))
#define buf_seterror(p,x) ((p)->error=(x))
#define buf_biodone(p) ((p)->done++)
static int buf_map(buf_t b,caddr_t *p){*p=(caddr_t)b->data;return 0;}
static void buf_unmap(buf_t b){(void)b;}
static void lck_mtx_lock(int *p){(void)p;}
static void lck_mtx_unlock(int *p){(void)p;}

static uint8_t host_bytes[4096],gcc_bytes[4096];
static uint32_t status,response,active_lba,active_count,active_word,card_count;
static uint32_t commands[64],bad_commands,mmio_writes;
static uint64_t timer;
/* A device completion arriving while the polling CPU is descheduled. */
static int late_response,late_armed,late_counter;
static uint32_t late_status;
static int late_ready_mode,late_ready_hidden,late_ready_counter;
static uint64_t test_frequency=19200000;
static int fail_cmd23,fail_cmd18,fail_data,fail_single,missing_end,early_end,corrupt_xo;
static int end_delay,end_delay_left,active_cmd;
static int fail_update,update_writes,clock_delay,card_delay,stuck_card;
static int fault_reset,map_failed,boot_fast,boot_multi,boot_perf;
static int stop_timeouts,status_timeouts,command_latched,status_illegal_once;
static uint32_t card_status=0x900, status_present_fault, status_fifo_fault;
static uint32_t command_register,cfg_register=0x2613;
static uint16_t clock_register=0xc0c7;
static uint32_t test_checks;
static uint8_t guarded[64+65536+64];

static uint64_t whyred_emmc_counter(void){
    timer+=1000;
    if(late_counter){timer+=200000;status=late_status;late_counter=0;}
    if(late_ready_counter){
        timer+=200000;late_ready_counter=0;
        if(late_ready_mode!=3)late_ready_hidden=0;
        if(late_ready_mode==2)status|=0x00208000U;
    }
    return timer;
}
static uint64_t whyred_emmc_timeout_ticks(void){return 100000;}
static void whyred_emmc_delay_us(uint32_t n){timer+=n*20+1;}
static uint32_t pattern_word(uint32_t lba,uint32_t word){return 0x91827364U^(lba*0x1020305U)^(word*0x03030303U);}
static uint16_t whyred_emmc_read16(volatile uint8_t *b,unsigned o)
{
    if(o==SDHCI_CLOCK_CONTROL){
        uint16_t v=clock_register;
        if(clock_delay>0){clock_delay--;v&=(uint16_t)~SDHCI_CLOCK_INT_STABLE;}
        if(card_delay>0){card_delay--;v&=(uint16_t)~SDHCI_CLOCK_CARD_ENABLE;}
        return v;
    }
    return (uint16_t)b[o]|((uint16_t)b[o+1]<<8);
}
static uint8_t whyred_emmc_read8(volatile uint8_t *b,unsigned o){return b[o];}
static uint32_t whyred_emmc_read32(volatile uint8_t *b,unsigned o)
{
    if(b==gcc_bytes){
        if(o==0x2c)return command_register;
        if(o==0x30)return cfg_register;
        if(o==0x04||o==0x08)return gcc_bytes[o];
    }
    if(b==host_bytes){
        if(o==SDHCI_INT_STATUS){if(late_armed){late_armed=0;late_counter=1;return 0;}return status;}
        if(o==SDHCI_RESPONSE)return response;
        if(o==SDHCI_PRESENT_STATE){
            if(commands[13] && status_present_fault)return status_present_fault;
            if(command_latched)return SDHCI_PSTATE_CMD_INHIBIT;
            if(active_count&&late_ready_hidden){late_ready_counter=1;return 0;}
            if(active_count)return SDHCI_PSTATE_DATA_AVAILABLE;
            if(end_delay_left>0){end_delay_left--;return 3;}
            return 0;
        }
        if(o==SDHCI_CORE_MCI_FIFO_COUNT)return commands[13] && status_fifo_fault?status_fifo_fault:(active_count?512U:0);
        if(o==SDHCI_BUFFER){
            uint32_t v=pattern_word(active_lba,active_word);
            if(corrupt_xo&&(cfg_register&0x371fU)==1)v^=0x80000000U;
            active_word++;
            if(fail_data&&commands[18]&&active_word==16){status|=0x00208000U;fail_data=0;}
            if(fail_single&&active_cmd==17&&active_word==16){status|=0x00208000U;fail_single--;}
            if(active_word==128){
                active_word=0;active_lba++;active_count--;
                host_bytes[SDHCI_BLOCK_COUNT]=(uint8_t)active_count;
                host_bytes[SDHCI_BLOCK_COUNT+1]=0;
                if(early_end&&active_count){active_count=0;status=SDHCI_INT_DATA_END;early_end=0;}
                else if(active_count)status|=SDHCI_INT_DATA_AVAILABLE;
                else if(!missing_end){status|=SDHCI_INT_DATA_END;end_delay_left=end_delay;}
            }
            return v;
        }
    }
    return (uint32_t)b[o]|((uint32_t)b[o+1]<<8)|((uint32_t)b[o+2]<<16)|((uint32_t)b[o+3]<<24);
}
static void whyred_emmc_write32(volatile uint8_t *b,unsigned o,uint32_t v)
{
    mmio_writes++;
    if(b==gcc_bytes){
        if(o==0x30){cfg_register=v;return;}
        if(o==0x2c){update_writes++;command_register=(fail_update==2||(fail_update==1&&update_writes==1))?v:(v&~1U);return;}
        bad_commands++;return; /* No PLL, branch-enable or other GCC write allowed. */
    }
    if(o==SDHCI_INT_STATUS){
        status&=~v;
        if(v==SDHCI_INT_RESPONSE&&active_cmd==17&&late_ready_mode)late_ready_hidden=1;
        return;
    }
    for(unsigned n=0;n<4;n++)b[o+n]=(uint8_t)(v>>(n*8));
}
static void whyred_emmc_write16(volatile uint8_t *b,unsigned o,uint16_t v)
{
    mmio_writes++;
    if(o==SDHCI_CLOCK_CONTROL){
        if(stuck_card&&v==0){clock_register|=4;return;}
        clock_register=v;
        if(v&SDHCI_CLOCK_INT_ENABLE)clock_register|=SDHCI_CLOCK_INT_STABLE;
        return;
    }
    b[o]=(uint8_t)v;b[o+1]=(uint8_t)(v>>8);
    if(o==SDHCI_COMMAND){
        unsigned cmd=v>>8;commands[cmd]++;response=0x900;status|=SDHCI_INT_RESPONSE;
        if(cmd==23){card_count=whyred_emmc_read32(b,SDHCI_ARGUMENT);if(fail_cmd23)response=0x00400000;}
        else if(cmd==17||cmd==18){
            if(cmd==18&&fail_cmd18){status=0x00018000;return;}
            active_cmd=(int)cmd;active_lba=whyred_emmc_read32(b,SDHCI_ARGUMENT);active_word=0;
            active_count=cmd==17?1:card_count;
            if(cmd==18&&(whyred_emmc_read16(b,SDHCI_TRANSFER_MODE)!=0x32||
                active_count!=whyred_emmc_read16(b,SDHCI_BLOCK_COUNT)))bad_commands++;
            status|=SDHCI_INT_DATA_AVAILABLE;
            if(late_response){late_status=status|(late_response==2?0x00018000U:0);status=0;late_armed=1;late_response=0;}
        }else if(cmd==12){
            active_count=0;
            if(stop_timeouts){stop_timeouts--;status=0x00018000;command_latched=1;return;}
            status|=SDHCI_INT_DATA_END;
        }else if(cmd==13){
            if(status_illegal_once){status_illegal_once--;response=0x00400900;return;}
            if(status_timeouts){status_timeouts--;status=0x00018000;command_latched=1;return;}
            response=card_status;
        }else bad_commands++;
    }
}
static void whyred_emmc_write8(volatile uint8_t *b,unsigned o,uint8_t v)
{
    mmio_writes++;
    if(o==SDHCI_SOFTWARE_RESET){
        if(v&~0x06U)bad_commands++;
        if(fault_reset){b[o]=v;return;}
        if(v&0x02)command_latched=0;
        b[o]=0;status=0;active_count=0;end_delay_left=0;return;
    }
    b[o]=v;
}
static vm_offset_t ml_io_map(vm_offset_t p,unsigned n){
    if(p!=0x116000ULL||n!=4096){bad_commands++;return 0;}
    return map_failed?0:(vm_offset_t)gcc_bytes;
}
static int PE_parse_boot_argn(const char *name,void *out,size_t n)
{
    int v;
    if(!strcmp(name,"whyred-emmc-partition")){const char *s="system";if(n<7)return 0;memcpy(out,s,7);return 1;}
    if(!strcmp(name,"whyred-emmc-fast"))v=boot_fast;
    else if(!strcmp(name,"whyred-emmc-multi"))v=boot_multi;
    else if(!strcmp(name,"whyred-emmc-perf"))v=boot_perf;
    else return 0;
    if(n!=4)return 0;*(uint32_t *)out=(uint32_t)v;return 1;
}

#include "kernel-fragment.h"
#include "whyred_boot_log.h"

#define CHECK(x) do{test_checks++;if(!(x))return __LINE__;}while(0)
static void reset_model(void)
{
    memset(host_bytes,0,sizeof(host_bytes));memset(gcc_bytes,0,sizeof(gcc_bytes));
    memset(commands,0,sizeof(commands));memset(&whyred_emmc_perf,0,sizeof(whyred_emmc_perf));
    memset(guarded,0xa5,sizeof(guarded));memset(whyred_gpt_parts,0,sizeof(whyred_gpt_parts));
    status=response=active_lba=active_count=active_word=card_count=bad_commands=mmio_writes=0;
    timer=0;late_response=late_armed=late_counter=0;late_status=0;
    late_ready_mode=late_ready_hidden=late_ready_counter=0;fail_cmd23=fail_cmd18=fail_data=fail_single=missing_end=early_end=corrupt_xo=0;
    active_cmd=end_delay=end_delay_left=0;
    fail_update=update_writes=clock_delay=card_delay=stuck_card=fault_reset=map_failed=0;
    stop_timeouts=status_timeouts=command_latched=status_illegal_once=0;card_status=0x900;status_present_fault=status_fifo_fault=0;
    boot_fast=boot_multi=boot_perf=0;
    command_register=0;cfg_register=0x2613;clock_register=0xc0c7;
    gcc_bytes[0x04]=gcc_bytes[0x08]=1;
    whyred_emmc_gcc=gcc_bytes;whyred_emmc_fast_requested=whyred_emmc_multi_requested=false;
    whyred_emmc_multi_enabled=whyred_emmc_xo_active=whyred_emmc_perf_enabled=false;
    whyred_emmc_transport_ok=true;
    whyred_emmc_live_io.base=host_bytes;whyred_emmc_live_io.sectors=4096;
    whyred_emmc_sector_count=4096;whyred_gpt_part_count=1;
    whyred_gpt_parts[0].first=64;whyred_gpt_parts[0].last=2047;whyred_gpt_parts[0].index=61;
    memcpy(whyred_gpt_parts[0].name,"system",7);
}
static int data_ok(const uint8_t *data,uint32_t lba,uint32_t count)
{
    for(uint32_t n=0;n<count;n++)for(uint32_t w=0;w<128;w++){
        uint32_t v=pattern_word(lba+n,w),p=n*512+w*4;
        for(unsigned b=0;b<4;b++)if(data[p+b]!=(uint8_t)(v>>(b*8)))return 0;
    }
    return 1;
}
static int guards_ok(unsigned bytes)
{
    for(unsigned i=0;i<64;i++)if(guarded[i]!=0xa5)return 0;
    for(unsigned i=64+bytes;i<sizeof(guarded);i++)if(guarded[i]!=0xa5)return 0;
    return 1;
}

#ifdef _WIN32
__declspec(dllexport)
#endif
int whyred_perf_late_poll_checks(void)
{
    reset_model();uint32_t observed=0;uint64_t start=whyred_emmc_counter();
    late_armed=1;late_status=SDHCI_INT_RESPONSE|SDHCI_INT_DATA_AVAILABLE;
    CHECK(whyred_emmc_wait_status(host_bytes,SDHCI_INT_RESPONSE,start,100000,&observed)==0);
    CHECK(observed==0x21U&&timer-start>=100000&&mmio_writes==0);
    /* FIFO becomes ready after an empty sample, while the polling CPU loses
     * longer than its timeout. A final ready/error sample distinguishes this
     * from a real timeout without issuing recovery or accepting partial data. */
    reset_model();late_ready_mode=1;
    CHECK(whyred_emmc_read_sector(&whyred_emmc_live_io,67,guarded+64)==0);
    CHECK(data_ok(guarded+64,67,1)&&guards_ok(512)&&commands[17]==1);
    CHECK(commands[12]==0&&commands[13]==0&&active_count==0&&status==0);
    reset_model();late_ready_mode=2;
    CHECK(whyred_emmc_read_sector(&whyred_emmc_live_io,67,guarded+64)!=0);
    CHECK(guards_ok(0)&&active_count==1&&commands[17]==1); /* late CRC error is not data */
    reset_model();late_ready_mode=3;
    CHECK(whyred_emmc_read_sector(&whyred_emmc_live_io,67,guarded+64)!=0);
    CHECK(guards_ok(0)&&active_count==1&&commands[17]==1); /* FIFO still unavailable */
    reset_model();late_response=1;
    CHECK(whyred_emmc_read_sector(&whyred_emmc_live_io,67,guarded+64)==0);
    CHECK(data_ok(guarded+64,67,1)&&guards_ok(512)&&commands[17]==1);
    reset_model();late_response=2;
    CHECK(whyred_emmc_read_sector(&whyred_emmc_live_io,67,guarded+64)!=0);
    CHECK(guards_ok(0)&&commands[17]==1); /* a late hardware error is never data */
    reset_model();start=whyred_emmc_counter();late_armed=1;late_status=SDHCI_INT_DATA_END;
    CHECK(whyred_emmc_wait_status(host_bytes,SDHCI_INT_DATA_END,start,100000,&observed)==0);
    CHECK(observed==SDHCI_INT_DATA_END&&mmio_writes==0);
    reset_model();start=whyred_emmc_counter();late_armed=1;late_status=0x00018000;
    CHECK(whyred_emmc_wait_status(host_bytes,SDHCI_INT_RESPONSE,start,100000,&observed)==0);
    CHECK((observed&SDHCI_INT_ERROR_MASK)!=0); /* caller still rejects hardware errors */
    reset_model();start=whyred_emmc_counter();late_armed=1;late_status=0;
    CHECK(whyred_emmc_wait_status(host_bytes,SDHCI_INT_RESPONSE,start,100000,&observed)!=0);
    CHECK(observed==0&&mmio_writes==0&&timer-start<=202000);
    return 0;
}
#ifdef _WIN32
__declspec(dllexport)
#endif
int whyred_perf_baseline_retry_checks(void)
{
    reset_model();fail_single=1;
    CHECK(whyred_emmc_read_blocks(&whyred_emmc_live_io,67,1,guarded+64)==0);
    CHECK(data_ok(guarded+64,67,1)&&guards_ok(512)&&whyred_emmc_transport_ok);
    CHECK(commands[17]==2&&commands[12]==1&&commands[13]==1&&update_writes==0);
    CHECK(!whyred_emmc_xo_active&&clock_register==0xc0c7&&cfg_register==0x2613);
    CHECK(whyred_emmc_perf.errors==1&&whyred_emmc_perf.fallbacks==1);
    reset_model();CHECK(whyred_emmc_try_xo(host_bytes)==1);
    whyred_emmc_multi_enabled=true;fail_data=1;fail_single=1;
    CHECK(whyred_emmc_read_blocks(&whyred_emmc_live_io,67,8,guarded+64)==0);
    CHECK(data_ok(guarded+64,67,8)&&guards_ok(4096)&&whyred_emmc_transport_ok);
    CHECK(commands[18]==1&&commands[17]==9&&commands[12]==2&&commands[13]==2);
    CHECK(whyred_emmc_perf.errors==2&&whyred_emmc_perf.fallbacks==2);
    reset_model();fail_single=2;
    struct test_buf failed={.count=512,.flags=B_READ,.blkno=3,.device=61,.data=guarded+64};
    whyred_emmc_strategy(&failed);
    CHECK(failed.done==1&&failed.error==EIO&&failed.resid==512&&!whyred_emmc_transport_ok);
    CHECK(commands[17]==2&&commands[12]==1&&commands[13]==1&&guards_ok(512));
    reset_model();fail_single=1;fault_reset=1;
    CHECK(whyred_emmc_read_blocks(&whyred_emmc_live_io,67,1,guarded+64)!=0);
    CHECK(!whyred_emmc_transport_ok);uint32_t old=mmio_writes;
    CHECK(whyred_emmc_read_blocks(&whyred_emmc_live_io,67,1,guarded+64)!=0&&mmio_writes==old);
    return 0;
}
#ifdef _WIN32
__declspec(dllexport)
#endif
int whyred_perf_stop_timeout_checks(void)
{
    reset_model();fail_single=1;stop_timeouts=1;
    CHECK(whyred_emmc_read_blocks(&whyred_emmc_live_io,67,1,guarded+64)==0);
    CHECK(data_ok(guarded+64,67,1)&&guards_ok(512)&&whyred_emmc_transport_ok);
    CHECK(commands[12]==1&&commands[13]==1&&commands[17]==2&&!command_latched);
    CHECK(bad_commands==0&&update_writes==0&&clock_register==0xc0c7);
    reset_model();CHECK(whyred_emmc_try_xo(host_bytes)==1);
    whyred_emmc_multi_enabled=true;fail_data=1;fail_single=1;stop_timeouts=2;
    CHECK(whyred_emmc_read_blocks(&whyred_emmc_live_io,67,8,guarded+64)==0);
    CHECK(data_ok(guarded+64,67,8)&&guards_ok(4096)&&whyred_emmc_transport_ok);
    CHECK(commands[12]==2&&commands[13]==2&&commands[17]==9&&!command_latched);
    reset_model();fail_single=1;stop_timeouts=1;status_timeouts=1;
    CHECK(whyred_emmc_read_blocks(&whyred_emmc_live_io,67,1,guarded+64)==0);
    CHECK(data_ok(guarded+64,67,1)&&commands[12]==2&&commands[13]==2&&!command_latched);
    reset_model();fail_single=1;stop_timeouts=1;status_illegal_once=1;
    CHECK(whyred_emmc_read_blocks(&whyred_emmc_live_io,67,1,guarded+64)==0);
    CHECK(data_ok(guarded+64,67,1)&&guards_ok(512)&&whyred_emmc_transport_ok);
    CHECK(commands[12]==1&&commands[13]==2&&commands[17]==2&&!command_latched);
    reset_model();fail_single=1;stop_timeouts=1;status_illegal_once=1;status_timeouts=1;
    CHECK(whyred_emmc_read_blocks(&whyred_emmc_live_io,67,1,guarded+64)==0);
    CHECK(data_ok(guarded+64,67,1)&&guards_ok(512)&&whyred_emmc_transport_ok);
    CHECK(commands[12]==2&&commands[13]==3&&commands[17]==2&&!command_latched);
    for(unsigned mode=0;mode<11;mode++) {
        reset_model();fail_single=1;stop_timeouts=1;
        if(mode==0)card_status=0x800; /* TRAN but not READY */
        if(mode==1)card_status=0xb00; /* READY but DATA state */
        if(mode==2)card_status=0x00400900; /* R1 card error */
        if(mode==3)status_timeouts=2;
        if(mode==4)card_status=0x00400800; /* illegal command, not READY */
        if(mode==5)card_status=0x00400b00; /* illegal command, DATA state */
        if(mode==6)card_status=0x00800900; /* distinct persistent R1 error */
        if(mode==7){status_illegal_once=1;status_present_fault=SDHCI_PSTATE_CMD_INHIBIT;}
        if(mode==8){status_illegal_once=1;status_present_fault=SDHCI_PSTATE_DATA_AVAILABLE;}
        if(mode==9){status_illegal_once=1;status_fifo_fault=4;}
        if(mode==10){status_illegal_once=1;fail_single=2;} /* fresh reread also fails */
        struct test_buf b={.count=512,.flags=B_READ,.blkno=3,.device=61,.data=guarded+64};
        whyred_emmc_strategy(&b);
        CHECK(b.error==EIO&&b.resid==512&&b.done==1&&!whyred_emmc_transport_ok);
        if(mode==7)CHECK(commands[17]==1&&commands[12]==2&&commands[13]==1&&guards_ok(512));
        else if(mode==10)CHECK(commands[17]==2&&commands[12]==1&&commands[13]==2&&guards_ok(512));
        else CHECK(commands[17]==1&&commands[12]==2&&commands[13]==((mode==2||mode==9)?3U:2U)&&guards_ok(512));
        uint32_t old=mmio_writes;
        CHECK(whyred_emmc_read_blocks(&whyred_emmc_live_io,67,1,guarded+64)!=0&&mmio_writes==old);
    }
    return 0;
}
#ifdef _WIN32
__declspec(dllexport)
#endif
int whyred_perf_host_checks(void)
{
    test_checks=0;
    CHECK(whyred_perf_late_poll_checks()==0);
    CHECK(whyred_perf_baseline_retry_checks()==0);
    CHECK(whyred_perf_stop_timeout_checks()==0);
    reset_model();
    CHECK(whyred_emmc_ticks_us(19200000,19200000)==1000000);
    CHECK(whyred_emmc_ticks_us(19200001,19200000)==1000000);
    CHECK(whyred_emmc_ticks_us(1,0)==0);
    CHECK(whyred_emmc_ticks_us(19200000ULL*86400,19200000)==86400000000ULL);
    for(uint32_t count=0;count<=33;count++){
        reset_model();
        int result=whyred_emmc_read_multi(&whyred_emmc_live_io,67,count,guarded+64);
        if(count>=2&&count<=32){
            CHECK(result==0);CHECK(data_ok(guarded+64,67,count));CHECK(guards_ok(count*512));
            CHECK(commands[23]==1&&commands[18]==1&&commands[17]==0&&bad_commands==0);
            CHECK(whyred_emmc_read16(host_bytes,SDHCI_BLOCK_SIZE)==0);
            CHECK(whyred_emmc_read16(host_bytes,SDHCI_TRANSFER_MODE)==0);
        }else{CHECK(result!=0);CHECK(mmio_writes==0);CHECK(guards_ok(0));}
    }
    reset_model();
    CHECK(whyred_emmc_read_multi(&whyred_emmc_live_io,4095,2,guarded+64)!=0);
    CHECK(whyred_emmc_read_multi(&whyred_emmc_live_io,UINT32_MAX,2,guarded+64)!=0);
    CHECK(whyred_emmc_read_multi(&whyred_emmc_live_io,2,2,NULL)!=0);
    CHECK(mmio_writes==0);
    for(int failure=0;failure<5;failure++){
        reset_model();
        if(failure==0)fail_cmd23=1;if(failure==1)fail_cmd18=1;
        if(failure==2)fail_data=1;if(failure==3)missing_end=1;if(failure==4)early_end=1;
        CHECK(whyred_emmc_read_multi(&whyred_emmc_live_io,67,8,guarded+64)!=0);
        CHECK(guards_ok(8*512));CHECK(bad_commands==0);
    }
    reset_model();clock_delay=3;card_delay=3;
    CHECK(whyred_emmc_try_xo(host_bytes)==1);
    CHECK((cfg_register&0x371f)==1&&whyred_emmc_xo_active&&clock_register==7);
    CHECK(whyred_emmc_restore_clock(host_bytes)==0);
    CHECK(cfg_register==0x2613&&clock_register==0xc0c7&&!whyred_emmc_xo_active&&bad_commands==0);
    reset_model();gcc_bytes[0x04]=0;
    CHECK(whyred_emmc_try_xo(host_bytes)==0&&mmio_writes==0);
    reset_model();map_failed=1;boot_fast=1;whyred_emmc_perf_configure(host_bytes);
    CHECK(whyred_emmc_gcc==NULL&&whyred_emmc_try_xo(host_bytes)==0);
    reset_model();fail_update=1;
    CHECK(whyred_emmc_try_xo(host_bytes)==0&&cfg_register==0x2613&&clock_register==0xc0c7);
    reset_model();fail_update=2;
    CHECK(whyred_emmc_try_xo(host_bytes)<0&&!whyred_emmc_xo_active);
    reset_model();boot_fast=boot_multi=1;whyred_emmc_perf_configure(host_bytes);
    CHECK(whyred_emmc_perf_prepare(&whyred_emmc_live_io)==0);
    CHECK(whyred_emmc_xo_active&&whyred_emmc_multi_enabled&&bad_commands==0);
    reset_model();boot_fast=1;corrupt_xo=1;whyred_emmc_perf_configure(host_bytes);
    CHECK(whyred_emmc_perf_prepare(&whyred_emmc_live_io)==0);
    CHECK(!whyred_emmc_xo_active&&cfg_register==0x2613&&clock_register==0xc0c7);
    reset_model();boot_multi=1;fail_cmd23=1;whyred_emmc_perf_configure(host_bytes);
    CHECK(whyred_emmc_perf_prepare(&whyred_emmc_live_io)==0&&!whyred_emmc_multi_enabled);
    reset_model();CHECK(whyred_emmc_try_xo(host_bytes)==1);
    whyred_emmc_multi_enabled=true;fail_data=1;
    CHECK(whyred_emmc_read_blocks(&whyred_emmc_live_io,67,8,guarded+64)==0);
    CHECK(data_ok(guarded+64,67,8)&&guards_ok(4096));
    CHECK(!whyred_emmc_multi_enabled&&!whyred_emmc_xo_active);
    CHECK(commands[18]==1&&commands[17]==8&&commands[12]==1&&commands[13]==1);
    CHECK(whyred_emmc_perf.fallbacks==1&&whyred_emmc_perf.errors==1&&bad_commands==0);
    reset_model();end_delay=3;
    CHECK(whyred_emmc_read_sector(&whyred_emmc_live_io,67,guarded+64)==0);
    CHECK(data_ok(guarded+64,67,1)&&guards_ok(512));
    reset_model();CHECK(whyred_emmc_try_xo(host_bytes)==1);fail_single=1;
    CHECK(whyred_emmc_read_blocks(&whyred_emmc_live_io,67,1,guarded+64)==0);
    CHECK(!whyred_emmc_xo_active&&commands[17]==2&&data_ok(guarded+64,67,1)&&guards_ok(512));
    reset_model();whyred_emmc_multi_enabled=true;fail_cmd18=1;fault_reset=1;
    CHECK(whyred_emmc_read_blocks(&whyred_emmc_live_io,67,8,guarded+64)!=0);
    CHECK(!whyred_emmc_transport_ok);uint32_t old=mmio_writes;
    CHECK(whyred_emmc_read_blocks(&whyred_emmc_live_io,67,8,guarded+64)!=0&&old==mmio_writes);
    for(unsigned size=0;size<=65536;size+=512){
        reset_model();whyred_emmc_multi_enabled=true;
        struct test_buf b={.count=size,.flags=B_READ,.blkno=3,.device=61,.data=guarded+64};
        whyred_emmc_strategy(&b);
        CHECK(b.done==1&&b.error==0&&b.resid==0);
        CHECK(data_ok(guarded+64,67,size/512)&&guards_ok(size)&&bad_commands==0);
        CHECK(commands[18]+commands[17]==(size/16384)+(size%16384!=0));
    }
    for(unsigned failure=0;failure<5;failure++){
        reset_model();
        struct test_buf b={.count=512,.flags=B_READ,.blkno=0,.device=61,.data=guarded+64};
        if(failure==0)b.flags=0;if(failure==1)b.device=0;
        if(failure==2)b.blkno=-1;if(failure==3)b.count=513;if(failure==4)b.blkno=1984;
        whyred_emmc_strategy(&b);CHECK(b.done==1&&b.error!=0&&b.resid==b.count);
        CHECK(mmio_writes==0&&guards_ok(0));
    }
    for(unsigned n=0;n<4096;n++){
        bool expected=n==1||n==2||n==3||n==4;
        for(unsigned p=8;p<4096;p*=2)expected|=n==p;
        CHECK(whyred_boot_log_sample(n)==expected);
    }
    reset_model();whyred_emmc_perf_enabled=true;
    for(unsigned n=0;n<1000;n++){uint64_t start=timer;timer+=test_frequency*31;whyred_emmc_perf_record(512,start);}
    CHECK(whyred_emmc_perf.reports==64&&whyred_emmc_perf.bytes==512000&&whyred_emmc_perf.requests==1000);
    return 0;
}
#ifdef _WIN32
__declspec(dllexport)
#endif
unsigned int whyred_perf_check_count(void){return test_checks;}
