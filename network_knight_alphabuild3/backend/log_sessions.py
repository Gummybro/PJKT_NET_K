"""Tab sessions use insertion IDs so late Windows records appear when collected."""
import ctypes
import os
import secrets
import subprocess
from pathlib import Path
from fastapi import HTTPException, Request


def approve_reset():
    if os.name != 'nt':
        raise HTTPException(403, "Windows administrator approval required")
    # Only the Windows registry utility elevates. Its protected HKLM write is
    # tied to a random challenge generated for this individual request.
    import winreg
    import time
    challenge = secrets.token_hex(32)
    key = r"SOFTWARE\NetworkKnight\SessionApproval"
    exe = str(Path(os.environ['SystemRoot']) / 'System32' / 'reg.exe')
    params = subprocess.list2cmdline(['add', 'HKLM\\'+key, '/v', 'Approval', '/t', 'REG_SZ', '/d', challenge, '/f', '/reg:64'])
    launch = ctypes.windll.shell32.ShellExecuteW
    launch.restype = ctypes.c_void_p
    if (launch(None, 'runas', exe, params, None, 0) or 0) <= 32:
        raise HTTPException(403, "Administrator approval was declined or unavailable")
    for _ in range(50):
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as handle:
                if winreg.QueryValueEx(handle, 'Approval')[0] == challenge:
                    return True
        except OSError:
            pass
        time.sleep(.1)
    raise HTTPException(403, "Administrator approval could not be verified")



def install(api, db, lock, dashboard, event):
    db.execute("CREATE TABLE IF NOT EXISTS log_sessions(token TEXT PRIMARY KEY, boundary INTEGER NOT NULL)")
    def newest():
        return db.execute("SELECT COALESCE(MAX(id),0) FROM events").fetchone()[0]

    @api.post('/api/log-sessions/{token}')
    def session(token: str, req: Request):
        dashboard(req)
        import uuid
        try:
            if str(uuid.UUID(token)) != token:
                raise ValueError()
        except ValueError:
            raise HTTPException(400, "Invalid tab identifier")
        with lock, db:
            db.execute("INSERT OR IGNORE INTO log_sessions VALUES(?,?)", (token, newest()))
        return {"ready": True}

    @api.post('/api/log-sessions/{token}/clear')
    def clear(token: str, req: Request):
        dashboard(req)
        with lock:
            if not db.execute("SELECT 1 FROM log_sessions WHERE token=?", (token,)).fetchone():
                raise HTTPException(404, "Session missing")
        if not approve_reset():
            raise HTTPException(403, 'Administrator approval required')
        with lock, db:
            db.execute('UPDATE log_sessions SET boundary=? WHERE token=?', (newest(), token))
        return {'cleared': True}

    @api.get('/api/log-page')
    def logs(session: str = '', q: str = '', severity: str = '', source: str = '', before: int = 0):
        with lock:
            boundary = 0
            if session:
                row = db.execute("SELECT boundary FROM log_sessions WHERE token=?", (session,)).fetchone()
                if not row:
                    raise HTTPException(404, "Session missing")
                boundary = row[0]
            clauses = ["dataset='live'", 'id>?']
            args = [boundary]
            for field, value in [('severity', severity), ('source', source)]:
                if value:
                    clauses.append(field+'=?')
                    args.append(value)
            if q:
                clauses.append("instr(lower(message||' '||source||' '||action||' '||host||' '||ip||' '||user||' '||id),lower(?))>0")
                args.append(q)
            where = ' AND '.join(clauses)
            total = db.execute('SELECT COUNT(*) FROM events WHERE '+where,args).fetchone()[0]
            if before:
                where += ' AND id<?'
                args.append(before)
            rows = db.execute('SELECT * FROM events WHERE '+where+' ORDER BY id DESC LIMIT 51',args).fetchall()
            return {'events':[event(r) for r in rows[:50]], 'total':total, 'more':len(rows)>50}


