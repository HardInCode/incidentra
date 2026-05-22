from app.core.detection_engine import DetectionEngine
from app.core.log_parser import parse_log_line

engine = DetectionEngine()
line = '192.168.1.36 - - [20/May/2026:00:00:00 +0000] "GET /cmd?cmd=whoami HTTP/1.1" 200 100 "-" "Mozilla"'
r = engine.analyze(parse_log_line(line))
print('cmd=whoami ->', r['attack_type'] if r else 'NO INCIDENT')
