// ============================================================================
// LINUM UNIFIED COMPILER: BPF + NATIVE MULTI-TARGET BACKEND
// ============================================================================

use std::collections::{BTreeMap, HashMap, HashSet};
use std::fmt;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum TargetArch {
    X86_64,
    AArch64,
    BpfEL, // eBPF Little Endian for XDP/TC
}

pub struct TargetSpec {
    pub triple: &'static str,
    pub datalayout: &'static str,
    pub max_stack_bytes: usize,
    pub allow_heap_alloc: bool,
}

impl TargetArch {
    pub fn spec(&self) -> TargetSpec {
        match self {
            TargetArch::X86_64 => TargetSpec {
                triple: "x86_64-unknown-linux-gnu",
                datalayout: "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128",
                max_stack_bytes: 8 * 1024 * 1024,
                allow_heap_alloc: true,
            },
            TargetArch::AArch64 => TargetSpec {
                triple: "aarch64-unknown-linux-gnu",
                datalayout: "e-m:e-i8:8:32-i16:16:32-i64:64-i128:128-n32:64-S128",
                max_stack_bytes: 8 * 1024 * 1024,
                allow_heap_alloc: true,
            },
            TargetArch::BpfEL => TargetSpec {
                triple: "bpfel-unknown-none",
                datalayout: "e-m:e-p:64:64-i64:64-i128:128-n32:64-S128",
                max_stack_bytes: 512, // Strict eBPF kernel verifier stack limit
                allow_heap_alloc: false,
            },
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Type {
    I32,
    I64,
    F64,
    Bool,
    Ptr,
    Void,
}

impl fmt::Display for Type {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Type::I32 => write!(f, "i32"),
            Type::I64 => write!(f, "i64"),
            Type::F64 => write!(f, "double"),
            Type::Bool => write!(f, "i1"),
            Type::Ptr => write!(f, "ptr"),
            Type::Void => write!(f, "void"),
        }
    }
}

#[derive(Debug, Clone)]
pub struct FunctionAnnotation {
    pub section: Option<String>,
    pub align: Option<usize>,
}

#[derive(Debug, Clone)]
pub struct Function {
    pub name: String,
    pub params: Vec<(String, Type)>,
    pub ret_type: Type,
    pub annotations: FunctionAnnotation,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct BlockId(pub usize);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct ValueId(pub usize);

impl fmt::Display for ValueId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "%v{}", self.0)
    }
}

