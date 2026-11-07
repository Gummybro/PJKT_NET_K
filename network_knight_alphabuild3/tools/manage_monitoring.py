"""Enable or disable only Network Knight components, never Windows security itself."""
import argparse
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from backend.service_control import Preferences,instance_id

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('service',choices=['protection','windows','all'])
    parser.add_argument('action',choices=['on','off'])
    parser.add_argument('--url',default='http://127.0.0.1:8787')
    args=parser.parse_args()
    from urllib.parse import urlparse
    target=urlparse(args.url)
    if target.scheme!='http' or target.hostname not in ('127.0.0.1','localhost') or target.path not in ('','/') or target.username:
        parser.error('Only a local backend is supported')
    data=Path(os.environ.get('NETWORK_KNIGHT_DATA',ROOT/'backend/data'))
    enabled=args.action=='on'
    try:
        with urllib.request.urlopen(args.url+'/api/health',timeout=3) as r:health=json.load(r)
    except urllib.error.HTTPError as exc:
        print('A server is on that port but is not a compatible Network Knight instance:',exc);return 1
    except OSError:
        Preferences(data).set(args.service,enabled)
        print('Saved for the next start:',args.service,'enabled' if enabled else 'disabled')
        print('Network Knight is not running. No Windows antivirus or firewall settings were changed.')
        return 0
    if health.get('instance_id')!=instance_id(data) or not health.get('managed'):
        print('Another or older server is on that port. Use the matching unified launcher before controlling components.');return 1
    request=urllib.request.Request(args.url+'/api/services/'+args.service,data=json.dumps({'enabled':enabled}).encode(),
        headers={'Content-Type':'application/json','X-Network-Knight':'dashboard'},method='POST')
    try:
        with urllib.request.urlopen(request,timeout=20) as r:json.load(r)
    except urllib.error.HTTPError as exc:
        print('Component change failed:',exc.read().decode());return 1
    print('Network Knight component:',args.service,'enabled' if enabled else 'disabled')
    print('The dashboard will update automatically. Windows antivirus/firewall settings are unchanged.')
    return 0
if __name__=='__main__':sys.exit(main())
