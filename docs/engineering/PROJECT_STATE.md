# Project State Record

## Milestone: Stage 2 Lowering — Intermediate Representation (R2-IR) Complete
- **Status**: GREEN
- **Verified Baseline**: 73/73 tests passing (`python3 -m unittest discover -s tests -v`)

### Pipeline Progression
1. **Stage 0 (Frontend)**:
   - `src/frontend/lexer.py` & `src/frontend/parser.py`: Feature-complete tokenizer and recursive-descent parser.
   - Verified on `proofboot_pb010.r2` (struct literals, array repeat, postfix operations, memory domain qualifiers).
2. **Stage 1 (Semantic Analysis)**:
   - `src/semantic/analyzer.py`: Declaration registration, memory domain enforcement (`ram`, `mmio`, `ioport`, `cap`), scoped symbol tables, statement checking, and expression type inference (`DerefExpr`, `TupleLetStmt`, `FieldExpr`, `IndexExpr`, `UnsafeExpr`).
3. **Stage 2 (Lowering / IR)**:
   - `src/lowering/ir.py`: Linear three-address code instructions, explicit domain memory accesses (`RamLoad`, `RamStore`, `MmioLoad`, `MmioStore`, `MmioBarrier`), basic blocks, and functions.
   - `src/lowering/lowerer.py`: Lowers checked AST into labeled basic blocks, flattening conditionals (`IfStmt`, `WhileStmt`) into `BranchIf` and `Jump` instructions.
   - `tests/test_stage2_lowering.py`: Validates branching flattening and lowering of all 5 functions in `proofboot_pb010.r2`.

### Active Task & Next Engineering Action
- Stages 0, 1, and 2 are green and regression-free.
- Next step: Stage 3 Target Backend / Code Emission (or symbolic execution / bytecode verification).
