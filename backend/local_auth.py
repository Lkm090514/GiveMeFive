"""Local development credentials and one-use launcher tickets; not a cloud account system."""
from __future__ import annotations
import hashlib,ipaddress,json,os,secrets,threading,time
from pathlib import Path

COOKIE_SECONDS=14*24*3600
TICKET_SECONDS=300

def data_instance(root):return hashlib.sha256(os.path.normcase(str(Path(root).resolve())).encode()).hexdigest()[:24]

def load_local_tokens(root):
    path=Path(root)/'local-access.json'
    try:
        with path.open('x',encoding='utf-8') as f:
            json.dump({secrets.token_urlsafe(32):{'owner_id':'local-owner','role':'admin'}},f)
        path.chmod(0o600)
    except FileExistsError:pass
    try:
        tokens=json.loads(path.read_text(encoding='utf-8'))
        if not tokens or any(not isinstance(k,str) or len(k)<24 or p.get('role') not in ('admin','student') or not p.get('owner_id') for k,p in tokens.items()):raise ValueError('invalid identity configuration')
        return tokens
    except (ValueError,AttributeError) as error:
        raise RuntimeError('本地身份文件无法读取；请保留 local-access.json 和数据库，检查文件，禁止自动重置身份。') from error

def loopback_request(request):
    try:return ipaddress.ip_address(request.client.host).is_loopback and request.url.hostname in ('localhost','127.0.0.1','::1')
    except (ValueError,AttributeError):return False

class LaunchTickets:
    def __init__(self,clock=time.time):self.clock=clock;self.items={};self.lock=threading.Lock()
    def issue(self,token):
        with self.lock:
            self.items={k:v for k,v in self.items.items() if v[1]>self.clock()}
            ticket=secrets.token_urlsafe(32);self.items[ticket]=(token,self.clock()+TICKET_SECONDS)
            return ticket
    def consume(self,ticket):
        if not isinstance(ticket,str):return None
        with self.lock:
            value=self.items.pop(ticket,None)
            return value[0] if value and value[1]>self.clock() else None
