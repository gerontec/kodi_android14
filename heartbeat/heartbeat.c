/*
 * heartbeat.c — MQTT JSON heartbeat sender
 *
 * Sends a JSON heartbeat to a Mosquitto broker every 5 minutes.
 * No external libraries required — raw MQTT 3.1.1 over TCP.
 *
 * Build (ARM):
 *   arm-linux-gnueabihf-gcc -O2 -static -o heartbeat heartbeat.c
 *
 * Usage:
 *   ./heartbeat [broker_host] [broker_port] [topic] [interval_seconds]
 *   ./heartbeat 192.168.178.218 1883 kodi/heartbeat 300
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <time.h>
#include <errno.h>
#include <sys/socket.h>
#include <sys/utsname.h>
#include <sys/ioctl.h>
#include <net/if.h>
#include <netinet/in.h>
#include <netdb.h>
#include <arpa/inet.h>
#include <ifaddrs.h>

#define DEFAULT_HOST     "192.168.178.218"
#define DEFAULT_PORT     1883
#define DEFAULT_TOPIC    "kodi/heartbeat"
#define DEFAULT_INTERVAL 300   /* 5 minutes */
#define CLIENT_ID        "kodi-tv-heartbeat"
#define KEEPALIVE        60

/* ── MQTT 3.1.1 helpers ─────────────────────────────────────────────────── */

static int encode_remaining(uint8_t *buf, int len)
{
    int i = 0;
    do {
        buf[i] = len & 0x7F;
        len >>= 7;
        if (len) buf[i] |= 0x80;
        i++;
    } while (len && i < 4);
    return i;
}

static int write_u16(uint8_t *buf, uint16_t v)
{
    buf[0] = v >> 8;
    buf[1] = v & 0xFF;
    return 2;
}

static int write_str(uint8_t *buf, const char *s)
{
    uint16_t len = (uint16_t)strlen(s);
    write_u16(buf, len);
    memcpy(buf + 2, s, len);
    return 2 + len;
}

/* Build MQTT CONNECT packet → returns total length */
static int mqtt_connect(uint8_t *pkt, const char *client_id)
{
    uint8_t payload[256];
    int     plen = 0;

    /* Variable header: protocol name + level + flags + keepalive */
    uint8_t varh[] = {
        0x00, 0x04, 'M','Q','T','T',   /* protocol name */
        0x04,                           /* level = 3.1.1 */
        0x02,                           /* connect flags: clean session */
        (KEEPALIVE >> 8) & 0xFF,
        KEEPALIVE & 0xFF
    };

    /* Payload: client id */
    plen += write_str(payload + plen, client_id);

    int remaining = sizeof(varh) + plen;
    uint8_t rem[4];
    int remlen = encode_remaining(rem, remaining);

    pkt[0] = 0x10;                          /* CONNECT */
    memcpy(pkt + 1, rem, remlen);
    memcpy(pkt + 1 + remlen, varh, sizeof(varh));
    memcpy(pkt + 1 + remlen + sizeof(varh), payload, plen);

    return 1 + remlen + remaining;
}

/* Build MQTT PUBLISH packet (QoS 0) → returns total length */
static int mqtt_publish(uint8_t *pkt, const char *topic, const char *payload)
{
    uint8_t body[4096];
    int     blen = 0;

    blen += write_str(body + blen, topic);
    int paylen = (int)strlen(payload);
    memcpy(body + blen, payload, paylen);
    blen += paylen;

    uint8_t rem[4];
    int remlen = encode_remaining(rem, blen);

    pkt[0] = 0x30;                          /* PUBLISH, QoS 0, no retain */
    memcpy(pkt + 1, rem, remlen);
    memcpy(pkt + 1 + remlen, body, blen);

    return 1 + remlen + blen;
}

/* Build MQTT DISCONNECT (2 bytes) */
static int mqtt_disconnect(uint8_t *pkt)
{
    pkt[0] = 0xE0;
    pkt[1] = 0x00;
    return 2;
}

