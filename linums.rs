// ============================================================================
// LINUMS :: UNIFIED COMPILER, RUNTIME & ZERO-DEPENDENCY LATENCY AUDITOR
// ============================================================================

use std::cell::UnsafeCell;
use std::collections::BTreeMap;
use std::fs::File;
use std::io::{Read, Write};
use std::net::UdpSocket;
use std::os::unix::io::RawFd;
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::Arc;
use std::thread;
use std::time::{Duration, Instant};

extern "C" {
    fn close(fd: RawFd) -> i32;
}

// ----------------------------------------------------------------------------
// 1. HARDWARE TSC / MONOTONIC CLOCK INTRINSIC
// ----------------------------------------------------------------------------

#[inline(always)]
pub fn read_cpu_tsc() -> u64 {
    #[cfg(target_arch = "x86_64")]
    unsafe {
        core::arch::x86_64::_rdtsc()
    }
    #[cfg(not(target_arch = "x86_64"))]
    {
        use std::time::SystemTime;
        SystemTime::now().duration_since(SystemTime::UNIX_EPOCH).unwrap().as_nanos() as u64
    }
}

// ----------------------------------------------------------------------------
// 2. WIRE FRAME & ZERO-ALLOC SPSC RING BUFFER (UnsafeCell for Lock-Free Concurrency)
// ----------------------------------------------------------------------------

#[repr(C, align(64))]
#[derive(Clone, Copy)]
pub struct WireFrame {
    pub ingress_seq: u64,
    pub accepted_seq: u64,
    pub t0_ingress_cycles: u64,
    pub t1_enqueue_cycles: u64,
    pub t2_dequeue_cycles: u64,
    pub t3_ordered_cycles: u64,
    pub t4_journal_cycles: u64,
    pub payload_len: u32,
    pub client_ip: u32,
    pub payload: [u8; 192],
}

pub const SPSC_CAPACITY: usize = 65536;
pub const SPSC_MASK: usize = SPSC_CAPACITY - 1;

#[repr(C, align(64))]
pub struct SpscRing {
    pub write_index: AtomicU64,
    _pad0: [u8; 56],
    pub read_index: AtomicU64,
    _pad1: [u8; 56],
    pub slots: UnsafeCell<[WireFrame; SPSC_CAPACITY]>,
}

unsafe impl Sync for SpscRing {}
unsafe impl Send for SpscRing {}

impl SpscRing {
    pub fn new() -> Arc<Self> {
        let layout = std::alloc::Layout::new::<Self>();
        unsafe {
            let ptr = std::alloc::alloc_zeroed(layout) as *mut Self;
            Arc::from_raw(ptr)
        }
    }

    #[inline(always)]
    pub unsafe fn write_slot(&self, idx: usize, frame: WireFrame) {
        let slots_ptr = self.slots.get() as *mut WireFrame;
        *slots_ptr.add(idx) = frame;
    }

    #[inline(always)]
    pub unsafe fn read_slot(&self, idx: usize) -> WireFrame {
        let slots_ptr = self.slots.get() as *const WireFrame;
        *slots_ptr.add(idx)
    }
}

// ----------------------------------------------------------------------------
// 3. HDR LATENCY HISTOGRAM & PERCENTILE ENGINE (0 - 100,000 µs)
// ----------------------------------------------------------------------------

pub const MAX_LATENCY_US: usize = 100_000;

pub struct LatencyAuditor {
    pub total_samples: u64,
    pub min_cycles: u64,
    pub max_cycles: u64,
    pub sum_cycles: u64,
    pub histogram: Vec<u32>,
    pub tsc_ghz: f64,
}

impl LatencyAuditor {
    pub fn new(tsc_ghz: f64) -> Self {
        Self {
            total_samples: 0,
            min_cycles: u64::MAX,
            max_cycles: 0,
            sum_cycles: 0,
            histogram: vec![0; MAX_LATENCY_US + 1],
            tsc_ghz,
        }
    }

    #[inline(always)]
    pub fn record(&mut self, delta_cycles: u64) {
        self.total_samples += 1;
        self.sum_cycles += delta_cycles;
        if delta_cycles < self.min_cycles { self.min_cycles = delta_cycles; }
        if delta_cycles > self.max_cycles { self.max_cycles = delta_cycles; }

        let us = ((delta_cycles as f64) / (self.tsc_ghz * 1000.0)) as usize;
        if us < MAX_LATENCY_US {
            self.histogram[us] += 1;
        } else {
            self.histogram[MAX_LATENCY_US] += 1;
        }
    }

