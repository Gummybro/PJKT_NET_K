import tempfile
import unittest
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app import create_app


class LogSessionTests(unittest.TestCase):
    def test_session_boundaries_and_retention(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temp:
            app = create_app(temp)
            try:
                with TestClient(app) as client:
                    headers = {'X-Network-Knight':'dashboard'}
                    def collect(action):
                        response = client.post('/api/ingest', headers={'Authorization':'Bearer '+app.state.key},
                            json={'events':[{'source':'windows:Security','action':action,'message':'isolated test'}]})
                        self.assertEqual(response.status_code,200)
                    def start():
                        token = str(uuid4())
                        self.assertEqual(client.post('/api/log-sessions/'+token,headers=headers).status_code,200)
                        return token
                    def count(token=''):
                        return client.get('/api/log-page',params={'session':token}).json()['total']
                    collect('windows_event')
                    first = start()
                    collect('workstation_locked')
                    second = start()
                    self.assertEqual((count(first),count(second),count()),(1,0,2))
                    target='/api/log-sessions/'+first+'/clear'
                    self.assertEqual(client.post(target).status_code,403)
                    with patch('backend.log_sessions.approve_reset',return_value=False):
                        self.assertEqual(client.post(target,headers=headers).status_code,403)
                    self.assertEqual(count(first),1)
                    collect('windows_event')
                    with patch('backend.log_sessions.approve_reset',return_value=True):
                        self.assertEqual(client.post(target,headers=headers).status_code,200)
                    self.assertEqual((count(first),count(second),count()),(0,1,3))
                    self.assertEqual(client.get('/api/state').json()['alerts'][0]['ruleId'],'WIN-012')
            finally:
                app.state.db.close()
