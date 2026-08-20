#!/usr/bin/env bash
set -euo pipefail

cd /home/ron/linum

# 1. Update .gitignore for build binary artifacts & intermediate dumps
cat << 'GIT_EOF' >> .gitignore
*.o
*.elf
*.bin
target/
.builds/
/tmp/qemu_fiber_serial.log
GIT_EOF

# 2. Stage core bare-metal source files, build scripts, and multi-boot configs
git add boot64_unified.asm \
        kernel64_unified.c \
        linker64.ld \
        build_and_run_64.sh \
        capture_fiber_run.py \
        configure_multiboot_grub.sh \
        .gitignore

# 3. Commit this verified 64-bit Long Mode milestone
git commit -m "feat(kernel64): implement verified 64-bit long-mode 3-fiber exokernel with SSE2, eBPF JIT, and GRUB multiboot"

echo "============================================================"
echo " [✔] MILESTONE COMMITTED CLEANLY TO GIT REPOSITORY"
echo "============================================================"
git log -n 1 --stat
