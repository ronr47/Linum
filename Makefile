# Makefile - Bare-Metal Target Framework Compilation Build Tool
CC = arm-none-eabi-gcc
OBJCOPY = arm-none-eabi-objcopy
CFLAGS = -Wall -Wextra -O2 -nostdlib -nostartfiles -ffreestanding -mcpu=cortex-m4 -mthumb
LDFLAGS = -T linker_bare.ld

TARGET = custom_hardware_toolchain
OBJS = usb_core.o

all: $(TARGET).bin

$(TARGET).elf: $(OBJS)
	$(CC) $(CFLAGS) $(LDFLAGS) $(OBJS) -o $@

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

$(TARGET).bin: $(TARGET).elf
	$(OBJCOPY) -O binary $< $@

clean:
	rm -f *.o *.elf *.bin
