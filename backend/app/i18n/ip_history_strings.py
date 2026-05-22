"""Template strings for IP history pattern_summary (no LLM)."""

SUPPORTED_LANGS = ('en', 'id')


def resolve_lang(lang_param):
    if lang_param and str(lang_param).lower().startswith('id'):
        return 'id'
    return 'en'


def _last_active(diff_seconds, lang):
    if diff_seconds < 60:
        if lang == 'id':
            return 'baru saja'
        return 'just now'
    if diff_seconds < 3600:
        n = int(diff_seconds / 60)
        if lang == 'id':
            return f'{n} menit lalu'
        return f'{n} minute{"s" if n != 1 else ""} ago'
    if diff_seconds < 86400:
        n = int(diff_seconds / 3600)
        if lang == 'id':
            return f'{n} jam lalu'
        return f'{n} hour{"s" if n != 1 else ""} ago'
    n = int(diff_seconds / 86400)
    if lang == 'id':
        return f'{n} hari lalu'
    return f'{n} day{"s" if n != 1 else ""} ago'


def _pattern_hint(frequency_per_day, critical_count, attack_count, lang):
    if frequency_per_day > 10:
        if lang == 'id':
            return 'Pola menunjukkan automated scanning atau bot attack.'
        return 'Pattern suggests automated scanning or bot activity.'
    if critical_count > 0:
        if lang == 'id':
            return 'Ditemukan serangan tingkat kritis yang mengindikasikan targeted attack.'
        return 'Critical-severity attacks indicate a targeted attack.'
    if attack_count > 2:
        if lang == 'id':
            return 'Variasi tipe serangan menunjukkan reconnaissance aktif.'
        return 'Multiple attack types suggest active reconnaissance.'
    if lang == 'id':
        return 'Aktivitas mencurigakan memerlukan pemantauan lebih lanjut.'
    return 'Suspicious activity warrants further monitoring.'


def empty_history_summary(ip_address, lang):
    if lang == 'id':
        return f'IP {ip_address} tidak memiliki riwayat insiden.'
    return f'IP {ip_address} has no incident history.'


def build_pattern_summary(
    total,
    days_span,
    dominant_attack,
    dominant_count,
    last_active_str,
    frequency_per_day,
    critical_count,
    attack_count,
    lang,
):
    hint = _pattern_hint(frequency_per_day, critical_count, attack_count, lang)
    if lang == 'id':
        return (
            f'IP ini memicu {total} insiden dalam {days_span} hari, '
            f'didominasi {dominant_attack} ({dominant_count}x). '
            f'Terakhir aktif {last_active_str}. {hint}'
        )
    return (
        f'This IP triggered {total} incident{"s" if total != 1 else ""} over {days_span} day'
        f'{"s" if days_span != 1 else ""}, dominated by {dominant_attack} ({dominant_count}x). '
        f'Last active {last_active_str}. {hint}'
    )


def format_last_active(diff_seconds, lang):
    return _last_active(diff_seconds, lang)
