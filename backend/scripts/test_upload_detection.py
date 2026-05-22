"""Quick check: FILE_UPLOAD only for dangerous extensions."""
from app.core.detection_engine import DetectionEngine
from app.core.log_parser import parse_log_line

engine = DetectionEngine()

cases = [
    ('safe_txt', '127.0.0.1 - - [20/May/2026:00:00:00 +0000] "POST /files HTTP/1.1" 302 0 "-" "Mozilla/5.0" POST_DATA:file=notes.txt', None),
    ('danger_php', '127.0.0.1 - - [20/May/2026:00:00:00 +0000] "POST /files HTTP/1.1" 302 0 "-" "Mozilla/5.0" POST_DATA:file=shell.php', 'FILE_UPLOAD'),
    ('double_ext', '127.0.0.1 - - [20/May/2026:00:00:00 +0000] "POST /files HTTP/1.1" 302 0 "-" "Mozilla/5.0" POST_DATA:file=evil.php.jpg', 'FILE_UPLOAD'),
]

for name, line, expected_type in cases:
    result = engine.analyze(parse_log_line(line))
    got = result['attack_type'] if result else None
    print(name, 'OK' if got == expected_type else f'FAIL expected={expected_type} got={got}')
