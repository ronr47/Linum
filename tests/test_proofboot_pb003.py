import unittest

from scripts.proofboot_pb003 import (
    Policy,
    Reject,
    State,
    authorize_transition,
    commit_transition,
    authorize_image,
)


class PB003Tests(unittest.TestCase):
    def setUp(self):
        self.old = Policy(
            policy_id="linum-release",
            generation=1,
            authorized_keys=frozenset({"release-A"}),
            allowed_architectures=frozenset(
                {"x86_64", "aarch64"}
            ),
            recovery_key="recovery-R",
        )

        self.new = Policy(
            policy_id="linum-release",
            generation=2,
            authorized_keys=frozenset({"release-B"}),
            allowed_architectures=frozenset(
                {"x86_64", "aarch64"}
            ),
            recovery_key="recovery-R",
        )

        self.digest = "ab" * 32

    def test_authorized_transition(self):
        state = authorize_transition(
            self.old, self.new, "release-A"
        )
        self.assertIs(state, State.UPDATE_PENDING)

    def test_untrusted_transition_signer_rejected(self):
        with self.assertRaises(Reject):
            authorize_transition(
                self.old, self.new, "attacker"
            )

    def test_generation_skip_rejected(self):
        skipped = Policy(
            policy_id="linum-release",
            generation=3,
            authorized_keys=frozenset({"release-B"}),
            allowed_architectures=frozenset(
                {"x86_64", "aarch64"}
            ),
        )
        with self.assertRaises(Reject):
            authorize_transition(
                self.old, skipped, "release-A"
            )

    def test_commit_requires_pending_state(self):
        with self.assertRaises(Reject):
            commit_transition(
                self.old, self.new, State.NORMAL
            )

    def test_authorized_commit(self):
        state = authorize_transition(
            self.old, self.new, "release-A"
        )
        committed = commit_transition(
            self.old, self.new, state
        )
        self.assertEqual(committed.generation, 2)

    def test_old_release_key_revoked_after_transition(self):
        with self.assertRaises(Reject):
            authorize_image(
                self.new, "aarch64", "release-A",
                self.digest
            )

    def test_new_release_key_authorized(self):
        self.assertIs(
            authorize_image(
                self.new, "aarch64", "release-B",
                self.digest
            ),
            State.NORMAL,
        )

    def test_cross_architecture_rejected(self):
        with self.assertRaises(Reject):
            authorize_image(
                self.new, "x86", "release-B",
                self.digest
            )

    def test_recovery_requires_authorized_key(self):
        with self.assertRaises(Reject):
            authorize_image(
                self.new, "aarch64", "attacker",
                self.digest, recovery=True
            )

    def test_authorized_recovery(self):
        self.assertIs(
            authorize_image(
                self.new, "aarch64", "recovery-R",
                self.digest, recovery=True
            ),
            State.RECOVERY,
        )


if __name__ == "__main__":
    unittest.main()
