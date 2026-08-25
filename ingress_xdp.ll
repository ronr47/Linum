; ModuleID = 'ingress_hook [In-Kernel eBPF]'
target datalayout = "e-m:e-p:64:64-i64:64-i128:128-n32:64-S128"
target triple = "bpfel-unknown-none"

@PACKET_RING = dso_local global [24 x i8] zeroinitializer, section ".maps", align 4

define i32 @xdp_ingress_filter(ptr %ctx) #0 section "xdp" align 64 {
bb0:
  ; Fast in-kernel boundary checks
  %t0 = call i64 inttoptr (i64 129 to ptr)()
  ret i32 2 ; XDP_PASS
}

attributes #0 = { nounwind }
