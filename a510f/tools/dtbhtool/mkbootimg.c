/* tools/mkbootimg/mkbootimg.c
**
** Copyright 2007, The Android Open Source Project
** Copyright 2013, Sony Mobile Communications
**
** Licensed under the Apache License, Version 2.0 (the "License");
** you may not use this file except in compliance with the License.
** You may obtain a copy of the License at
**
**     http://www.apache.org/licenses/LICENSE-2.0
**
** Unless required by applicable law or agreed to in writing, software
** distributed under the License is distributed on an "AS IS" BASIS,
** WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
** See the License for the specific language governing permissions and
** limitations under the License.
**
** June 2014, Ketut Putu Kumajaya
** Modified for Samsung Exynos DTBH, based on mkqcdtbootimg from Sony
*/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <limits.h>

#include <sys/types.h>
#include <arpa/inet.h>
#include <assert.h>
#include <dirent.h>
#include <err.h>
#include <stdint.h>

#include <dtbimg.h>

#include <openssl/sha.h>
#include "bootimg.h"

static void *load_file(const char *fn, unsigned *_sz)
{
    char *data;
    int sz;
    int fd;

    data = 0;
    fd = open(fn, O_RDONLY);
    if(fd < 0) return 0;

    sz = lseek(fd, 0, SEEK_END);
    if(sz < 0) goto oops;

    if(lseek(fd, 0, SEEK_SET) != 0) goto oops;

    data = (char*) malloc(sz);
    if(data == 0) goto oops;

    if(read(fd, data, sz) != sz) goto oops;
    close(fd);

    if(_sz) *_sz = sz;
    return data;

oops:
    close(fd);
    if(data != 0) free(data);
    return 0;
}

int usage(void)
{
    fprintf(stderr,"usage: mkbootimg\n"
            "       --kernel <filename>\n"
            "       --ramdisk <filename>\n"
            "       [ --second <2ndbootloader-filename> ]\n"
            "       [ --cmdline <kernel-commandline> ]\n"
            "       [ --board <boardname> ]\n"
            "       [ --base <address> ]\n"
            "       [ --pagesize <pagesize> ]\n"
            "       [ --ramdisk_offset <address> ]\n"
            "       [ --dt_dir <dtb path> ]\n"
            "       [ --dt <filename> ]\n"
            "       [ --signature <filename> ]\n"
            "       -o|--output <filename>\n"
            );
    return 1;
}



static unsigned char padding[131072] = { 0, };

int write_padding(int fd, unsigned pagesize, unsigned itemsize)
{
    unsigned pagemask = pagesize - 1;
    unsigned count;

    if((itemsize & pagemask) == 0) {
        return 0;
    }

    count = pagesize - (itemsize & pagemask);

    if(write(fd, padding, count) != count) {
        return -1;
    } else {
        return 0;
    }
}

