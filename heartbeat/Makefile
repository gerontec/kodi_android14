CC_ARM   = arm-linux-gnueabihf-gcc
CC_NATIVE= gcc
CFLAGS   = -O2 -Wall -Wextra
LDFLAGS  = -static

TARGET   = heartbeat

.PHONY: arm native clean install

arm: $(TARGET).arm

native: $(TARGET)

$(TARGET).arm: heartbeat.c
	$(CC_ARM) $(CFLAGS) $(LDFLAGS) -o $@ $<
	@echo "Built ARM binary: $@"
	@file $@

$(TARGET): heartbeat.c
	$(CC_NATIVE) $(CFLAGS) -o $@ $<
	@echo "Built native binary: $@"

install: $(TARGET).arm
	adb -s 192.168.178.43:5555 push $(TARGET).arm /data/local/tmp/heartbeat
	adb -s 192.168.178.43:5555 shell chmod +x /data/local/tmp/heartbeat
	@echo "Installed on TV: /data/local/tmp/heartbeat"

clean:
	rm -f $(TARGET) $(TARGET).arm