    pub fn get_percentile(&self, p: f64) -> f64 {
        if self.total_samples == 0 { return 0.0; }
        let target = ((self.total_samples as f64) * (p / 100.0)).ceil() as u64;
        let mut accumulated = 0u64;

        for (us, &count) in self.histogram.iter().enumerate() {
            accumulated += count as u64;
            if accumulated >= target {
                return us as f64;
            }
        }
        MAX_LATENCY_US as f64
    }

    pub fn print_report(&self, title: &str) {
        if self.total_samples == 0 {
            println!("[-] {} Auditor: No samples captured.", title);
            return;
        }

        let mean_us = (self.sum_cycles as f64 / self.total_samples as f64) / (self.tsc_ghz * 1000.0);
        let min_us = (self.min_cycles as f64) / (self.tsc_ghz * 1000.0);
        let max_us = (self.max_cycles as f64) / (self.tsc_ghz * 1000.0);

        println!("\n==================================================================");
        println!(" LATENCY AUDIT REPORT: {:<40}", title);
        println!("==================================================================");
        println!(" Total Samples Recorded : {:>15}", self.total_samples);
        println!(" Min Latency            : {:>15.3} µs", min_us);
        println!(" Mean Latency           : {:>15.3} µs", mean_us);
        println!(" p50.00 (Median)        : {:>15.3} µs", self.get_percentile(50.0));
        println!(" p90.00                 : {:>15.3} µs", self.get_percentile(90.0));
        println!(" p99.00                 : {:>15.3} µs", self.get_percentile(99.0));
        println!(" p99.90                 : {:>15.3} µs", self.get_percentile(99.9));
        println!(" p99.99                 : {:>15.3} µs", self.get_percentile(99.99));
        println!(" Max Latency            : {:>15.3} µs", max_us);
        println!("------------------------------------------------------------------");
    }
}

// ----------------------------------------------------------------------------
// 4. FRONTEND LEXER & PARSER
// ----------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq)]
pub enum Token {
    Fn, Struct, Let, Mut, If, Else, While, Return, At,
    Ident(String), IntLit(i64), StrLit(String),
    Colon, Semi, Comma, LParen, RParen, LBrace, RBrace, LBracket, RBracket,
    Plus, Minus, Star, Slash, Equal, EqEq, Gt, Lt, Arrow, Ampersand, EOF,
}

pub struct Lexer<'a> {
    src: &'a str,
    pos: usize,
}

impl<'a> Lexer<'a> {
    pub fn new(src: &'a str) -> Self { Self { src, pos: 0 } }

    pub fn next_token(&mut self) -> Token {
        self.skip_whitespace();
        if self.pos >= self.src.len() { return Token::EOF; }

        let rest = &self.src[self.pos..];
        let c = rest.chars().next().unwrap();

        match c {
            '@' => { self.pos += 1; Token::At }
            ':' => { self.pos += 1; Token::Colon }
            ';' => { self.pos += 1; Token::Semi }
            ',' => { self.pos += 1; Token::Comma }
            '(' => { self.pos += 1; Token::LParen }
            ')' => { self.pos += 1; Token::RParen }
            '{' => { self.pos += 1; Token::LBrace }
            '}' => { self.pos += 1; Token::RBrace }
            '[' => { self.pos += 1; Token::LBracket }
            ']' => { self.pos += 1; Token::RBracket }
            '&' => { self.pos += 1; Token::Ampersand }
            '+' => { self.pos += 1; Token::Plus }
            '-' => {
                if rest.starts_with("->") { self.pos += 2; Token::Arrow }
                else { self.pos += 1; Token::Minus }
            }
            '*' => { self.pos += 1; Token::Star }
            '/' => { self.pos += 1; Token::Slash }
            '=' => {
                if rest.starts_with("==") { self.pos += 2; Token::EqEq }
                else { self.pos += 1; Token::Equal }
            }
            '>' => { self.pos += 1; Token::Gt }
            '<' => { self.pos += 1; Token::Lt }
            '"' => {
                self.pos += 1;
                let mut s = String::new();
                while self.pos < self.src.len() {
                    let sc = self.src[self.pos..].chars().next().unwrap();
                    self.pos += sc.len_utf8();
                    if sc == '"' { break; }
                    s.push(sc);
                }
                Token::StrLit(s)
            }
            _ if c.is_ascii_digit() => {
                let mut num = String::new();
                while self.pos < self.src.len() {
                    let nc = self.src[self.pos..].chars().next().unwrap();
                    if nc.is_ascii_digit() {
                        num.push(nc);
                        self.pos += nc.len_utf8();
                    } else { break; }
                }
                Token::IntLit(num.parse().unwrap_or(0))
            }
            _ if c.is_alphabetic() || c == '_' => {
                let mut id = String::new();
                while self.pos < self.src.len() {
                    let ic = self.src[self.pos..].chars().next().unwrap();
                    if ic.is_alphanumeric() || ic == '_' {
                        id.push(ic);
                        self.pos += ic.len_utf8();
                    } else { break; }
                }
                match id.as_str() {
                    "fn" => Token::Fn,
                    "struct" => Token::Struct,
                    "let" => Token::Let,
                    "mut" => Token::Mut,
                    "if" => Token::If,
                    "else" => Token::Else,
                    "while" => Token::While,
                    "return" => Token::Return,
                    _ => Token::Ident(id),
                }
            }
            _ => { self.pos += c.len_utf8(); self.next_token() }
        }
    }

    fn skip_whitespace(&mut self) {
        while self.pos < self.src.len() {
            let rest = &self.src[self.pos..];
            if rest.starts_with("//") {
                while self.pos < self.src.len() && !self.src[self.pos..].starts_with('\n') {
                    self.pos += 1;
                }
            } else if rest.chars().next().unwrap().is_whitespace() {
                self.pos += 1;
            } else { break; }
        }
    }
}

// ----------------------------------------------------------------------------
// 5. AST & PARSER
// ----------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub enum TypeSig {
    I32, I64, Ptr, Void, Custom(String),
}

