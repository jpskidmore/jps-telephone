#include "AKSIPPreferredAddressFamily.h"
#include <pjsua.h>
#include <stdio.h>
#include <string.h>

#define CHECK(expr) do { \
    const pj_status_t status = (expr); \
    if (status != PJ_SUCCESS) { \
        pjsua_perror("loopback", #expr, status); \
        return 1; \
    } \
} while (0)

int main(int argc, char **argv) {
    if (argc != 3) {
        return 2;
    }

    pjsua_config ua;
    pjsua_media_config media;
    pjsua_transport_config transport;
    pjsua_acc_config account;
    pjsua_transport_id transport4, transport6;
    pjsua_acc_id account_id;
    pjsua_call_id call_id;
    CHECK(pjsua_create());
    pjsua_config_default(&ua);
    pjsua_media_config_default(&media);
    media.enable_ice = PJ_FALSE;
    CHECK(pjsua_init(&ua, NULL, &media));

    pjsua_transport_config_default(&transport);
    transport.bound_addr = pj_str("127.0.0.1");
    CHECK(pjsua_transport_create(PJSIP_TRANSPORT_UDP, &transport, &transport4));
    transport.bound_addr = pj_str("::1");
    CHECK(pjsua_transport_create(PJSIP_TRANSPORT_UDP6, &transport, &transport6));
    CHECK(pjsua_start());
    CHECK(pjsua_set_null_snd_dev());

    pj_bool_t ipv6 = AKSIPHostHasIPv6Route(argv[1]);
    pjsua_acc_config_default(&account);
    account.id = pj_str(ipv6 ? "sip:synthetic@[::1]" : "sip:synthetic@127.0.0.1");
    account.transport_id = ipv6 ? transport6 : transport4;
    account.ipv6_sip_use = ipv6 ? PJSUA_IPV6_ENABLED_USE_IPV6_ONLY : PJSUA_IPV6_DISABLED;
    account.ipv6_media_use = account.ipv6_sip_use;
    account.rtp_cfg.bound_addr = pj_str(ipv6 ? "::1" : "127.0.0.1");
    CHECK(pjsua_acc_add(&account, PJ_TRUE, &account_id));

    pj_str_t destination = pj_str(argv[2]);
    CHECK(pjsua_call_make_call(account_id, &destination, NULL, NULL, NULL, &call_id));
    for (int attempt = 0; attempt < 100; ++attempt) {
        pjsua_call_info info;
        CHECK(pjsua_call_get_info(call_id, &info));
        if (info.state == PJSIP_INV_STATE_CONFIRMED) {
            CHECK(pjsua_destroy());
            return 0;
        }
        pj_thread_sleep(25);
    }

    CHECK(pjsua_destroy());
    fputs("Synthetic SIP call did not reach confirmed state\n", stderr);
    return 1;
}
