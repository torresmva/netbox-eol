"""Framework-free matching decision logic (no Django imports).

Pure functions over plain values and client dataclasses, so they are unit-testable
without NetBox. The Django model/job layer extracts DeviceType values, calls these,
and persists the results.
"""

MIN_Q = 2


def build_query(*, ref, model=None, part_number=None, vendor_slug=None):
    """Build a single `/integrations/match` query for a DeviceType.

    Prefer part_number over model; pre-filter q < 2 chars (return None so the
    caller doesn't spend a daily item on a row that would only error).
    """
    q = (part_number or model or "").strip()
    if len(q) < MIN_Q:
        return None
    query = {"ref": str(ref), "q": q}
    if vendor_slug:
        query["vendor"] = vendor_slug
    return query


def classify(row, auto_accept_tiers, review_tiers):
    """Map a MatchRow to an action: 'invalid' | 'auto' | 'review' | 'unmatched'.

    'invalid' = bad input (has an error) → "fix the NetBox data", distinct from a
    valid no-match ('unmatched'). Tier policy drives the rest.
    """
    if row.error:
        return "invalid"
    if row.confidence in auto_accept_tiers:
        return "auto"
    if row.confidence in review_tiers:
        return "review"
    return "unmatched"


def learned_vendor(row):
    """The vendor slug to cache for a Manufacturer: the resolved hint if the alias
    map fired, else the matched product's own vendor (the richest signal when the
    hint didn't resolve but a global match still landed). None if neither."""
    if row.vendor_resolved:
        return row.vendor_resolved
    if row.match and row.match.vendor_slug:
        return row.match.vendor_slug
    return None
