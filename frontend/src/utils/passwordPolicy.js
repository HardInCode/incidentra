/** Client-side mirror of backend/app/utils/password_policy.py */
const SPECIAL = /[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/;

export function validatePassword(password) {
  if (!password || password.length < 8) return 'password_too_short';
  if (!/[A-Z]/.test(password)) return 'password_policy_weak';
  if (!/[a-z]/.test(password)) return 'password_policy_weak';
  if (!/\d/.test(password)) return 'password_policy_weak';
  if (!SPECIAL.test(password)) return 'password_policy_weak';
  return null;
}