/* ── Network ────────────────────────────────────────────────────────────── */

static int tcp_connect(const char *host, int port)
{
    struct addrinfo hints = {0}, *res;
    hints.ai_family   = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;

    char portstr[8];
    snprintf(portstr, sizeof(portstr), "%d", port);

    if (getaddrinfo(host, portstr, &hints, &res) != 0) {
        fprintf(stderr, "getaddrinfo(%s): %s\n", host, strerror(errno));
        return -1;
    }

    int fd = socket(res->ai_family, res->ai_socktype, res->ai_protocol);
    if (fd < 0) { freeaddrinfo(res); return -1; }

    if (connect(fd, res->ai_addr, res->ai_addrlen) < 0) {
        fprintf(stderr, "connect(%s:%d): %s\n", host, port, strerror(errno));
        close(fd);
        freeaddrinfo(res);
        return -1;
    }
    freeaddrinfo(res);
    return fd;
}

static int send_all(int fd, const uint8_t *buf, int len)
{
    int sent = 0;
    while (sent < len) {
        int n = (int)send(fd, buf + sent, len - sent, 0);
        if (n <= 0) return -1;
        sent += n;
    }
    return 0;
}

/* Read CONNACK (4 bytes) and check return code */
static int read_connack(int fd)
{
    uint8_t buf[4];
    int n = (int)recv(fd, buf, sizeof(buf), 0);
    if (n < 4) return -1;
    if (buf[0] != 0x20) return -1;   /* not CONNACK */
    if (buf[3] != 0x00) {
        fprintf(stderr, "CONNACK error code: 0x%02X\n", buf[3]);
        return -1;
    }
    return 0;
}

/* ── IP address collector ────────────────────────────────────────────────── */

/* Append all IPv4/IPv6 addresses (skip loopback) as JSON arrays.
   ipv4_out / ipv6_out: caller-supplied buffers for the JSON array strings. */
static void collect_ips(char *ipv4_out, size_t v4sz,
                        char *ipv6_out, size_t v6sz)
{
    ipv4_out[0] = '\0';
    ipv6_out[0] = '\0';

    struct ifaddrs *ifap = NULL;
    if (getifaddrs(&ifap) != 0) return;

    /* Build comma-separated quoted strings */
    char v4[512] = "";
    char v6[512] = "";

    for (struct ifaddrs *ifa = ifap; ifa; ifa = ifa->ifa_next) {
        if (!ifa->ifa_addr) continue;
        if (ifa->ifa_flags & IFF_LOOPBACK) continue;

        char addr[INET6_ADDRSTRLEN] = "";
        int  family = ifa->ifa_addr->sa_family;

        if (family == AF_INET) {
            inet_ntop(AF_INET,
                      &((struct sockaddr_in *)ifa->ifa_addr)->sin_addr,
                      addr, sizeof(addr));
            if (strlen(v4) + strlen(addr) + 4 < sizeof(v4)) {
                if (v4[0]) strncat(v4, ",", sizeof(v4) - strlen(v4) - 1);
                strncat(v4, "\"", sizeof(v4) - strlen(v4) - 1);
                strncat(v4, addr, sizeof(v4) - strlen(v4) - 1);
                strncat(v4, "\"", sizeof(v4) - strlen(v4) - 1);
            }
        } else if (family == AF_INET6) {
            inet_ntop(AF_INET6,
                      &((struct sockaddr_in6 *)ifa->ifa_addr)->sin6_addr,
                      addr, sizeof(addr));
            /* Skip link-local (fe80::) */
            if (strncmp(addr, "fe80", 4) == 0) continue;
            if (strlen(v6) + strlen(addr) + 4 < sizeof(v6)) {
                if (v6[0]) strncat(v6, ",", sizeof(v6) - strlen(v6) - 1);
                strncat(v6, "\"", sizeof(v6) - strlen(v6) - 1);
                strncat(v6, addr, sizeof(v6) - strlen(v6) - 1);
                strncat(v6, "\"", sizeof(v6) - strlen(v6) - 1);
            }
        }
    }
    freeifaddrs(ifap);

    snprintf(ipv4_out, v4sz, "[%s]", v4);
    snprintf(ipv6_out, v6sz, "[%s]", v6);
}