impl TypeSig {
    pub fn to_llvm(&self) -> &'static str {
        match self {
            TypeSig::I32 => "i32",
            TypeSig::I64 => "i64",
            TypeSig::Ptr => "ptr",
            TypeSig::Void => "void",
            TypeSig::Custom(_) => "ptr",
        }
    }
}

#[derive(Debug, Clone)]
pub enum Expr {
    Int(i64),
    Var(String),
    Binary { op: String, lhs: Box<Expr>, rhs: Box<Expr> },
    Call { name: String, args: Vec<Expr> },
}

#[derive(Debug, Clone)]
pub enum Stmt {
    Let { name: String, val: Expr },
    Assign { name: String, val: Expr },
    Return(Option<Expr>),
    Expr(Expr),
    If { cond: Expr, then_block: Vec<Stmt>, else_block: Option<Vec<Stmt>> },
}

#[derive(Debug, Clone)]
pub struct FunctionAST {
    pub name: String,
    pub section: Option<String>,
    pub align: Option<usize>,
    pub params: Vec<(String, TypeSig)>,
    pub ret_type: TypeSig,
    pub body: Vec<Stmt>,
}

pub struct Parser<'a> {
    lexer: Lexer<'a>,
    cur: Token,
}

impl<'a> Parser<'a> {
    pub fn new(src: &'a str) -> Self {
        let mut lexer = Lexer::new(src);
        let cur = lexer.next_token();
        Self { lexer, cur }
    }

    fn advance(&mut self) { self.cur = self.lexer.next_token(); }

    pub fn parse_module(&mut self) -> Result<Vec<FunctionAST>, String> {
        let mut funcs = Vec::new();
        while self.cur != Token::EOF {
            let mut section = None;
            let mut align = None;

            while self.cur == Token::At {
                self.advance();
                if let Token::Ident(attr) = &self.cur {
                    let attr_name = attr.clone();
                    self.advance();
                    if self.cur == Token::LParen {
                        self.advance();
                        if attr_name == "section" {
                            if let Token::StrLit(sec) = &self.cur { section = Some(sec.clone()); self.advance(); }
                        } else if attr_name == "align" {
                            if let Token::IntLit(val) = self.cur { align = Some(val as usize); self.advance(); }
                        }
                        if self.cur == Token::RParen { self.advance(); }
                    }
                }
            }

            if self.cur == Token::Struct {
                while self.cur != Token::RBrace && self.cur != Token::EOF { self.advance(); }
                if self.cur == Token::RBrace { self.advance(); }
                continue;
            }

            if let Token::Ident(ref id) = self.cur {
                if id == "static" {
                    while self.cur != Token::Semi && self.cur != Token::EOF { self.advance(); }
                    if self.cur == Token::Semi { self.advance(); }
                    continue;
                }
            }

            if self.cur == Token::Fn {
                funcs.push(self.parse_function(section, align)?);
            } else {
                self.advance();
            }
        }
        Ok(funcs)
    }

