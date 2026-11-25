/* Development USB log mirror. Authentication decisions remain in Dropbear. */
#ifndef WHYRED_SSH_UDP_H
#define WHYRED_SSH_UDP_H
#include <sys/socket.h>
#include <netinet/in.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#ifndef WHYRED_SSH_LOG_SOURCE
#define WHYRED_SSH_LOG_SOURCE 0xc0a80702u
#endif
#ifndef WHYRED_SSH_LOG_DESTINATION
#define WHYRED_SSH_LOG_DESTINATION 0xc0a80701u
#endif
#ifndef WHYRED_SSH_LOG_PORT
#define WHYRED_SSH_LOG_PORT 5140
#endif
static void whyred_ssh_usb_log(const char *message) {
    int saved = errno;
    static unsigned budget = 512;
    if (!budget) return;
    budget--;
    char line[1024];
    int n = snprintf(line, sizeof(line), "WHYRED SSH: pid=%d %s\n", getpid(), message);
    if (n < 0) { errno = saved; return; }
    size_t length = (size_t)n < sizeof(line) ? (size_t)n : sizeof(line) - 1;
    if (length) line[length - 1] = '\n';
    for (size_t i = 0; i + 1 < length; i++)
        if ((unsigned char)line[i] < 32 || (unsigned char)line[i] == 127) line[i] = ' ';
    int fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd >= 0) {
        struct sockaddr_in source, destination;
        memset(&source, 0, sizeof(source)); memset(&destination, 0, sizeof(destination));
#if defined(__APPLE__)
        source.sin_len = sizeof(source); destination.sin_len = sizeof(destination);
#endif
        source.sin_family = destination.sin_family = AF_INET;
        source.sin_addr.s_addr = htonl(WHYRED_SSH_LOG_SOURCE);
        destination.sin_addr.s_addr = htonl(WHYRED_SSH_LOG_DESTINATION);
        destination.sin_port = htons(WHYRED_SSH_LOG_PORT);
        int flags = fcntl(fd, F_GETFL);
        if (flags >= 0 && !fcntl(fd, F_SETFL, flags | O_NONBLOCK) &&
            !bind(fd, (struct sockaddr *)&source, sizeof(source)))
            (void)sendto(fd, line, length, 0, (struct sockaddr *)&destination, sizeof(destination));
        close(fd);
    }
    errno = saved;
}
#endif