#[derive(Debug, Clone)]
pub enum Instruction {
    ConstInt { dest: ValueId, val: i64, ty: Type },
    BpfHelperCall { dest: Option<ValueId>, helper_id: u32, helper_name: &'static str },
    MemoryLoad { dest: ValueId, ptr: ValueId, ty: Type },
    MemoryStore { ptr: ValueId, val: ValueId },
    Binary { dest: ValueId, op: &'static str, lhs: ValueId, rhs: ValueId, ty: Type },
    Phi { dest: ValueId, incoming: Vec<(BlockId, ValueId)>, ty: Type },
}

#[derive(Debug, Clone)]
pub enum Terminator {
    Branch { cond: ValueId, then_block: BlockId, else_block: BlockId },
    Jump(BlockId),
    Return(Option<ValueId>),
}

#[derive(Debug, Clone)]
pub struct BasicBlock {
    pub id: BlockId,
    pub instructions: Vec<Instruction>,
    pub terminator: Option<Terminator>,
}

pub struct FunctionCFG {
    pub name: String,
    pub params: Vec<(String, Type, ValueId)>,
    pub ret_type: Type,
    pub annotations: FunctionAnnotation,
    pub blocks: BTreeMap<BlockId, BasicBlock>,
}

// ----------------------------------------------------------------------------
// Multi-Target Unified LLVM / BPF Code Generator
// ----------------------------------------------------------------------------

pub struct UnifiedBackend {
    pub target: TargetArch,
}

impl UnifiedBackend {
    pub fn new(target: TargetArch) -> Self {
        Self { target }
    }

    pub fn emit_module(&self, funcs: &[FunctionCFG]) -> Result<String, String> {
        let spec = self.target.spec();
        let mut out = String::new();

        out.push_str(&format!("; ModuleID = 'LinumUnifiedModule'\n"));
        out.push_str(&format!("source_filename = \"unified_pipeline.ln\"\n"));
        out.push_str(&format!("target datalayout = \"{}\"\n", spec.datalayout));
        out.push_str(&format!("target triple = \"{}\"\n\n", spec.triple));

        if self.target == TargetArch::BpfEL {
            // Emit BPF Map Declarations in standard ELF section
            out.push_str("; --- eBPF Maps Definitions ---\n");
            out.push_str("@PACKET_RING = dso_local global [24 x i8] zeroinitializer, section \".maps\", align 4\n\n");
        }

        for func in funcs {
            self.validate_target_invariants(func, &spec)?;
            out.push_str(&self.emit_function(func));
            out.push('\n');
        }

        out.push_str("attributes #0 = { nounwind }\n");
        out.push_str("!llvm.module.flags = !{!0}\n");
        out.push_str("!0 = !{i32 1, !\"wchar_size\", i32 4}\n");

        Ok(out)
    }

    fn validate_target_invariants(&self, func: &FunctionCFG, spec: &TargetSpec) -> Result<(), String> {
        if self.target == TargetArch::BpfEL {
            // Strict Invariant Check 1: eBPF requires explicit sections (e.g., xdp, tc)
            if func.annotations.section.is_none() {
                return Err(format!(
                    "eBPF Verifier Error: Function '{}' missing @section attribute.",
                    func.name
                ));
            }
        }
        Ok(())
    }

    fn emit_function(&self, func: &FunctionCFG) -> String {
        let mut out = String::new();
        let params_fmt = func.params.iter()
            .map(|(_, ty, val)| format!("{} %v{}", ty, val.0))
            .collect::<Vec<_>>()
            .join(", ");

        let section_attr = if let Some(sec) = &func.annotations.section {
            format!(" section \"{}\"", sec)
        } else {
            String::new()
        };

        let align_attr = if let Some(align) = func.annotations.align {
            format!(" align {}", align)
        } else {
            String::new()
        };

        out.push_str(&format!(
            "define {} @{}({}) #0{}{} {{\n",
            func.ret_type, func.name, params_fmt, section_attr, align_attr
        ));

        for (&id, block) in &func.blocks {
            out.push_str(&format!("bb{}:\n", id.0));

            for inst in &block.instructions {
                match inst {
                    Instruction::ConstInt { dest, val, ty } => {
                        out.push_str(&format!("  {} = add {} 0, {}\n", dest, ty, val));
                    }
                    Instruction::BpfHelperCall { dest, helper_id, helper_name } => {
                        out.push_str(&format!(
                            "  ; BPF Helper Call: {} (ID: {})\n",
                            helper_name, helper_id
                        ));
                        if let Some(d) = dest {
                            out.push_str(&format!(
                                "  {} = call i64 inttoptr (i64 {} to ptr)()\n",
                                d, helper_id
                            ));
                        } else {
                            out.push_str(&format!(
                                "  call void inttoptr (i64 {} to ptr)()\n",
                                helper_id
                            ));
                        }
                    }
                    Instruction::MemoryLoad { dest, ptr, ty } => {
                        out.push_str(&format!("  {} = load {}, ptr {}\n", dest, ty, ptr));
                    }
                    Instruction::MemoryStore { ptr, val } => {
                        out.push_str(&format!("  store i64 {}, ptr {}\n", val, ptr));
                    }
                    Instruction::Binary { dest, op, lhs, rhs, ty } => {
                        out.push_str(&format!("  {} = {} {} {}, {}\n", dest, op, ty, lhs, rhs));
                    }
                    Instruction::Phi { dest, incoming, ty } => {
                        let inc_str = incoming.iter()
                            .map(|(b, v)| format!("[ {}, %bb{} ]", v, b.0))
                            .collect::<Vec<_>>()
                            .join(", ");
                        out.push_str(&format!("  {} = phi {} {}\n", dest, ty, inc_str));
                    }
                }
            }

            if let Some(term) = &block.terminator {
                match term {
                    Terminator::Jump(to) => out.push_str(&format!("  br label %bb{}\n", to.0)),
                    Terminator::Branch { cond, then_block, else_block } => {
                        out.push_str(&format!(
                            "  br i1 {}, label %bb{}, label %bb{}\n",
                            cond, then_block.0, else_block.0
                        ));
                    }
                    Terminator::Return(Some(v)) => out.push_str(&format!("  ret {} {}\n", func.ret_type, v)),
                    Terminator::Return(None) => out.push_str("  ret void\n"),
                }
            }
        }

        out.push_str("}\n");
        out
    }
}

// ----------------------------------------------------------------------------
// Compiler Driver & Verification Test Harness
// ----------------------------------------------------------------------------

fn main() {
    println!("============================================================");
    println!(" LINUM COMPILER CORE: MULTI-TARGET BPF/NATIVE ENGINE        ");
    println!("============================================================\n");

    // 1. Build In-Kernel XDP Hook CFG
    let mut bpf_blocks = BTreeMap::new();
    let mut entry_block = BasicBlock {
        id: BlockId(0),
        instructions: vec![
            Instruction::ConstInt { dest: ValueId(1), val: 2, ty: Type::I32 },
            Instruction::BpfHelperCall {
                dest: Some(ValueId(2)),
                helper_id: 129, // BPF_FUNC_ktime_get_ns
                helper_name: "bpf_ktime_get_ns",
            },
        ],
        terminator: Some(Terminator::Return(Some(ValueId(1)))),
    };
    bpf_blocks.insert(BlockId(0), entry_block);

    let xdp_func = FunctionCFG {
        name: "xdp_ingress_filter".to_string(),
        params: vec![("ctx".to_string(), Type::Ptr, ValueId(0))],
        ret_type: Type::I32,
        annotations: FunctionAnnotation {
            section: Some("xdp".to_string()),
            align: Some(64),
        },
        blocks: bpf_blocks,
    };

    // 2. Emit Verified eBPF Target LLVM IR
    let bpf_backend = UnifiedBackend::new(TargetArch::BpfEL);
    let bpf_ir = bpf_backend.emit_module(&[xdp_func]).expect("BPF Lowering Failed");

    println!("; --- [TARGET: bpfel-unknown-none (In-Kernel XDP Hook)] ---");
    println!("{}", bpf_ir);

    // 3. Build User-Space Sequencer CFG
    let mut native_blocks = BTreeMap::new();
    let native_entry = BasicBlock {
        id: BlockId(0),
        instructions: vec![
            Instruction::ConstInt { dest: ValueId(2), val: 0, ty: Type::I64 },
        ],
        terminator: Some(Terminator::Return(Some(ValueId(2)))),
    };
    native_blocks.insert(BlockId(0), native_entry);

    let seq_func = FunctionCFG {
        name: "sequencer_worker".to_string(),
        params: vec![
            ("ring".to_string(), Type::Ptr, ValueId(0)),
            ("journal".to_string(), Type::Ptr, ValueId(1)),
        ],
        ret_type: Type::I64,
        annotations: FunctionAnnotation {
            section: None,
            align: Some(64),
        },
        blocks: native_blocks,
    };

    // 4. Emit Native Host Target LLVM IR
    let native_backend = UnifiedBackend::new(TargetArch::X86_64);
    let native_ir = native_backend.emit_module(&[seq_func]).expect("Native Lowering Failed");

    println!("; --- [TARGET: x86_64-unknown-linux-gnu (User-Space Sequencer)] ---");
    println!("{}", native_ir);
}
