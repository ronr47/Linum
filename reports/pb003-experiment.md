# LINUM ProofBoot PB-003

## Hypothesis
Every accepted boot image must be authorized by the currently
committed trust policy or by a valid, explicitly authorized
policy transition.

## Platforms
- x86_64 PE32+ EFI
- AArch64 PE32+ EFI

## Test cases
1. Valid image and valid policy: accept.
2. Modified image: reject.
3. Modified policy: reject.
4. Policy signed by an untrusted key: reject.
5. Policy generation below the committed minimum: reject.
6. Interrupted policy update: preserve the old committed policy.
7. Recovery image without recovery authorization: reject.
8. Cross-architecture image substitution: reject.
9. Replayed old policy after a successful transition: reject.
10. Same protocol vectors on both architectures: identical decisions.

## Important limitation
A file-based generation counter is not secure against an attacker
who can restore the entire filesystem or replace the verifier.
Rollback resistance requires trusted persistent state, such as a
hardware-backed monotonic mechanism or a separately protected
commit record.