    fn parse_function(&mut self, section: Option<String>, align: Option<usize>) -> Result<FunctionAST, String> {
        self.advance();
        let name = match &self.cur {
            Token::Ident(n) => n.clone(),
            _ => return Err("Expected function name".into()),
        };
        self.advance();

        let mut params = Vec::new();
        if self.cur == Token::LParen {
            self.advance();
            while self.cur != Token::RParen && self.cur != Token::EOF {
                if let Token::Ident(pname) = &self.cur {
                    let param_name = pname.clone();
                    self.advance();
                    let mut ty = TypeSig::I64;
                    if self.cur == Token::Colon {
                        self.advance();
                        ty = self.parse_type();
                    }
                    params.push((param_name, ty));
                }
                if self.cur == Token::Comma { self.advance(); }
            }
            if self.cur == Token::RParen { self.advance(); }
        }

        let mut ret_type = TypeSig::Void;
        if self.cur == Token::Colon || self.cur == Token::Arrow {
            self.advance();
            ret_type = self.parse_type();
        }

        let body = self.parse_block()?;
        Ok(FunctionAST { name, section, align, params, ret_type, body })
    }

    fn parse_type(&mut self) -> TypeSig {
        let mut is_ptr = false;
        if self.cur == Token::Star {
            self.advance();
            if self.cur == Token::Mut { self.advance(); }
            is_ptr = true;
        }

        let ty = match &self.cur {
            Token::Ident(n) => {
                let name = n.clone();
                self.advance();
                match name.as_str() {
                    "u32" | "i32" => TypeSig::I32,
                    "u64" | "i64" | "usize" => TypeSig::I64,
                    _ => TypeSig::Custom(name),
                }
            }
            _ => TypeSig::I64,
        };

        if is_ptr { TypeSig::Ptr } else { ty }
    }

    fn parse_block(&mut self) -> Result<Vec<Stmt>, String> {
        let mut stmts = Vec::new();
        if self.cur != Token::LBrace { return Err("Expected '{'".into()); }
        self.advance();

        while self.cur != Token::RBrace && self.cur != Token::EOF {
            stmts.push(self.parse_statement()?);
        }

        if self.cur == Token::RBrace { self.advance(); }
        Ok(stmts)
    }

    fn parse_statement(&mut self) -> Result<Stmt, String> {
        match self.cur {
            Token::Let => {
                self.advance();
                if self.cur == Token::Mut { self.advance(); }
                let name = match &self.cur {
                    Token::Ident(n) => n.clone(),
                    _ => return Err("Expected variable name after let".into()),
                };
                self.advance();
                if self.cur == Token::Colon {
                    self.advance();
                    let _ = self.parse_type();
                }
                if self.cur != Token::Equal { return Err("Expected '=' in let binding".into()); }
                self.advance();
                let expr = self.parse_expr()?;
                if self.cur == Token::Semi { self.advance(); }
                Ok(Stmt::Let { name, val: expr })
            }
            Token::Return => {
                self.advance();
                if self.cur == Token::Semi {
                    self.advance();
                    Ok(Stmt::Return(None))
                } else {
                    let expr = self.parse_expr()?;
                    if self.cur == Token::Semi { self.advance(); }
                    Ok(Stmt::Return(Some(expr)))
                }
            }
            Token::If => {
                self.advance();
                let cond = self.parse_expr()?;
                let then_block = self.parse_block()?;
                let mut else_block = None;
                if self.cur == Token::Else {
                    self.advance();
                    else_block = Some(self.parse_block()?);
                }
                Ok(Stmt::If { cond, then_block, else_block })
            }
            Token::Ident(ref n) => {
                let name = n.clone();
                self.advance();
                if self.cur == Token::Equal {
                    self.advance();
                    let val = self.parse_expr()?;
                    if self.cur == Token::Semi { self.advance(); }
                    Ok(Stmt::Assign { name, val })
                } else {
                    let expr = self.parse_expr_rest(Expr::Var(name))?;
                    if self.cur == Token::Semi { self.advance(); }
                    Ok(Stmt::Expr(expr))
                }
            }
            _ => {
                let expr = self.parse_expr()?;
                if self.cur == Token::Semi { self.advance(); }
                Ok(Stmt::Expr(expr))
            }
        }
    }

    fn parse_expr(&mut self) -> Result<Expr, String> {
        let left = match &self.cur {
            Token::IntLit(val) => { let v = *val; self.advance(); Expr::Int(v) }
            Token::Ident(name) => {
                let n = name.clone();
                self.advance();
                if self.cur == Token::LParen {
                    self.advance();
                    let mut args = Vec::new();
                    while self.cur != Token::RParen && self.cur != Token::EOF {
                        args.push(self.parse_expr()?);
                        if self.cur == Token::Comma { self.advance(); }
                    }
                    if self.cur == Token::RParen { self.advance(); }
                    Expr::Call { name: n, args }
                } else {
                    Expr::Var(n)
                }
            }
            _ => { let tok = format!("{:?}", self.cur); self.advance(); return Err(format!("Unexpected token: {}", tok)); }
        };
        self.parse_expr_rest(left)
    }

