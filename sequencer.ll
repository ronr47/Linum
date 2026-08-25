; ModuleID = 'sequencer_core [Native Host Sequencer]'
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-unknown-linux-gnu"

define i64 @sequencer_worker(ptr %ring, ptr %journal) #0 align 64 {
bb0:
  ret i64 0
}

attributes #0 = { nounwind }
