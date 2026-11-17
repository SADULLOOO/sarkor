from decimal import Decimal

from .models import ExecutorProfile, User

PROFILE_FILLED_THRESHOLD = 80
RELIABLE_MIN_COMPLETED = 10
RELIABLE_MIN_RATING = Decimal("4.5")

# What makes an executor profile "complete" and how much each part is worth.
COMPLETENESS_WEIGHTS = {
    "name": 20,
    "photo": 20,
    "about": 20,
    "categories": 20,
    "districts": 10,
    "portfolio": 10,
}


def get_completeness(profile: ExecutorProfile) -> tuple[int, list[str]]:
    """Return (percent, missing parts) for the executor profile."""
    filled = {
        "name": bool(profile.user.name),
        "photo": bool(profile.photo),
        "about": bool(profile.about.strip()),
        "categories": profile.categories.exists(),
        "districts": profile.districts.exists(),
        "portfolio": profile.portfolio.exists(),
    }
    percent = sum(COMPLETENESS_WEIGHTS[part] for part, ok in filled.items() if ok)
    missing = [part for part, ok in filled.items() if not ok]
    return percent, missing


def _is_reliable(profile: ExecutorProfile | None) -> bool:
    # TODO: also require "no confirmed complaints in 90 days" once complaints exist.
    return (
        profile is not None
        and profile.completed_count >= RELIABLE_MIN_COMPLETED
        and profile.rating >= RELIABLE_MIN_RATING
    )


def refresh_trust_level(user: User) -> None:
    """Recalculate the levels that depend only on the profile and the work history.

    "Verified" is given by a moderator after the passport check and "caution"
    by complaints/antifraud, so here we only move inside these pairs:
    newbie <-> profile filled, verified <-> reliable.
    """
    if user.trust_level == User.TrustLevel.CAUTION:
        return

    profile = getattr(user, "executor_profile", None)
    if user.trust_level in (User.TrustLevel.VERIFIED, User.TrustLevel.RELIABLE):
        new_level = User.TrustLevel.RELIABLE if _is_reliable(profile) else User.TrustLevel.VERIFIED
    else:
        is_filled = profile is not None and get_completeness(profile)[0] >= PROFILE_FILLED_THRESHOLD
        new_level = User.TrustLevel.PROFILE_FILLED if is_filled else User.TrustLevel.NEWBIE

    if user.trust_level != new_level:
        user.trust_level = new_level
        user.save(update_fields=["trust_level"])
