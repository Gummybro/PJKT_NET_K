import json
from pathlib import Path
import platform
import tempfile
import time
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from backend.app import create_app
from backend.service_control import Preferences, Supervisor, collector_status, overall_status, stamp


class FakeProcess:
    next_pid = 9000

    def __init__(self, *args, **kwargs):
        FakeProcess.next_pid += 1
        self.pid = FakeProcess.next_pid
        self.returncode = None

    def poll(self): return self.returncode
    def terminate(self): self.returncode = 0
    def kill(self): self.returncode = -1
    def wait(self, timeout=None): return self.returncode


class HealthTests(unittest.TestCase):
    def heartbeat(self, age=0, status='ok'):
        return dict(last_seen=stamp(time.time()-age), status=status, detail='isolated heartbeat fixture')

    def test_live_process_requires_fresh_heartbeat(self):
        process=dict(pid=42, started_at=time.time()-5)
        self.assertEqual(collector_status('protection',True,None,process)['state'],'starting')
        self.assertEqual(collector_status('protection',True,self.heartbeat(),process)['state'],'running')
        process['started_at']=time.time()-40
        self.assertEqual(collector_status('protection',True,self.heartbeat(31),process)['state'],'offline')

    def test_disabled_and_dead_process_override_old_healthy_data(self):
        self.assertEqual(collector_status('protection',False,self.heartbeat())['state'],'disabled')
        self.assertEqual(collector_status('protection',True,self.heartbeat(),{'error':'process exited'})['state'],'error')

    def test_restart_does_not_reuse_previous_process_heartbeat(self):
        process=dict(pid=43,started_at=time.time())
        self.assertEqual(collector_status('windows',True,self.heartbeat(10),process)['state'],'starting')

    def test_permission_and_overall_status_are_not_green(self):
        limited=collector_status('windows',True,self.heartbeat(status='degraded'))
        self.assertEqual(limited['state'],'degraded')
        self.assertEqual(overall_status([limited]),'degraded')
        self.assertEqual(overall_status([{'id':'windows','state':'disabled'}]),'partial')
        self.assertEqual(overall_status([{'id':'windows','state':'offline'}]),'attention')


class ServiceControlTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir='backend/tests')
        self.folder=Path(self.tmp.name)
        self.spawn=patch('backend.service_control.subprocess.Popen',side_effect=FakeProcess).start()
        self.manager=Supervisor(self.folder,'http://127.0.0.1:8787')

    def tearDown(self):
        self.manager.stop()
        patch.stopall()
        self.tmp.cleanup()

    def test_disable_one_component_stops_only_it_and_persists(self):
        self.manager.reconcile()
        protection=self.manager.processes['protection']
        windows=self.manager.processes['windows']
        self.manager.set_enabled('protection',False)
        self.assertIsNotNone(protection.poll())
        self.assertIsNone(windows.poll())
        self.assertFalse(Preferences(self.folder).read()['protection'])
        self.assertTrue(Preferences(self.folder).read()['windows'])
        self.manager.stop()
        self.manager=Supervisor(self.folder,'http://127.0.0.1:8787')
        self.manager.reconcile()
        self.assertNotIn('protection',self.manager.processes)
        self.assertIn('windows',self.manager.processes)

    def test_failed_process_exposed_until_explicit_restart(self):
        self.manager.reconcile()
        self.manager.processes['protection'].returncode=7
        self.manager.reconcile()
        service=next(s for s in self.manager.snapshot([]) if s['id']=='protection')
        self.assertEqual(service['state'],'error')
        previous_pid=service['pid']
        self.manager.restart('protection')
        self.assertNotEqual(self.manager.processes['protection'].pid,previous_pid)
        self.assertEqual(next(s for s in self.manager.snapshot([]) if s['id']=='protection')['state'],'starting')

    def test_config_rejects_strings_and_preserves_other_choice(self):
        settings=Preferences(self.folder)
        settings.set('windows',False)
        settings.set('protection',True)
        self.assertEqual(settings.read(),{'protection':True,'windows':False})
        with self.assertRaises(ValueError):settings.set('all','false')

    def test_api_status_control_history_and_auth(self):
        app=create_app(self.folder/'api')
        self.manager=Supervisor(self.folder/'api','http://127.0.0.1:8787')
        app.state.runtime=self.manager
        self.manager.reconcile()
        client=TestClient(app)
        header={'X-Network-Knight':'dashboard'}
        try:
            self.assertEqual(client.post('/api/services/windows',json={'enabled':False}).status_code,403)
            self.assertEqual(client.post('/api/services/windows',headers=header,json={'enabled':'false'}).status_code,400)
            self.assertEqual(client.post('/api/services/unknown',headers=header,json={'enabled':False}).status_code,404)
            before=client.get('/api/state').json()
            self.assertTrue(before['managed'])
            self.assertEqual(len(before['services']),3)
            self.assertEqual(before['events'],[])
            self.assertEqual(before['alerts'],[])
            self.assertTrue(before['service_activity'])
            auth={'Authorization':'Bearer '+app.state.key}
            for prefix in ['protection:','windows:']:
                host=platform.node().upper() if prefix=='windows:' else platform.node()
                response=client.post('/api/heartbeat',headers=auth,json={'id':prefix+host,'status':'ok','detail':'ISOLATED fixture'})
                self.assertEqual(response.status_code,200)
            live=client.get('/api/state').json()
            self.assertEqual(live['monitoring_status'],'running')
            count=len(live['service_activity'])
            self.assertEqual(len(client.get('/api/state').json()['service_activity']),count)
            client.post('/api/services/windows',headers=header,json={'enabled':False})
            after=client.get('/api/state').json()
            self.assertEqual(next(s for s in after['services'] if s['id']=='windows')['state'],'disabled')
            self.assertEqual(after['monitoring_status'],'partial')
            self.assertEqual(after['events'],[])
            self.assertEqual(after['alerts'],[])
        finally:
            client.close();self.manager.stop();app.state.db.close()

    def test_unmanaged_api_does_not_claim_to_stop_external_collectors(self):
        app=create_app(self.folder/'unmanaged')
        with TestClient(app) as client:
            response=client.post('/api/services/windows',headers={'X-Network-Knight':'dashboard'},json={'enabled':False})
            self.assertEqual(response.status_code,409)
        app.state.db.close()


if __name__=='__main__':unittest.main()
