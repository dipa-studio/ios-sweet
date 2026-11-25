/* Windows host test SHA-256 backend; the kernel uses its existing SHA2 API. */
#ifndef WHYRED_HOST_SHA_H
#define WHYRED_HOST_SHA_H
#include <windows.h>
#include <bcrypt.h>
#include <stdlib.h>
#include <stdint.h>
static unsigned char *SHA256(const unsigned char *data, size_t len, unsigned char out[32]) {
    BCRYPT_ALG_HANDLE alg = NULL;
    BCRYPT_HASH_HANDLE hash = NULL;
    if (BCryptOpenAlgorithmProvider(&alg, BCRYPT_SHA256_ALGORITHM, NULL, 0) < 0 ||
        BCryptCreateHash(alg, &hash, NULL, 0, NULL, 0, 0) < 0) abort();
    while (len != 0) {
        ULONG n = len > UINT32_MAX ? UINT32_MAX : (ULONG)len;
        if (BCryptHashData(hash, (PUCHAR)data, n, 0) < 0) abort();
        data += n; len -= n;
    }
    if (BCryptFinishHash(hash, out, 32, 0) < 0) abort();
    BCryptDestroyHash(hash);
    BCryptCloseAlgorithmProvider(alg, 0);
    return out;
}
#endif
