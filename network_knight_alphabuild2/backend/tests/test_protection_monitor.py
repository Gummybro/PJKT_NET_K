import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.protection_monitor import Monitor, protection_events


class ProtectionMonitorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='backend/tests')
        self.root = Path(self.tmp.name)
        self.app = create_app(self.root / 'database')
        self.client = TestClient(self.app)
        self.monitor = Monitor(self.root / 'state.json')
        self.headers = {'Authorization': 'Bearer ' + self.app.state.key}

    def tearDown(self):
        self.client.close()
        self.app.state.db.close()
        self.tmp.cleanup()

    def transport(self, url, key, path, body):
        response = self.client.post(path, json=body, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def flush(self):
        with patch('backend.protection_monitor.post', side_effect=self.transport):
            return self.monitor.flush('http://127.0.0.1:8787', self.app.state.key)

    def test_off_initial_and_transition_alerts_without_poll_flood(self):
        self.monitor.poll(lambda: ({'defender': False, 'firewall:Public': False}, []))
        count = len(self.monitor.state['pending'])
        self.monitor.poll(lambda: ({'defender': False, 'firewall:Public': False}, []))
        self.assertEqual(len(self.monitor.state['pending']), count)
        self.monitor.poll(lambda: ({'defender': True, 'firewall:Public': True}, []))
        self.monitor.poll(lambda: ({'defender': False, 'firewall:Public': True}, []))
        self.flush()
        state = self.client.get('/api/state').json()
        self.assertEqual([a['ruleId'] for a in state['alerts']].count('WIN-010'), 2)
        self.assertEqual([a['ruleId'] for a in state['alerts']].count('WIN-011'), 1)
        self.assertIn('protection_restored', {e['action'] for e in state['events']})
        self.assertTrue(all(e['origin'] == 'collector' for e in state['events']))

    def test_unknown_status_does_not_create_false_off_alert(self):
        self.assertEqual(protection_events({}, {'defender': None}), [])
        self.assertIn('Access denied', self.monitor.poll(lambda: ({}, ['Access denied'])))
        self.flush()
        self.assertEqual(self.client.get('/api/state').json()['alerts'], [])
        self.assertEqual(self.monitor.checks, {})

    def test_restart_and_lost_ack_retries_keep_ids_and_deduplicate(self):
        self.monitor.poll(lambda: ({'defender': False}, []))
        pending = self.monitor.state['pending']
        self.client.post('/api/ingest', json={'events': pending}, headers=self.headers)
        self.monitor = Monitor(self.root / 'state.json')
        self.assertEqual(self.monitor.state['pending'], pending)
        self.assertEqual(self.flush(), 0)
        self.assertEqual(len(self.client.get('/api/state').json()['alerts']), 1)
        self.assertEqual(json.loads((self.root / 'state.json').read_text())['pending'], [])

    def test_protection_heartbeat_reports_booleans_and_clears_failed_checks(self):
        body = dict(id='protection:test', checks={'defender': True, 'firewall:Public': False})
        self.assertEqual(self.client.post('/api/heartbeat', json=body, headers=self.headers).status_code, 200)
        state = self.client.get('/api/state').json()
        self.assertEqual(state['collectors'][0]['checks'], body['checks'])
        body['checks'] = {'defender': 'false'}
        self.assertEqual(self.client.post('/api/heartbeat', json=body, headers=self.headers).status_code, 400)
        body['checks'] = {}
        self.client.post('/api/heartbeat', json=body, headers=self.headers)
        self.assertEqual(self.client.get('/api/state').json()['collectors'][0]['checks'], {})



if __name__ == '__main__':
    unittest.main()