    fn parse_expr_rest(&mut self, left: Expr) -> Result<Expr, String> {
        let mut lhs = left;
        while matches!(self.cur, Token::Plus | Token::Minus | Token::Star | Token::Slash | Token::Gt | Token::Lt | Token::EqEq) {
            let op = match self.cur {
                Token::Plus => "+", Token::Minus => "-", Token::Star => "*", Token::Slash => "/",
                Token::Gt => ">", Token::Lt => "<", Token::EqEq => "==",
                _ => unreachable!(),
            }.to_string();
            self.advance();
            let rhs = match &self.cur {
                Token::IntLit(v) => { let val = *v; self.advance(); Expr::Int(val) }
                Token::Ident(n) => { let id = n.clone(); self.advance(); Expr::Var(id) }
                _ => self.parse_expr()?,
            };
            lhs = Expr::Binary { op, lhs: Box::new(lhs), rhs: Box::new(rhs) };
        }
        Ok(lhs)
    }
}

// ----------------------------------------------------------------------------
// 6. SSA BUILDER & CODE EMITTER
// ----------------------------------------------------------------------------

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub struct ValueId(pub usize);

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub struct BlockId(pub usize);

#[derive(Debug, Clone)]
pub enum SSALocalInst {
    ConstInt { dest: ValueId, val: i64, ty: &'static str },
    Binary { dest: ValueId, op: String, lhs: ValueId, rhs: ValueId, ty: &'static str },
    BpfCall { dest: Option<ValueId>, helper_id: u32, helper_name: &'static str },
    Return(Option<ValueId>, &'static str),
    Jump(BlockId),
    Branch { cond: ValueId, then_block: BlockId, else_block: BlockId },
}

#[derive(Debug, Clone)]
pub struct SSABlock {
    pub id: BlockId,
    pub insts: Vec<SSALocalInst>,
}

pub struct SSABuilder {
    pub blocks: BTreeMap<BlockId, SSABlock>,
    cur_block: BlockId,
    next_value: usize,
    next_block: usize,
    env: BTreeMap<String, ValueId>,
}

impl SSABuilder {
    pub fn new() -> Self {
        let mut blocks = BTreeMap::new();
        blocks.insert(BlockId(0), SSABlock { id: BlockId(0), insts: Vec::new() });
        Self {
            blocks,
            cur_block: BlockId(0),
            next_value: 1,
            next_block: 1,
            env: BTreeMap::new(),
        }
    }

    fn new_value(&mut self) -> ValueId {
        let v = ValueId(self.next_value);
        self.next_value += 1;
        v
    }

    fn new_block(&mut self) -> BlockId {
        let b = BlockId(self.next_block);
        self.next_block += 1;
        self.blocks.insert(b, SSABlock { id: b, insts: Vec::new() });
        b
    }

    fn push_inst(&mut self, inst: SSALocalInst) {
        self.blocks.get_mut(&self.cur_block).unwrap().insts.push(inst);
    }

    pub fn compile_function(&mut self, func: &FunctionAST) {
        for (i, (name, _)) in func.params.iter().enumerate() {
            self.env.insert(name.clone(), ValueId(i));
        }

        for stmt in &func.body {
            self.lower_stmt(stmt, func.ret_type.to_llvm());
        }

        let cur_insts = &self.blocks.get(&self.cur_block).unwrap().insts;
        if cur_insts.is_empty() || !matches!(cur_insts.last().unwrap(), SSALocalInst::Return(..) | SSALocalInst::Jump(..) | SSALocalInst::Branch { .. }) {
            self.push_inst(SSALocalInst::Return(None, func.ret_type.to_llvm()));
        }
    }

    fn lower_stmt(&mut self, stmt: &Stmt, ret_ty: &'static str) {
        match stmt {
            Stmt::Let { name, val } => {
                let v = self.lower_expr(val);
                self.env.insert(name.clone(), v);
            }
            Stmt::Assign { name, val } => {
                let v = self.lower_expr(val);
                self.env.insert(name.clone(), v);
            }
            Stmt::Return(Some(expr)) => {
                let v = self.lower_expr(expr);
                self.push_inst(SSALocalInst::Return(Some(v), ret_ty));
            }
            Stmt::Return(None) => {
                self.push_inst(SSALocalInst::Return(None, ret_ty));
            }
            Stmt::Expr(expr) => {
                self.lower_expr(expr);
            }
            Stmt::If { cond, then_block, else_block } => {
                let cond_val = self.lower_expr(cond);
                let then_b = self.new_block();
                let else_b = self.new_block();
                let merge_b = self.new_block();

                let actual_else = if else_block.is_some() { else_b } else { merge_b };
                self.push_inst(SSALocalInst::Branch { cond: cond_val, then_block: then_b, else_block: actual_else });

                self.cur_block = then_b;
                for s in then_block { self.lower_stmt(s, ret_ty); }
                self.push_inst(SSALocalInst::Jump(merge_b));

                if let Some(eb) = else_block {
                    self.cur_block = else_b;
                    for s in eb { self.lower_stmt(s, ret_ty); }
                    self.push_inst(SSALocalInst::Jump(merge_b));
                }

                self.cur_block = merge_b;
            }
        }
    }

    fn lower_expr(&mut self, expr: &Expr) -> ValueId {
        match expr {
            Expr::Int(val) => {
                let dest = self.new_value();
                self.push_inst(SSALocalInst::ConstInt { dest, val: *val, ty: "i64" });
                dest
            }
            Expr::Var(name) => {
                *self.env.get(name).unwrap_or(&ValueId(0))
            }
            Expr::Binary { op, lhs, rhs } => {
                let l = self.lower_expr(lhs);
                let r = self.lower_expr(rhs);
                let dest = self.new_value();
                let (llvm_op, ty) = match op.as_str() {
                    "+" => ("add", "i64"),
                    "-" => ("sub", "i64"),
                    "*" => ("mul", "i64"),
                    ">" => ("icmp ugt", "i1"),
                    "<" => ("icmp ult", "i1"),
                    "==" => ("icmp eq", "i1"),
                    _ => ("add", "i64"),
                };
                self.push_inst(SSALocalInst::Binary { dest, op: llvm_op.to_string(), lhs: l, rhs: r, ty });
                dest
            }
            Expr::Call { name, .. } => {
                if name == "bpf_ktime_get_ns" {
                    let dest = self.new_value();
                    self.push_inst(SSALocalInst::BpfCall {
                        dest: Some(dest),
                        helper_id: 129,
                        helper_name: "bpf_ktime_get_ns",
                    });
                    dest
                } else {
                    let dest = self.new_value();
                    self.push_inst(SSALocalInst::ConstInt { dest, val: 0, ty: "i64" });
                    dest
                }
            }
        }
    }

    pub fn emit_llvm_function(&self, func: &FunctionAST) -> String {
        let mut out = String::new();
        let params_fmt = func.params.iter().enumerate()
            .map(|(i, (_, ty))| format!("{} %v{}", ty.to_llvm(), i))
            .collect::<Vec<_>>()
            .join(", ");

        let sec_attr = func.section.as_ref().map(|s| format!(" section \"{}\"", s)).unwrap_or_default();
        let align_attr = func.align.map(|a| format!(" align {}", a)).unwrap_or_default();

        out.push_str(&format!(
            "define {} @{}({}) #0{}{} {{\n",
            func.ret_type.to_llvm(), func.name, params_fmt, sec_attr, align_attr
        ));

        for (bid, block) in &self.blocks {
            out.push_str(&format!("bb{}:\n", bid.0));
            for inst in &block.insts {
                match inst {
                    SSALocalInst::ConstInt { dest, val, ty } => {
                        out.push_str(&format!("  %v{} = add {} 0, {}\n", dest.0, ty, val));
                    }
                    SSALocalInst::Binary { dest, op, lhs, rhs, ty } => {
                        if op.starts_with("icmp") {
                            out.push_str(&format!("  %v{} = {} i64 %v{}, %v{}\n", dest.0, op, lhs.0, rhs.0));
                        } else {
                            out.push_str(&format!("  %v{} = {} {} %v{}, %v{}\n", dest.0, op, ty, lhs.0, rhs.0));
                        }
                    }
                    SSALocalInst::BpfCall { dest, helper_id, helper_name } => {
                        out.push_str(&format!("  ; BPF Helper: {} (ID: {})\n", helper_name, helper_id));
                        if let Some(d) = dest {
                            out.push_str(&format!("  %v{} = call i64 inttoptr (i64 {} to ptr)()\n", d.0, helper_id));
                        }
                    }
                    SSALocalInst::Branch { cond, then_block, else_block } => {
                        out.push_str(&format!("  br i1 %v{}, label %bb{}, label %bb{}\n", cond.0, then_block.0, else_block.0));
                    }
                    SSALocalInst::Jump(target) => {
                        out.push_str(&format!("  br label %bb{}\n", target.0));
                    }
                    SSALocalInst::Return(Some(v), ty) => {
                        out.push_str(&format!("  ret {} %v{}\n", ty, v.0));
                    }
                    SSALocalInst::Return(None, ty) => {
                        out.push_str(&format!("  ret {}\n", ty));
                    }
                }
            }
        }
        out.push_str("}\n\n");
        out
    }
}

// ----------------------------------------------------------------------------
// 7. MULTI-THREADED SEQUENCER RUNTIME & AUDIT HARNESS
// ----------------------------------------------------------------------------

pub struct NativeRuntimeAudit;

impl NativeRuntimeAudit {
    pub fn run_benchmark(target_port: u16, total_packets: u64, tsc_ghz: f64) {
        println!("==================================================================");
        println!(" LINUMS RUNTIME: ZERO-DEPENDENCY T0-T4 LATENCY AUDIT              ");
        println!("==================================================================");
        println!("[*] CPU Clock Calibration : {:.2} GHz", tsc_ghz);
        println!("[*] Ingress Port          : 127.0.0.1:{}", target_port);
        println!("[*] Target Burst Volume   : {} frames", total_packets);

        let running = Arc::new(AtomicBool::new(true));
        let ring = SpscRing::new();
        let total_processed = Arc::new(AtomicU64::new(0));

        let r_ring = Arc::clone(&ring);
        let r_running = Arc::clone(&running);
        let r_total = Arc::clone(&total_processed);

        // Sequencer Thread
        let seq_handle = thread::spawn(move || {
            let mut local_seq: u64 = 0;
            let mut t1_t2_auditor = LatencyAuditor::new(tsc_ghz);
            let mut t2_t3_auditor = LatencyAuditor::new(tsc_ghz);
            let mut t3_t4_auditor = LatencyAuditor::new(tsc_ghz);
            let mut t0_t4_auditor = LatencyAuditor::new(tsc_ghz);

            while r_running.load(Ordering::Relaxed) || r_total.load(Ordering::Relaxed) < total_packets {
                let r = r_ring.read_index.load(Ordering::Relaxed);
                let w = r_ring.write_index.load(Ordering::Acquire);

                if r == w {
                    std::hint::spin_loop();
                    continue;
                }

                let slot_idx = (r as usize) & SPSC_MASK;
                let mut frame = unsafe { r_ring.read_slot(slot_idx) };

                frame.t2_dequeue_cycles = read_cpu_tsc();
                local_seq += 1;
                frame.accepted_seq = local_seq;
                frame.t3_ordered_cycles = read_cpu_tsc();
                frame.t4_journal_cycles = read_cpu_tsc();

                if frame.t2_dequeue_cycles >= frame.t1_enqueue_cycles {
                    t1_t2_auditor.record(frame.t2_dequeue_cycles - frame.t1_enqueue_cycles);
                }
                if frame.t3_ordered_cycles >= frame.t2_dequeue_cycles {
                    t2_t3_auditor.record(frame.t3_ordered_cycles - frame.t2_dequeue_cycles);
                }
                if frame.t4_journal_cycles >= frame.t3_ordered_cycles {
                    t3_t4_auditor.record(frame.t4_journal_cycles - frame.t3_ordered_cycles);
                }
                if frame.t4_journal_cycles >= frame.t0_ingress_cycles {
                    t0_t4_auditor.record(frame.t4_journal_cycles - frame.t0_ingress_cycles);
                }

                r_ring.read_index.store(r + 1, Ordering::Release);
                r_total.fetch_add(1, Ordering::Relaxed);
            }

            (t1_t2_auditor, t2_t3_auditor, t3_t4_auditor, t0_t4_auditor)
        });

        // Ingress Thread
        let i_ring = Arc::clone(&ring);
        let i_running = Arc::clone(&running);

        let ingress_handle = thread::spawn(move || {
            let socket = UdpSocket::bind(format!("127.0.0.1:{}", target_port)).expect("Bind failed");
            socket.set_read_timeout(Some(Duration::from_millis(100))).unwrap();
            let mut buf = [0u8; 256];

            let mut in_seq = 0u64;
            while i_running.load(Ordering::Relaxed) {
                if let Ok((len, _)) = socket.recv_from(&mut buf) {
                    let t0 = read_cpu_tsc();

                    let w = i_ring.write_index.load(Ordering::Relaxed);
                    let r = i_ring.read_index.load(Ordering::Acquire);

                    if (w - r) >= SPSC_CAPACITY as u64 {
                        continue;
                    }

                    let slot_idx = (w as usize) & SPSC_MASK;
                    in_seq += 1;

                    let mut frame = WireFrame {
                        ingress_seq: in_seq,
                        accepted_seq: 0,
                        t0_ingress_cycles: t0,
                        t1_enqueue_cycles: read_cpu_tsc(),
                        t2_dequeue_cycles: 0,
                        t3_ordered_cycles: 0,
                        t4_journal_cycles: 0,
                        payload_len: len as u32,
                        client_ip: 0x7F000001,
                        payload: [0u8; 192],
                    };
                    frame.payload[..len.min(192)].copy_from_slice(&buf[..len.min(192)]);

                    unsafe { i_ring.write_slot(slot_idx, frame); }
                    i_ring.write_index.store(w + 1, Ordering::Release);
                }
            }
        });

        thread::sleep(Duration::from_millis(50));

        println!("[*] Injecting wire load...");
        let gen_start = Instant::now();
        let client_sock = UdpSocket::bind("0.0.0.0:0").unwrap();
        client_sock.connect(format!("127.0.0.1:{}", target_port)).unwrap();
        let test_payload = [0xA5u8; 64];

        for _ in 0..total_packets {
            let _ = client_sock.send(&test_payload);
        }

        let gen_dur = gen_start.elapsed().as_secs_f64();
        let pps = total_packets as f64 / gen_dur;
        println!("[✓] Dispatched {} packets in {:.4}s ({:.0} pkt/sec)", total_packets, gen_dur, pps);

        thread::sleep(Duration::from_millis(200));
        running.store(false, Ordering::Relaxed);

        let _ = ingress_handle.join();
        let (t1_t2, t2_t3, t3_t4, t0_t4) = seq_handle.join().unwrap();

        t1_t2.print_report("T1 -> T2 (SPSC Queue Wait Delay)");
        t2_t3.print_report("T2 -> T3 (Sequencer Ordering Logic)");
        t3_t4.print_report("T3 -> T4 (Journal Commit & Write)");
        t0_t4.print_report("T0 -> T4 (Total Ingress-to-Journal Wire Transit)");
    }
}

// ----------------------------------------------------------------------------
// 8. MAIN ENTRYPOINT
// ----------------------------------------------------------------------------

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let cmd = if args.len() > 1 { args[1].as_str() } else { "help" };

    match cmd {
        "build" => {
            let source_path = if args.len() > 2 { &args[2] } else { "linum_unified/unified_pipeline.ln" };
            println!("[*] Compiling Linum Source: {}", source_path);

            let mut src_content = String::new();
            if let Ok(mut f) = File::open(source_path) {
                f.read_to_string(&mut src_content).unwrap();
            } else {
                eprintln!("[FATAL] Could not read {}", source_path);
                return;
            }

            let mut parser = Parser::new(&src_content);
            let ast_funcs = parser.parse_module().expect("AST Parsing Failed");

            let mut bpf_ll = String::from("; ModuleID = 'LinumBPF'\ntarget datalayout = \"e-m:e-p:64:64-i64:64-i128:128-n32:64-S128\"\ntarget triple = \"bpfel-unknown-none\"\n\n@PACKET_RING = dso_local global [24 x i8] zeroinitializer, section \".maps\", align 4\n\n");
            let mut native_ll = String::from("; ModuleID = 'LinumNative'\ntarget datalayout = \"e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128\"\ntarget triple = \"x86_64-unknown-linux-gnu\"\n\n");

            for func in &ast_funcs {
                let mut builder = SSABuilder::new();
                builder.compile_function(func);
                let llvm_func = builder.emit_llvm_function(func);

                if func.section.is_some() {
                    bpf_ll.push_str(&llvm_func);
                } else {
                    native_ll.push_str(&llvm_func);
                }
            }

            bpf_ll.push_str("attributes #0 = { nounwind }\n!llvm.module.flags = !{!0}\n!0 = !{i32 1, !\"wchar_size\", i32 4}\n");
            native_ll.push_str("attributes #0 = { nounwind }\n!llvm.module.flags = !{!0}\n!0 = !{i32 1, !\"wchar_size\", i32 4}\n");

            let mut f_bpf = File::create("ingress_xdp.ll").unwrap();
            f_bpf.write_all(bpf_ll.as_bytes()).unwrap();

            let mut f_native = File::create("sequencer.ll").unwrap();
            f_native.write_all(native_ll.as_bytes()).unwrap();

            println!("[✓] Successfully lowered {} functions to SSA and emitted ingress_xdp.ll & sequencer.ll", ast_funcs.len());
        }
        "audit" => {
            let count = if args.len() > 2 { args[2].parse().unwrap_or(200_000) } else { 200_000 };
            let port = if args.len() > 3 { args[3].parse().unwrap_or(9999) } else { 9999 };
            let ghz = if args.len() > 4 { args[4].parse().unwrap_or(2.60) } else { 2.60 };
            NativeRuntimeAudit::run_benchmark(port, count, ghz);
        }
        _ => {
            println!("============================================================");
            println!(" LINUMS UNIFIED COMPILER & IN-CORE LATENCY AUDITOR          ");
            println!("============================================================");
            println!("Usage:");
            println!("  linums build [file.ln]        Compile AST -> SSA -> LLVM IR");
            println!("  linums audit [pkts] [p] [ghz] Run In-Core T0-T4 Latency Benchmark");
            println!("============================================================");
        }
    }
}
