// frontend/src/hooks/useCurrentUser.js
// REVISI 3B: Hook untuk decode JWT dan mendapatkan info user saat ini

/**
 * Decode JWT dari localStorage tanpa library tambahan.
 * Return: { user_id, username, role } atau null jika tidak ada / expired.
 */
export default function useCurrentUser() {
  try {
    const token = localStorage.getItem('incidentra_token');
    if (!token) return null;

    const parts = token.split('.');
    if (parts.length !== 3) return null;

    // Decode base64url → JSON
    const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));

    // Cek expired
    if (payload.exp && payload.exp * 1000 < Date.now()) return null;

    return {
      user_id: payload.user_id,
      username: payload.username,
      role: payload.role,
    };
  } catch {
    return null;
  }
}
