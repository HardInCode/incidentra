"""Shared password policy — register, forgot/reset, admin create/reset."""
import re

PASSWORD_MIN_LENGTH = 8
SPECIAL_PATTERN = re.compile(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]')


def validate_password(password: str) -> tuple[bool, str | None]:
    """
    Return (ok, error_code). error_code is machine-readable for frontend i18n.
    """
    if not password or len(password) < PASSWORD_MIN_LENGTH:
        return False, 'password_too_short'
    if not re.search(r'[A-Z]', password):
        return False, 'password_policy_weak'
    if not re.search(r'[a-z]', password):
        return False, 'password_policy_weak'
    if not re.search(r'\d', password):
        return False, 'password_policy_weak'
    if not SPECIAL_PATTERN.search(password):
        return False, 'password_policy_weak'
    return True, None
