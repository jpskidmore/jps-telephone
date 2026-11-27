#ifndef AKSIPPreferredAddressFamily_h
#define AKSIPPreferredAddressFamily_h

#include <netdb.h>
#include <netinet/in.h>
#include <stdbool.h>
#include <unistd.h>

static inline bool AKSIPHostHasIPv6Route(const char *host) {
    if (!host || !*host) {
        return false;
    }

    const struct addrinfo hints = {.ai_family = AF_INET6, .ai_socktype = SOCK_DGRAM};
    struct addrinfo *addresses = NULL;
    if (getaddrinfo(host, "5060", &hints, &addresses) != 0) {
        return false;
    }

    bool reachable = false;
    for (const struct addrinfo *entry = addresses; entry && !reachable; entry = entry->ai_next) {
        const struct sockaddr_in6 *address = (const struct sockaddr_in6 *)entry->ai_addr;
        if (IN6_IS_ADDR_V4MAPPED(&address->sin6_addr)) {
            continue;
        }
        int fd = socket(AF_INET6, SOCK_DGRAM, 0);
        if (fd >= 0) {
            // A UDP connect selects a local route without sending a packet.
            reachable = connect(fd, entry->ai_addr, entry->ai_addrlen) == 0;
            close(fd);
        }
    }
    freeaddrinfo(addresses);
    return reachable;
}

#endif