/* ── Payload builder ─────────────────────────────────────────────────────── */

static void build_json(char *buf, size_t bufsz, const char *client_id)
{
    /* Timestamp */
    time_t now = time(NULL);
    struct tm *t = gmtime(&now);
    char ts[32];
    strftime(ts, sizeof(ts), "%Y-%m-%dT%H:%M:%SZ", t);

    /* Hostname */
    char hostname[128] = "unknown";
    gethostname(hostname, sizeof(hostname));

    /* Uptime from /proc/uptime */
    double uptime_s = 0;
    FILE *f = fopen("/proc/uptime", "r");
    if (f) { (void)fscanf(f, "%lf", &uptime_s); fclose(f); }
    long uptime_min = (long)(uptime_s / 60);

    /* Kernel */
    struct utsname u;
    uname(&u);

    /* IP addresses */
    char ipv4[512], ipv6[512];
    collect_ips(ipv4, sizeof(ipv4), ipv6, sizeof(ipv6));

    snprintf(buf, bufsz,
        "{"
        "\"client\":\"%s\","
        "\"host\":\"%s\","
        "\"ts\":\"%s\","
        "\"uptime_min\":%ld,"
        "\"os\":\"%s %s\","
        "\"ipv4\":%s,"
        "\"ipv6\":%s,"
        "\"status\":\"alive\""
        "}",
        client_id, hostname, ts, uptime_min,
        u.sysname, u.release,
        ipv4, ipv6);
}

/* ── Main ────────────────────────────────────────────────────────────────── */

int main(int argc, char *argv[])
{
    const char *host     = argc > 1 ? argv[1] : DEFAULT_HOST;
    int         port     = argc > 2 ? atoi(argv[2]) : DEFAULT_PORT;
    const char *topic    = argc > 3 ? argv[3] : DEFAULT_TOPIC;
    int         interval = argc > 4 ? atoi(argv[4]) : DEFAULT_INTERVAL;

    fprintf(stderr, "heartbeat: broker=%s:%d  topic=%s  interval=%ds\n",
            host, port, topic, interval);

    uint8_t pkt[4096];
    char    json[2048];
    int     seq = 0;

    while (1) {
        /* Build and send heartbeat */
        int fd = tcp_connect(host, port);
        if (fd < 0) {
            fprintf(stderr, "Connection failed, retry in %ds\n", interval);
            goto wait;
        }

        /* CONNECT */
        int n = mqtt_connect(pkt, CLIENT_ID);
        if (send_all(fd, pkt, n) < 0 || read_connack(fd) < 0) {
            fprintf(stderr, "MQTT handshake failed\n");
            close(fd);
            goto wait;
        }

        /* PUBLISH */
        build_json(json, sizeof(json), CLIENT_ID);
        /* inject sequence number */
        char *end = json + strlen(json) - 1;  /* before closing } */
        char seq_buf[32];
        snprintf(seq_buf, sizeof(seq_buf), ",\"seq\":%d}", seq++);
        *end = '\0';
        strncat(json, seq_buf, sizeof(json) - strlen(json) - 1);

        n = mqtt_publish(pkt, topic, json);
        if (send_all(fd, pkt, n) == 0) {
            time_t now = time(NULL);
            fprintf(stderr, "%.19s  published seq=%d → %s\n",
                    ctime(&now), seq - 1, topic);
        }

        /* DISCONNECT */
        n = mqtt_disconnect(pkt);
        send_all(fd, pkt, n);
        close(fd);

    wait:
        sleep(interval);
    }
    return 0;
}
