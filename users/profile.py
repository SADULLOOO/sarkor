from .models import ExecutorProfile, User

PROFILE_FILLED_THRESHOLD = 80

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


def refresh_trust_level(user: User) -> None:
    """Move the user between "newbie" and "profile filled".

    Higher levels (verified, reliable) and "caution" are set by other rules,
    so we don't touch them here.
    """
    auto_levels = {User.TrustLevel.NEWBIE, User.TrustLevel.PROFILE_FILLED}
    if user.trust_level not in auto_levels:
        return

    profile = getattr(user, "executor_profile", None)
    is_filled = profile is not None and get_completeness(profile)[0] >= PROFILE_FILLED_THRESHOLD
    new_level = User.TrustLevel.PROFILE_FILLED if is_filled else User.TrustLevel.NEWBIE

    if user.trust_level != new_level:
        user.trust_level = new_level
        user.save(update_fields=["trust_level"])
