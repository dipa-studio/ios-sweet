#!/usr/bin/env python3
"""Compile actual digitizer helpers; exercise geometry and whole packet rejection."""
import argparse, hashlib, json, os, subprocess
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('source', type=Path)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=True)
header = a.source / 'iokit/Kernel/arm/hid/WhyredTouch.h'
hid = a.source / 'iokit/Kernel/arm/hid/SweetHID.cpp'
text = hid.read_text()
assert 'fWhyred ? whyred_touch_axis(x, 1080)' in text
assert 'fWhyred ? whyred_touch_axis(y, 2160)' in text
assert 'y > panelMaxY - SWEET_TOUCH_EDGE_PX' in text
assert '!fWhyred || whyred_touch_decode_nvt(bytes, length, &frame)' in text
fixture = r'''
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include "WhyredTouch.h"
static unsigned checks;
#define CHECK(c) do { ++checks; if (!(c)) { fprintf(stderr,"line %d\n",__LINE__); return 1; } } while (0)
static void contact(uint8_t *p,unsigned slot,unsigned id,unsigned state,unsigned x,unsigned y) {
 p += slot*6; p[0]=(uint8_t)(id*8+state); p[1]=(uint8_t)(x>>4);
 p[2]=(uint8_t)(y>>4); p[3]=(uint8_t)((x&15)*16+(y&15));
}
int main(void) {
 CHECK(whyred_touch_axis(540,1080)==32768);
 CHECK(whyred_touch_axis(1080,2160)==32768);
 CHECK(whyred_touch_axis(-1,2160)==0);
 CHECK(whyred_touch_axis(9999,2160)==whyred_touch_axis(2159,2160));
 CHECK(whyred_touch_axis(2159,2160)>65500);
 CHECK(whyred_touch_axis(0,0)==0);
 for (int i=1;i<2160;i++) CHECK(whyred_touch_axis(i,2160)>whyred_touch_axis(i-1,2160));
 uint8_t bytes[65]={0}; struct whyred_touch_frame f, before;
 memset(&f,0x5a,sizeof(f)); before=f;
 for (size_t n=0;n<65;n++) { CHECK(whyred_touch_decode_nvt(bytes,n,&f)==-1); CHECK(!memcmp(&f,&before,sizeof(f))); }
 CHECK(whyred_touch_decode_nvt(bytes,66,&f)==-1);
 CHECK(whyred_touch_decode_nvt(NULL,65,&f)==-1);
 CHECK(whyred_touch_decode_nvt(bytes,65,NULL)==-1);
 CHECK(whyred_touch_decode_nvt(bytes,65,&f)==0 && f.active==0);
 contact(bytes,0,10,1,1080,2160);
 CHECK(whyred_touch_decode_nvt(bytes,65,&f)==0 && f.active==512 && f.x[9]==1079 && f.y[9]==2159);
 memset(bytes,0,sizeof(bytes));
 for (unsigned i=0;i<10;i++) contact(bytes,i,10-i,1+(i&1),100+i,200+i);
 CHECK(whyred_touch_decode_nvt(bytes,65,&f)==0 && f.active==1023);
 CHECK(f.x[9]==100 && f.y[0]==209); before=f;
 contact(bytes,1,10,1,50,50);
 CHECK(whyred_touch_decode_nvt(bytes,65,&f)==-1 && !memcmp(&f,&before,sizeof(f)));
 for (unsigned id=0;id<32;id++) {
  memset(bytes,0,sizeof(bytes));contact(bytes,0,id,1,100,100);
  CHECK(whyred_touch_decode_nvt(bytes,65,&f)==(id>=1 && id<=10 ? 0:-1));
 }
 for (unsigned state=0;state<8;state++) {
  memset(bytes,0,sizeof(bytes));contact(bytes,0,1,state,540,1080);
  CHECK(whyred_touch_decode_nvt(bytes,65,&f)==0);
  CHECK(f.active==((state==1 || state==2)?1u:0u));
 }
 memset(bytes,0,sizeof(bytes));contact(bytes,0,1,1,1081,20);
 CHECK(whyred_touch_decode_nvt(bytes,65,&f)==-1);
 contact(bytes,0,1,1,20,2161); CHECK(whyred_touch_decode_nvt(bytes,65,&f)==-1);
 memset(bytes,0x77,6); CHECK(whyred_touch_decode_nvt(bytes,65,&f)==-1);
 memset(bytes,0xff,sizeof(bytes)); CHECK(whyred_touch_decode_nvt(bytes,65,&f)==-1);
 memset(bytes,0,sizeof(bytes)); CHECK(whyred_touch_decode_nvt(bytes,65,&f)==0 && !f.active);
 printf("PASS %u geometry/packet checks\n",checks);
 return 0;
}
'''
cpp = a.output / 'touch.cpp'; cpp.write_text(fixture)
env = os.environ.copy(); env.pop('SDKROOT', None); env.pop('MACOSX_DEPLOYMENT_TARGET', None)
exe = a.output / 'touch-host'
subprocess.run(['clang++','-std=c++11','-Wall','-Wextra','-Werror','-fsanitize=undefined','-I'+str(header.parent.resolve()),str(cpp),'-o',str(exe)],check=True,env=env)
r = subprocess.run([str(exe.resolve())],check=True,capture_output=True,text=True,env=env)
report = dict(passed=True,result=r.stdout.strip(),header_sha256=hashlib.sha256(header.read_bytes()).hexdigest(),hid_sha256=hashlib.sha256(hid.read_bytes()).hexdigest(),hardware_tested=False,i2c_transport_implemented=False)
(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(r.stdout,end='')
