"""Explainable event rules. Runs inside the caller's SQLite transaction."""
import json
import re
from datetime import datetime, timedelta, timezone


def rule(id, name, logic, severity, input):
    return dict(id=id, name=name, logic=logic, severity=severity, input=input)


RULES = [
    rule('AUTH-001', 'Failed login burst', '5 failed logins in 60 seconds, same source, host, IP and user', 'high', 'Windows 4625 or normalized login_failed'),
    rule('WIN-001', 'Windows audit log cleared', 'Security event 1102', 'critical', 'Windows collector: Security'),
    rule('WIN-002', 'Windows account created', 'Security event 4720; verify authorization', 'medium', 'Windows collector: Security'),
    rule('WIN-003', 'Windows service installed', 'System 7045 / Security 4697; verify authorization', 'medium', 'Windows collector: System / Security'),
    rule('WIN-004', 'Defender threat detected', 'Defender event 1116', 'high', 'Windows collector: Defender Operational'),
    rule('AUTH-002', 'Successful login after failures', 'A successful login following 5 failures in 5 minutes for the same source, host, IP and user', 'high', 'Windows 4625 + 4624, or normalized login_failed + login_success'),
    rule('AUTH-003', 'Possible password spraying', '10 failed logins across at least 5 known usernames in 5 minutes from the same known IP, source and host', 'high', 'Windows 4625 or normalized login_failed; requires usable IP and usernames'),
    rule('WIN-005', 'Windows account locked out', 'Security event 4740; investigate repeated authentication failures', 'medium', 'Windows collector: Security'),
    rule('WIN-006', 'Windows account deleted', 'Security event 4726; verify authorization', 'medium', 'Windows collector: Security'),
    rule('WIN-007', 'Administrative group member added', 'Group member addition to local Administrators, Domain Admins or Enterprise Admins, identified by group SID', 'high', 'Windows 4732 / 4728 / 4756, with details.fields.TargetSid'),
    rule('WIN-008', 'Windows audit policy changed', 'Security event 4719; review the recorded audit policy change', 'high', 'Windows collector: Security; policy changes may be legitimate'),
    rule('WIN-009', 'Windows scheduled task created', 'Security event 4698; review the recorded task and author', 'medium', 'Windows collector: Security; task creation is not proof of persistence abuse'),
    rule('WIN-010', 'Defender real-time protection disabled', 'Defender Operational event 5001, or antivirus/real-time protection observed OFF', 'high', 'Windows Event collector or V1 read-only Defender status monitor; other antivirus products not assessed'),
    rule('WIN-011', 'Windows Firewall profile disabled', 'A Windows Firewall profile is observed disabled, initially or after a change', 'high', 'V1 protection monitor: read-only Get-NetFirewallProfile'),
]
BY_ID = {r['id']: r for r in RULES}
SINGLE = {'audit_cleared': 'WIN-001', 'account_created': 'WIN-002',
          'service_installed': 'WIN-003', 'malware_detected': 'WIN-004',
          'account_locked': 'WIN-005', 'account_deleted': 'WIN-006',
          'audit_policy_changed': 'WIN-008', 'scheduled_task_created': 'WIN-009',
          'defender_disabled': 'WIN-010', 'firewall_disabled': 'WIN-011'}


def known(value):
    return str(value).strip().lower() not in ('', '-', 'unknown', 'none', 'null')


def detect(db, e):
    def window(action, seconds, account=False):
        fields = ['dataset', 'source', 'host', 'ip'] + (['user'] if account else [])
        start = (datetime.fromisoformat(e['ts']) - timedelta(seconds=seconds)).isoformat(timespec='milliseconds')
        where = ' AND '.join(f'{f}=?' for f in fields)
        rows = db.execute(f'SELECT * FROM events WHERE {where} AND action=? AND ts BETWEEN ? AND ? ORDER BY ts,id',
                          [e[f] for f in fields] + [action, start, e['ts']]).fetchall()
        return rows, json.dumps([e[f] for f in fields])

    def emit(rule_id, rows, group, merge=True):
        ids = [str(r['id']) for r in rows]
        current = datetime.now(timezone.utc)
        stamp = current.isoformat(timespec='milliseconds')
        if merge:
            old = db.execute('SELECT * FROM alerts WHERE ruleId=? AND group_key=? AND dataset=? AND updatedAt>=? ORDER BY id DESC LIMIT 1',
                             (rule_id, group, e['dataset'], (current-timedelta(seconds=60)).isoformat(timespec='milliseconds'))).fetchone()
            if old:
                ids = list(dict.fromkeys(json.loads(old['eventIds']) + ids))
                db.execute('UPDATE alerts SET eventIds=?,updatedAt=? WHERE id=?', (json.dumps(ids), stamp, old['id']))
                return
        r = BY_ID[rule_id]
        db.execute("INSERT INTO alerts(ruleId,title,severity,status,createdAt,updatedAt,group_key,dataset,eventIds) VALUES(?,?,?,'open',?,?,?,?,?)",
                   (rule_id, r['name'], r['severity'], stamp, stamp, group, e['dataset'], json.dumps(ids)))

    action = e['action']
    if action == 'login_failed':
        rows, group = window(action, 60, account=True)
        if len(rows) >= 5:
            emit('AUTH-001', rows, group)
    if action == 'login_failed' and known(e['ip']):
        rows, group = window(action, 300)
        rows = [r for r in rows if known(r['user'])]
        if len(rows) >= 10 and len({r['user'].casefold() for r in rows}) >= 5:
            emit('AUTH-003', rows, group)
    if action == 'login_success' and known(e['user']):
        rows, group = window('login_failed', 300, account=True)
        # The success must follow the failures, including timestamp ties only
        # when failure records were received before this success.
        if len(rows) >= 5:
            emit('AUTH-002', [*rows, e], group)
    if action in SINGLE:
        emit(SINGLE[action], [e], str(e['id']), merge=False)
    if action == 'group_member_added':
        details = e['details']
        fields = details.get('fields', {})
        sid = str(fields.get('TargetSid', '')) if isinstance(fields, dict) else ''
        if sid == 'S-1-5-32-544' or re.fullmatch(r'S-1-5-21-\d+-\d+-\d+-(512|519)', sid):
            emit('WIN-007', [e], str(e['id']), merge=False)
