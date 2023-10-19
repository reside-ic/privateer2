from privateer2.backup import backup_command
from privateer2.config import read_config
from privateer2.util import current_timezone_name
from privateer2.yacron import generate_yacron_yaml, validate_yacron_yaml


def test_can_generate_yacron_yaml():
    cfg = read_config("example/schedule.json")
    cfg.clients[0].schedule.port = None
    cfg.clients[0].schedule.jobs.pop()
    res = generate_yacron_yaml(cfg, "bob")
    expected = [
        "defaults:",
        f'  timezone: "{current_timezone_name()}"',
        "jobs:",
        '  - name: "job-1"',
        f"    command: \"{' '.join(backup_command('bob', 'data1', 'alice'))}\"",
        '    schedule: "@daily"',
    ]
    validate_yacron_yaml(res)
    assert res == expected
