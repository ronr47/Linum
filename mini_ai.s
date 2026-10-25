.global _start

.section .rodata
    .align 3
msg_stable:
    .ascii "1\n"
    .equ MSG_STABLE_LEN, . - msg_stable

msg_anomaly:
    .ascii "0\n"
    .equ MSG_ANOMALY_LEN, . - msg_anomaly

.section .text
_start:
    // Sensory input: X0 = 5
    mov     x0, #5

    // Kernel parameters: W = 3, B = -4
    mov     x1, #3
    mov     x2, #-4

    // Linear projection: Y = (X * W) + B
    mul     x3, x0, x1
    adds    x3, x3, x2

    // Activation threshold check
    ble     .L_anomaly

.L_stable:
    adr     x1, msg_stable
    mov     x2, #MSG_STABLE_LEN
    b       .L_emit

.L_anomaly:
    adr     x1, msg_anomaly
    mov     x2, #MSG_ANOMALY_LEN

.L_emit:
    mov     x0, #1          // STDOUT_FILENO
    mov     x8, #64         // sys_write (Linux AArch64)
    svc     #0

    mov     x0, #0          // exit code 0
    mov     x8, #93         // sys_exit (Linux AArch64)
    svc     #0