int main(int argc, char **argv)
{
    boot_img_hdr hdr;

    char *kernel_fn = 0;
    void *kernel_data = 0;
    char *ramdisk_fn = 0;
    void *ramdisk_data = 0;
    char *second_fn = 0;
    void *second_data = 0;
    char *cmdline = "";
    char *bootimg = 0;
    char *board = "";
    char *dt_dir = 0;
    char *dt_fn = 0;
    void *dt_data = 0;
    char *sig_fn = 0;
    void *sig_data = 0;
    unsigned pagesize = 2048;
    int fd;
    SHA_CTX ctx;
    uint8_t sha[SHA_DIGEST_LENGTH];
    unsigned base           = 0x10000000;
    unsigned kernel_offset  = 0x00008000;
    unsigned ramdisk_offset = 0x01000000;
    unsigned second_offset  = 0x00f00000;
    unsigned tags_offset    = 0x00000100;

    argc--;
    argv++;

    memset(&hdr, 0, sizeof(hdr));

    while(argc > 0){
        char *arg = argv[0];
        char *val = argv[1];
        if(argc < 2) {
            return usage();
        }
        argc -= 2;
        argv += 2;
        if(!strcmp(arg, "--output") || !strcmp(arg, "-o")) {
            bootimg = val;
        } else if(!strcmp(arg, "--kernel")) {
            kernel_fn = val;
        } else if(!strcmp(arg, "--ramdisk")) {
            ramdisk_fn = val;
        } else if(!strcmp(arg, "--second")) {
            second_fn = val;
        } else if(!strcmp(arg, "--cmdline")) {
            cmdline = val;
        } else if(!strcmp(arg, "--base")) {
            base = strtoul(val, 0, 16);
        } else if(!strcmp(arg, "--kernel_offset")) {
            kernel_offset = strtoul(val, 0, 16);
        } else if(!strcmp(arg, "--ramdisk_offset")) {
            ramdisk_offset = strtoul(val, 0, 16);
        } else if(!strcmp(arg, "--second_offset")) {
            second_offset = strtoul(val, 0, 16);
        } else if(!strcmp(arg, "--tags_offset")) {
            tags_offset = strtoul(val, 0, 16);
        } else if(!strcmp(arg, "--board")) {
            board = val;
        } else if(!strcmp(arg,"--pagesize")) {
            pagesize = strtoul(val, 0, 10);
            if ((pagesize != 2048) && (pagesize != 4096) && (pagesize != 8192) && (pagesize != 16384) && (pagesize != 32768) && (pagesize != 65536) && (pagesize != 131072)) {
                fprintf(stderr,"error: unsupported page size %d\n", pagesize);
                return -1;
            }
        } else if (!strcmp(arg, "--dt_dir")) {
            dt_dir = val;
        } else if(!strcmp(arg, "--dt")) {
            dt_fn = val;
        } else if(!strcmp(arg, "--signature")) {
            sig_fn = val;
        } else {
            return usage();
        }
    }
    hdr.page_size = pagesize;

    hdr.kernel_addr =  base + kernel_offset;
    hdr.ramdisk_addr = base + ramdisk_offset;
    hdr.second_addr =  base + second_offset;
    hdr.tags_addr =    base + tags_offset;

    if (dt_dir && dt_fn) {
        fprintf(stderr,"error: don't use both --dt_dir and --dt option\n");
        return usage();
    }

    if(bootimg == 0) {
        fprintf(stderr,"error: no output filename specified\n");
        return usage();
    }

    if(kernel_fn == 0) {
        fprintf(stderr,"error: no kernel image specified\n");
        return usage();
    }

    if(ramdisk_fn == 0) {
        fprintf(stderr,"error: no ramdisk image specified\n");
        return usage();
    }

    if(strlen(board) >= BOOT_NAME_SIZE) {
        fprintf(stderr,"error: board name too large\n");
        return usage();
    }

    strcpy(hdr.name, board);

    memcpy(hdr.magic, BOOT_MAGIC, BOOT_MAGIC_SIZE);

    if(strlen(cmdline) > (BOOT_ARGS_SIZE - 1)) {
        fprintf(stderr,"error: kernel commandline too large\n");
        return 1;
    }
    strcpy((char*)hdr.cmdline, cmdline);

    kernel_data = load_file(kernel_fn, &hdr.kernel_size);
    if(kernel_data == 0) {
        fprintf(stderr,"error: could not load kernel '%s'\n", kernel_fn);
        return 1;
    }

    if(!strcmp(ramdisk_fn,"NONE")) {
        ramdisk_data = 0;
        hdr.ramdisk_size = 0;
    } else {
        ramdisk_data = load_file(ramdisk_fn, &hdr.ramdisk_size);
        if(ramdisk_data == 0) {
            fprintf(stderr,"error: could not load ramdisk '%s'\n", ramdisk_fn);
            return 1;
        }
    }

    if(second_fn) {
        second_data = load_file(second_fn, &hdr.second_size);
        if(second_data == 0) {
            fprintf(stderr,"error: could not load secondstage '%s'\n", second_fn);
            return 1;
        }
    }

    if (dt_dir) {
        dt_data = load_dtbh_block(dt_dir, pagesize, &hdr.dt_size);
        if (dt_data == 0) {
            fprintf(stderr, "error: could not load device tree blobs '%s'\n", dt_dir);
            return 1;
        }
    }

    if(dt_fn) {
        dt_data = load_file(dt_fn, &hdr.dt_size);
        if (dt_data == 0) {
            fprintf(stderr,"error: could not load device tree image '%s'\n", dt_fn);
            return 1;
        }
    }

    if(sig_fn) {
        sig_data = load_file(sig_fn, 0);
        if (sig_data == 0) {
            fprintf(stderr,"error: could not load signature '%s'\n", sig_fn);
            return 1;
        }
    }

    /* put a hash of the contents in the header so boot images can be
     * differentiated based on their first 2k.
     */
    SHA1_Init(&ctx);
    SHA1_Update(&ctx, kernel_data, hdr.kernel_size);
    SHA1_Update(&ctx, &hdr.kernel_size, sizeof(hdr.kernel_size));
    SHA1_Update(&ctx, ramdisk_data, hdr.ramdisk_size);
    SHA1_Update(&ctx, &hdr.ramdisk_size, sizeof(hdr.ramdisk_size));
    SHA1_Update(&ctx, second_data, hdr.second_size);
    SHA1_Update(&ctx, &hdr.second_size, sizeof(hdr.second_size));
    if(dt_data) {
        SHA1_Update(&ctx, dt_data, hdr.dt_size);
        SHA1_Update(&ctx, &hdr.dt_size, sizeof(hdr.dt_size));
    }
    SHA1_Final(sha, &ctx);
    memcpy(hdr.id, sha,
           SHA_DIGEST_LENGTH > sizeof(hdr.id) ? sizeof(hdr.id) : SHA_DIGEST_LENGTH);

    fd = open(bootimg, O_CREAT | O_TRUNC | O_WRONLY, 0644);
    if(fd < 0) {
        fprintf(stderr,"error: could not create '%s'\n", bootimg);
        return 1;
    }

    if(write(fd, &hdr, sizeof(hdr)) != sizeof(hdr)) goto fail;
    if(write_padding(fd, pagesize, sizeof(hdr))) goto fail;

    if(write(fd, kernel_data, hdr.kernel_size) != hdr.kernel_size) goto fail;
    if(write_padding(fd, pagesize, hdr.kernel_size)) goto fail;

    if(write(fd, ramdisk_data, hdr.ramdisk_size) != hdr.ramdisk_size) goto fail;
    if(write_padding(fd, pagesize, hdr.ramdisk_size)) goto fail;

    if(second_data) {
        if(write(fd, second_data, hdr.second_size) != hdr.second_size) goto fail;
        if(write_padding(fd, pagesize, hdr.ramdisk_size)) goto fail;
    }

    if(dt_data) {
        if(write(fd, dt_data, hdr.dt_size) != hdr.dt_size) goto fail;
        if(write_padding(fd, pagesize, hdr.dt_size)) goto fail;
    }

    if(sig_data) {
        if(write(fd, sig_data, 256) != 256) goto fail;
    }

    return 0;

fail:
    unlink(bootimg);
    close(fd);
    fprintf(stderr,"error: failed writing '%s': %s\n", bootimg,
            strerror(errno));
    return 1;
}
