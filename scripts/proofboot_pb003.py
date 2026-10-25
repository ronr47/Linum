#!/usr/bin/env python3
"""LINUM ProofBoot PB-003: policy transition model."""

from dataclasses import dataclass
from enum import Enum


class State(Enum):
    NORMAL = "NORMAL"
    UPDATE_PENDING = "UPDATE_PENDING"
    RECOVERY = "RECOVERY"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class Policy:
    policy_id: str
    generation: int
    authorized_keys: frozenset[str]
    allowed_architectures: frozenset[str]
    recovery_key: str | None = None


class Reject(Exception):
    pass


def validate_policy(policy):
    if not policy.policy_id:
        raise Reject("empty policy ID")
    if type(policy.generation) is not int or policy.generation < 1:
        raise Reject("invalid generation")
    if not policy.authorized_keys:
        raise Reject("no authorized release keys")
    if not policy.allowed_architectures:
        raise Reject("no allowed architectures")


def authorize_transition(committed, proposed, signer_key):
    """Authorize a proposed policy transition."""
    validate_policy(committed)
    validate_policy(proposed)

    if signer_key not in committed.authorized_keys:
        raise Reject("transition signer is not currently authorized")

    if proposed.generation != committed.generation + 1:
        raise Reject("policy generation must advance by exactly one")

    return State.UPDATE_PENDING


def commit_transition(committed, proposed, transition_state):
    """Model a commit after transition authorization."""
    if transition_state is not State.UPDATE_PENDING:
        raise Reject("no authorized update is pending")

    validate_policy(committed)
    validate_policy(proposed)

    if proposed.generation != committed.generation + 1:
        raise Reject("committed generation changed")

    return proposed


def authorize_image(
    policy, architecture, signer_key, image_digest, recovery=False
):
    validate_policy(policy)

    if architecture not in policy.allowed_architectures:
        raise Reject("architecture is not permitted")

    if not isinstance(image_digest, str) or len(image_digest) != 64:
        raise Reject("expected a SHA-256 hex digest")

    try:
        bytes.fromhex(image_digest)
    except ValueError as exc:
        raise Reject("invalid image digest") from exc

    if recovery:
        if policy.recovery_key is None:
            raise Reject("recovery is not authorized")
        if signer_key != policy.recovery_key:
            raise Reject("invalid recovery signer")
        return State.RECOVERY

    if signer_key not in policy.authorized_keys:
        raise Reject("image signer is not authorized")

    return State.NORMAL
