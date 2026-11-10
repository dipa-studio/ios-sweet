/* tools/mkbootimg/dtbimg.c
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
** December 2016, Christopher N. Hesse
** Separate dt creation from mkbootimg program.
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

/* must be provided by the device tree */
#include <samsung_dtbh.h>

#include "libfdt.h"

struct dt_blob;

struct dt_entry {
    uint32_t chip;
    uint32_t platform;
    uint32_t subtype;
    uint32_t hw_rev;
    uint32_t hw_rev_end;
    uint32_t offset;
    uint32_t size; /* including padding */
    uint32_t space;

    struct dt_blob *blob;
};

/*
 * Comparator for sorting dt_entries
 */
static int dt_entry_cmp(const void *ap, const void *bp)
{
    struct dt_entry *a = (struct dt_entry*)ap;
    struct dt_entry *b = (struct dt_entry*)bp;

    if (a->chip != b->chip)
        return a->chip - b->chip;
    return a->hw_rev - b->hw_rev;
}

/*
 * In memory representation of a dtb blob
 */
struct dt_blob {
    uint32_t size;
    uint32_t offset;

    void *payload;
    struct dt_blob *next;
};

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

void *load_dtbh_block(const char *dtb_path, unsigned pagesize, unsigned *_sz)
{
    const unsigned pagemask = pagesize - 1;
    struct dt_entry *new_entries;
    struct dt_entry *entries = NULL;
    struct dt_entry *entry;
    struct dt_blob *blob;
    struct dt_blob *blob_list = NULL;
    struct dt_blob *last_blob = NULL;
    struct dirent *de;
    unsigned new_count;
    unsigned entry_count = 0;
    unsigned offset;
    unsigned dtb_sz;
    unsigned hdr_sz = DT_HEADER_PHYS_SIZE;
    uint32_t version = DTBH_VERSION;
    unsigned blob_sz = 0;
    char fname[PATH_MAX];
    const unsigned *model;
    const unsigned *prop_chip;
    const unsigned *prop_platform;
    const unsigned *prop_subtype;
    const unsigned *prop_hw_rev;
    const unsigned *prop_hw_rev_end;
    int namlen;
    int len;
    void *dtb;
    char *dtbh;
    DIR *dir;
    unsigned c;

    dir = opendir(dtb_path);

    if (dir == NULL)
        err(1, "failed to open '%s'", dtb_path);

    while ((de = readdir(dir)) != NULL) {
        namlen = strlen(de->d_name);
        if (namlen < 4 || strcmp(&de->d_name[namlen - 4], ".dtb"))
            continue;

        snprintf(fname, sizeof(fname), "%s/%s", dtb_path, de->d_name);

        dtb = load_file(fname, &dtb_sz);
        if (dtb == NULL)
            err(1, "failed to read dtb '%s'", fname);

        if (fdt_check_header(dtb) != 0) {
            warnx("'%s' is not a valid dtb, skipping", fname);
            free(dtb);
            continue;
        }

        offset = fdt_path_offset(dtb, "/");

#ifdef DTBH_MODEL
        model = fdt_getprop(dtb, offset, "model", &len);
        if (strstr((char *)&model[0], DTBH_MODEL) == NULL) {
            warnx("model of %s is invalid, skipping (expected *%s* but got %s)",
                  fname, DTBH_MODEL, (char *)&model[0]);
            free(dtb);
            continue;
        }
#endif

        prop_chip = fdt_getprop(dtb, offset, "model_info-chip", &len);
        if (len % (sizeof(uint32_t)) != 0) {
            warnx("model_info-chip of %s is of invalid size, skipping", fname);
            free(dtb);
            continue;
        }

        prop_platform = fdt_getprop(dtb, offset, "model_info-platform", &len);
        if (strcmp((char *)&prop_platform[0], DTBH_PLATFORM)) {
            warnx("model_info-platform of %s is invalid, skipping (expected %s but got %s)",
                  fname, DTBH_PLATFORM, (char *)&prop_platform[0]);
            free(dtb);
            continue;
        }

        prop_subtype = fdt_getprop(dtb, offset, "model_info-subtype", &len);
        if (strcmp((char *)&prop_subtype[0], DTBH_SUBTYPE)) {
            warnx("model_info-subtype of %s is invalid, skipping (expected %s but got %s)",
                  fname, DTBH_SUBTYPE, (char *)&prop_subtype[0]);
            free(dtb);
            continue;
        }

        prop_hw_rev = fdt_getprop(dtb, offset, "model_info-hw_rev", &len);
        if (len % (sizeof(uint32_t)) != 0) {
            warnx("model_info-hw_rev of %s is of invalid size, skipping", fname);
            free(dtb);
            continue;
        }

        prop_hw_rev_end = fdt_getprop(dtb, offset, "model_info-hw_rev_end", &len);
        if (len % (sizeof(uint32_t)) != 0) {
            warnx("model_info-hw_rev_end of %s is of invalid size, skipping", fname);
            free(dtb);
            continue;
        }

        blob = calloc(1, sizeof(struct dt_blob));
        if (blob == NULL)
            err(1, "failed to allocate memory");

        blob->payload = dtb;
        blob->size = dtb_sz;
        if (blob_list == NULL) {
            blob_list = blob;
            last_blob = blob;
        } else {
            last_blob->next = blob;
            last_blob = blob;
        }

        blob_sz += (blob->size + pagemask) & ~pagemask;
        new_count = entry_count + 1;
        new_entries = realloc(entries, new_count * sizeof(struct dt_entry));
        if (new_entries == NULL)
            err(1, "failed to allocate memory");

        entries = new_entries;
        entry = &entries[entry_count];
        memset(entry, 0, sizeof(*entry));
        entry->chip = ntohl(prop_chip[0]);
        entry->platform = DTBH_PLATFORM_CODE;
        entry->subtype = DTBH_SUBTYPE_CODE;
        entry->hw_rev = ntohl(prop_hw_rev[0]);
        entry->hw_rev_end = ntohl(prop_hw_rev_end[0]);
        entry->space = 0x20; /* space delimiter */
        entry->blob = blob;

        entry_count++;

        hdr_sz += entry_count * DT_ENTRY_PHYS_SIZE;
    }

    closedir(dir);

    if (entry_count == 0) {
        warnx("unable to locate any dtbs in the given path");
        return NULL;
    }

    hdr_sz += sizeof(uint32_t); /* eot marker */
    hdr_sz = (hdr_sz + pagemask) & ~pagemask;

    qsort(entries, entry_count, sizeof(struct dt_entry), dt_entry_cmp);

    /* The size of the dt header is now known, calculate the blob offsets... */
    offset = hdr_sz;
    for (blob = blob_list; blob; blob = blob->next) {
        blob->offset = offset;
        offset += (blob->size + pagemask) & ~pagemask;
    }

    /* ...and update the entries */
    for (c = 0; c < entry_count; c++) {
        entry = &entries[c];

        entry->offset = entry->blob->offset;
        entry->size = (entry->blob->size + pagemask) & ~pagemask;
    }

    /*
     * All parts are now gathered, so build the dt block
     */
    dtbh = calloc(hdr_sz + blob_sz, 1);
    if (dtbh == NULL)
            err(1, "failed to allocate memory");

    offset = 0;

    memcpy(dtbh, DTBH_MAGIC, sizeof(uint32_t));
    memcpy(dtbh + sizeof(uint32_t), &version, sizeof(uint32_t));
    memcpy(dtbh + (sizeof(uint32_t) * 2), &entry_count, sizeof(uint32_t));

    offset += DT_HEADER_PHYS_SIZE;

    /* add dtbh entries */
    for (c = 0; c < entry_count; c++) {
        entry = &entries[c];
        memcpy(dtbh + offset, entry, DT_ENTRY_PHYS_SIZE);
        offset += DT_ENTRY_PHYS_SIZE;
    }

    /* add padding after dt header */
    offset += pagesize - (offset & pagemask);

    for (blob = blob_list; blob; blob = blob->next) {
        memcpy(dtbh + offset, blob->payload, blob->size);
        offset += (blob->size + pagemask) & ~pagemask;
    }

    *_sz = hdr_sz + blob_sz;

    return dtbh;
}
