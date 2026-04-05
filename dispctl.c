/*
 * dispctl.c — Android TV display control via uinput + MQTT
 * Läuft als ADB-shell user (group uhid → /dev/uinput Zugriff)
 *
 * Build in Termux:
 *   clang -O2 -fPIE -pie dispctl.c -o /data/local/tmp/dispctl
 *
 * Verwendung:
 *   dispctl --on | --off | --toggle | --saver | --status
 *   dispctl --mqtt [broker=192.168.178.218] [prefix=tv/display]
 *
 * MQTT:
 *   Subscribe: tv/display/set   → ON | OFF | TOGGLE | SAVER | STATUS
 *   Publish:   tv/display/state → ON | OFF
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <time.h>
#include <signal.h>
#include <sys/socket.h>
#include <sys/select.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>

/* ── display control via Android input service ───────────────────────────── */

static void screen_off(void)   { system("input keyevent KEYCODE_SLEEP");      printf("Screen: OFF\n");  fflush(stdout); }
static void screen_on(void)    { system("input keyevent KEYCODE_WAKEUP");     printf("Screen: ON\n");   fflush(stdout); }
static void screen_saver(void) { system("service call dreams 1 2>/dev/null"); printf("Screensaver\n"); fflush(stdout); }

/* ── source / app switching ─────────────────────────────────────────────── */
/* 1=kodi (default), 2=astra live-tv, 3=google home                         */

static void launch_source(int src) {
    char cmd[256];
    const char *pkg = NULL;
    switch (src) {
        case 1: pkg = "de.gerontec.kodilauncher/.LauncherActivity";             break;
        case 2: pkg = "com.cltv.hybrid/com.iwedia.cltv.MainActivity";          break;
        case 3: pkg = "com.google.android.apps.tv.launcherx/.home.HomeActivity"; break;
        default:
            fprintf(stderr, "Unbekannte Quelle: %d (1=Kodi 2=Astra 3=Google)\n", src);
            return;
    }
    snprintf(cmd, sizeof(cmd), "am start -n %s", pkg);
    system(cmd);
    printf("Source: %d (%s)\n", src, pkg); fflush(stdout);
}

static int screen_state(void) {
    FILE *fp = popen("dumpsys power 2>/dev/null", "r");
    char buf[256];
    int st = -1;
    if (!fp) return -1;
    while (fgets(buf, sizeof(buf), fp)) {
        if (strstr(buf, "mWakefulness=")) {
            st = !!strstr(buf, "Awake"); break;
        }
        if (strstr(buf, "Display Power")) {
            st = !!strstr(buf, "state=ON"); break;
        }
    }
    pclose(fp);
    return st;
}

/* ── minimal MQTT (no external lib) ─────────────────────────────────────── */

static int tcp_connect(const char *host, int port) {
    struct sockaddr_in addr;
    struct hostent *he = gethostbyname(host);
    if (!he) { fprintf(stderr, "DNS lookup failed: %s\n", host); return -1; }
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port   = htons(port);
    memcpy(&addr.sin_addr, he->h_addr, he->h_length);
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) { perror("socket"); return -1; }
    if (connect(fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) { perror("connect"); close(fd); return -1; }
    return fd;
}

static int xwrite(int fd, const unsigned char *buf, int len) {
    return write(fd, buf, len) == len ? 0 : -1;
}

static int mqtt_connect_pkt(int fd, const char *cid) {
    int cl = strlen(cid);
    int pl = 10 + 2 + cl;
    unsigned char b[128]; int i = 0;
    b[i++]=0x10; b[i++]=(unsigned char)pl;
    b[i++]=0; b[i++]=4; b[i++]='M'; b[i++]='Q'; b[i++]='T'; b[i++]='T';
    b[i++]=4; b[i++]=2; b[i++]=0; b[i++]=60;
    b[i++]=0; b[i++]=(unsigned char)cl;
    memcpy(&b[i], cid, cl); i += cl;
    return xwrite(fd, b, i);
}

static int mqtt_sub(int fd, const char *topic) {
    int tl = strlen(topic);
    int pl = 2 + 2 + tl + 1;
    unsigned char b[256]; int i = 0;
    b[i++]=0x82; b[i++]=(unsigned char)pl;
    b[i++]=0; b[i++]=1;
    b[i++]=0; b[i++]=(unsigned char)tl;
    memcpy(&b[i], topic, tl); i += tl;
    b[i++]=0;
    return xwrite(fd, b, i);
}

static int mqtt_pub(int fd, const char *topic, const char *payload) {
    int tl = strlen(topic), vl = strlen(payload);
    int pl = 2 + tl + vl;
    unsigned char b[512]; int i = 0;
    b[i++]=0x30; b[i++]=(unsigned char)pl;
    b[i++]=0; b[i++]=(unsigned char)tl;
    memcpy(&b[i], topic, tl); i += tl;
    memcpy(&b[i], payload, vl); i += vl;
    return xwrite(fd, b, i);
}

static int mqtt_ping(int fd) {
    unsigned char b[2] = {0xC0, 0x00};
    return xwrite(fd, b, 2);
}

static int mqtt_read(int fd, unsigned char *out, int maxlen, int *out_rem) {
    unsigned char t, e; int rem = 0, mul = 1;
    if (read(fd, &t, 1) != 1) return -1;
    do {
        if (read(fd, &e, 1) != 1) return -1;
        rem += (e & 0x7F) * mul; mul *= 128;
    } while (e & 0x80);
    if (out_rem) *out_rem = rem;
    if (rem > 0 && rem < maxlen) {
        int got = 0;
        while (got < rem) { int r = read(fd, out+got, rem-got); if (r <= 0) return -1; got += r; }
    }
    if (rem < maxlen) out[rem] = 0;
    return t >> 4;
}

