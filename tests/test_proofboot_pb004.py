import copy
import unittest


def initial_store():
    return {
        "committed": {
            "generation": 1,
            "key": "release-A",
        },
        "pending": None,
    }


def recover(store):
    """Only the committed record is authoritative."""
    committed = store.get("committed")
    if not isinstance(committed, dict):
        raise ValueError("no valid committed policy")
    if type(committed.get("generation")) is not int:
        raise ValueError("invalid committed generation")
    if not committed.get("key"):
        raise ValueError("invalid committed key")
    return copy.deepcopy(committed)


def update_policy(store, crash_after=None):
    """
    Simulate persistence steps.
    crash_after=N interrupts after step N.
    """
    new_policy = {
        "generation": 2,
        "key": "release-B",
    }

    # Step 1: write an inactive pending record.
    store["pending"] = copy.deepcopy(new_policy)
    if crash_after == 1:
        raise RuntimeError("simulated crash after pending write")

    # Step 2: validate the proposed record.
    if new_policy["generation"] != (
        store["committed"]["generation"] + 1
    ):
        raise ValueError("invalid generation")
    if crash_after == 2:
        raise RuntimeError("simulated crash after validation")

    # Step 3: atomically replace the committed record.
    # This is atomic only in this in-memory model.
    store["committed"] = copy.deepcopy(new_policy)
    if crash_after == 3:
        raise RuntimeError("simulated crash after commit")

    # Step 4: clear the pending record.
    store["pending"] = None
    if crash_after == 4:
        raise RuntimeError("simulated crash after cleanup")


class PB004Tests(unittest.TestCase):
    def test_crash_before_update_preserves_old_policy(self):
        store = initial_store()
        self.assertEqual(
            recover(store),
            {"generation": 1, "key": "release-A"},
        )

    def test_crash_after_pending_write(self):
        store = initial_store()
        with self.assertRaises(RuntimeError):
            update_policy(store, crash_after=1)
        self.assertEqual(recover(store)["generation"], 1)

    def test_crash_after_validation(self):
        store = initial_store()
        with self.assertRaises(RuntimeError):
            update_policy(store, crash_after=2)
        self.assertEqual(recover(store)["key"], "release-A")

    def test_crash_after_commit(self):
        store = initial_store()
        with self.assertRaises(RuntimeError):
            update_policy(store, crash_after=3)
        self.assertEqual(
            recover(store),
            {"generation": 2, "key": "release-B"},
        )

    def test_crash_after_cleanup(self):
        store = initial_store()
        with self.assertRaises(RuntimeError):
            update_policy(store, crash_after=4)
        self.assertEqual(recover(store)["generation"], 2)

    def test_completed_update(self):
        store = initial_store()
        update_policy(store)
        self.assertEqual(
            recover(store),
            {"generation": 2, "key": "release-B"},
        )
        self.assertIsNone(store["pending"])


if __name__ == "__main__":
    unittest.main()
