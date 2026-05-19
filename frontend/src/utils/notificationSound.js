const SOUND_ENABLED_KEY = 'sme_notif_sound_enabled';

let audioCtx = null;

export function isNotificationSoundEnabled() {
  const raw = localStorage.getItem(SOUND_ENABLED_KEY);
  if (raw === null) return true;
  return raw === 'true';
}

export function setNotificationSoundEnabled(enabled) {
  localStorage.setItem(SOUND_ENABLED_KEY, enabled ? 'true' : 'false');
}

/** Resume AudioContext after a user gesture (browser autoplay policy). */
export function unlockNotificationSound() {
  try {
    if (!audioCtx) {
      const Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      audioCtx = new Ctx();
    }
    if (audioCtx.state === 'suspended') {
      audioCtx.resume();
    }
  } catch {
    /* ignore */
  }
}

/** Short alert beep (~300ms). Returns false if blocked by autoplay policy. */
export function playNotificationSound() {
  if (!isNotificationSoundEnabled()) return true;
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return false;
    if (!audioCtx) audioCtx = new Ctx();
    if (audioCtx.state === 'suspended') {
      audioCtx.resume().catch(() => {});
      if (audioCtx.state === 'suspended') return false;
    }

    const now = audioCtx.currentTime;
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(880, now);
    osc.frequency.setValueAtTime(660, now + 0.12);
    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.exponentialRampToValueAtTime(0.12, now + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.28);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start(now);
    osc.stop(now + 0.3);
    return true;
  } catch {
    return false;
  }
}