/* ── MQTT daemon ─────────────────────────────────────────────────────────── */

static volatile int running = 1;
static void on_sig(int s) { (void)s; running = 0; }

static void run_mqtt(const char *broker, const char *prefix) {
    char set_t[256], state_t[256];
    snprintf(set_t,   sizeof(set_t),   "%s/set",   prefix);
    snprintf(state_t, sizeof(state_t), "%s/state", prefix);

    signal(SIGINT, on_sig); signal(SIGTERM, on_sig);

    printf("MQTT: %s:1883  sub=%s  pub=%s\n", broker, set_t, state_t);
    fflush(stdout);

    int mfd = -1;
reconnect:
    if (!running) { close(mfd); printf("Stopped.\n"); return; }
    if (mfd >= 0) close(mfd);
    mfd = tcp_connect(broker, 1883);
    if (mfd < 0) { fprintf(stderr, "Retry in 5s...\n"); sleep(5); goto reconnect; }

    mqtt_connect_pkt(mfd, "dispctl-tv");
    usleep(150000);

    unsigned char pkt[512]; int pkt_rem = 0;
    if (mqtt_read(mfd, pkt, sizeof(pkt), NULL) != 2) {
        fprintf(stderr, "CONNACK failed\n"); sleep(3); goto reconnect;
    }

    mqtt_sub(mfd, set_t);
    usleep(100000);

    int st = screen_state();
    mqtt_pub(mfd, state_t, st == 1 ? "ON" : "OFF");

    time_t last_report = time(NULL);

    while (running) {
        struct timeval tv = {30, 0};
        fd_set rfds; FD_ZERO(&rfds); FD_SET(mfd, &rfds);
        int sel = select(mfd+1, &rfds, NULL, NULL, &tv);
        if (sel < 0) { if (errno == EINTR) continue; goto reconnect; }
        if (sel == 0) {
            mqtt_ping(mfd);
            if (time(NULL) - last_report >= 300) {
                st = screen_state();
                mqtt_pub(mfd, state_t, st == 1 ? "ON" : "OFF");
                last_report = time(NULL);
            }
            continue;
        }

        int pt = mqtt_read(mfd, pkt, sizeof(pkt), &pkt_rem);
        if (pt < 0) { fprintf(stderr, "Disconnected, reconnecting...\n"); sleep(3); goto reconnect; }

        if (pt == 3) {  /* PUBLISH */
            int tl = (pkt[0] << 8) | pkt[1];
            char topic[256] = {0}, payload[256] = {0};
            if (tl > 0 && tl < 256) {
                memcpy(topic, pkt+2, tl);
                int pl = pkt_rem - 2 - tl;  /* payload length from remaining */
                if (pl > 0 && pl < 256) memcpy(payload, pkt+2+tl, pl);
            }
            printf("MQTT: %s → %s\n", topic, payload); fflush(stdout);
            if (strcmp(topic, set_t) == 0) {
                if      (!strcasecmp(payload, "OFF"))    { screen_off();  mqtt_pub(mfd, state_t, "OFF"); }
                else if (!strcasecmp(payload, "ON"))     { screen_on();   mqtt_pub(mfd, state_t, "ON"); }
                else if (!strcasecmp(payload, "SAVER"))  { screen_saver(); mqtt_pub(mfd, state_t, "SAVER"); }
                else if (!strcasecmp(payload, "STATUS")) { st = screen_state(); mqtt_pub(mfd, state_t, st==1?"ON":"OFF"); }
                else if (!strcasecmp(payload, "TOGGLE")) {
                    st = screen_state();
                    if (st == 1) { screen_off(); mqtt_pub(mfd, state_t, "OFF"); }
                    else         { screen_on();  mqtt_pub(mfd, state_t, "ON"); }
                }
                else if (!strncasecmp(payload, "SOURCE:", 7)) {
                    launch_source(atoi(payload + 7));
                }
            }
        }
    }
    close(mfd);
    printf("Stopped.\n");
}

/* ── main ────────────────────────────────────────────────────────────────── */

int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("dispctl --on|--off|--toggle|--saver|--status\n"
               "dispctl --mqtt [broker] [topic_prefix]\n"
               "  Default broker: 192.168.178.218\n"
               "  Default prefix: tv/display\n");
        return 1;
    }
    const char *cmd = argv[1];
    if (!strcmp(cmd, "--status")) { printf("%s\n", screen_state()==1?"ON":"OFF"); return 0; }
    if (!strcmp(cmd, "--saver"))  { screen_saver(); return 0; }
    if (!strcmp(cmd, "--mqtt"))   { run_mqtt(argc>2?argv[2]:"192.168.178.218", argc>3?argv[3]:"tv/display"); return 0; }
    if (!strcmp(cmd, "--source") && argc > 2) { launch_source(atoi(argv[2])); return 0; }
    if      (!strcmp(cmd, "--off"))    screen_off();
    else if (!strcmp(cmd, "--on"))     screen_on();
    else if (!strcmp(cmd, "--toggle")) { int s=screen_state(); if(s==1) screen_off(); else screen_on(); }
    else { fprintf(stderr, "Verwendung: dispctl --on|--off|--toggle|--saver|--status|--source 1-3\n"
                           "            dispctl --mqtt [broker] [prefix]\n"); }
    return 0;
}
