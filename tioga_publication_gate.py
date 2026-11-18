"""Fail-closed publication decision for *verified* Tioga notice evidence.

Offline policy primitive only; never fetches, seeds, or publishes bids.
The caller must independently verify every input from permitted official notices.
"""
from datetime import datetime, timezone
from tioga_notice_sections import deadline_evidence_status


def publication_decision(*, index_deadline, document_deadline, checked_at,
                         official_document_verified=False,
                         eligible_tree_scope=False, geographic_match=False,
                         historical_or_awarded=False):
    """Return (eligible, reason), requiring affirmative evidence for every gate.

    This deliberately excludes related demolition/site-prep: those need a
    separately labeled, independently verified policy and must not be
    represented as tree contracts.
    """
    if historical_or_awarded:
        return False, 'historical_or_awarded'
    if not official_document_verified:
        return False, 'document_unverified'
    if not eligible_tree_scope:
        return False, 'scope_unverified_or_unrelated'
    if not geographic_match:
        return False, 'geography_unverified_or_outside'
    status = deadline_evidence_status(index_deadline, document_deadline)
    if status != 'consistent':
        return False, 'deadline_' + status
    try:
        deadline = datetime.fromisoformat(document_deadline)
    except (TypeError, ValueError):
        return False, 'deadline_verification_required'
    if not isinstance(checked_at, datetime) or checked_at.tzinfo is None or checked_at.utcoffset() is None:
        return False, 'check_time_unverified'
    if deadline <= checked_at:
        return False, 'expired'
    return True, 'verified_candidate_not_publication'
