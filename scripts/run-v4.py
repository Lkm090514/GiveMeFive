"""One complete local server; ready-check, reuse and initialize identity before opening."""
from pathlib import Path
import argparse,json,os,socket,sys,threading,time,urllib.error,urllib.request,webbrowser
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'as-v3-reference')]
from backend.local_auth import data_instance

HTTP=urllib.request.build_opener(urllib.request.ProxyHandler({}))

def call(origin,path,token=None):
    headers={'Authorization':'Bearer '+token} if token else {}
    request=urllib.request.Request(origin+path,headers=headers,method='POST' if token else 'GET')
    with HTTP.open(request,timeout=3) as response:return json.load(response)

def running_service(origin,root):
    try:health=call(origin,'/api/v4/health')
    except (OSError,ValueError):return False
    if health.get('service')!='givemefive-python' or health.get('startup_protocol')!=2 or health.get('data_instance')!=data_instance(root):
        raise RuntimeError('该端口运行的是旧版服务或另一份项目。请先关闭对应启动窗口，再运行本项目的启动器；不会覆盖其数据。')
    if health.get('auth_mode')!='local':raise RuntimeError('该服务使用独立身份配置，不能通过本机管理员启动入口接管。')
    return True

def initialize_browser(origin,root,open_browser=False,link_file=None):
    tokens=json.loads((root/'local-access.json').read_text(encoding='utf-8'))
    token=next((k for k,v in tokens.items() if v.get('role')=='admin'),None)
    if not token:raise RuntimeError('本地身份文件中没有管理员。请保留原文件及数据库，不要重置。')
    # The printed ticket remains usable even after the default browser consumes its own ticket.
    url=origin+call(origin,'/api/v4/local-launch',token)['login_path']
    target=Path(link_file) if link_file else root/'last-launch.json';target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps({'url':url,'expires_at':time.time()+300,'origin':origin}),encoding='utf-8');target.chmod(0o600)
    print('完整网站与题库已就绪。\n本机手动登录入口（五分钟有效、使用一次；请勿转发）：\n'+url,flush=True)
    if open_browser:
        auto_url=origin+call(origin,'/api/v4/local-launch',token)['login_path']
        webbrowser.open(auto_url)
    return url

def main(argv=None):
    p=argparse.ArgumentParser(description='GiveMeFive 完整本地启动器（前端 + Python API + 本机登录）')
    p.add_argument('--port',type=int,default=int(os.getenv('PORT',4173)))
    p.add_argument('--host',default='127.0.0.1')
    p.add_argument('--open',action=argparse.BooleanOptionalAction,default=False)
    p.add_argument('--link-file',type=Path,help='仅用于本机验收；记录短期登录入口，不包含长期令牌')
    args=p.parse_args(argv)
    if args.host not in ('127.0.0.1','localhost','::1') or os.getenv('GMF_AUTH_MODE','local')!='local' or os.getenv('GMF_QA_FIXTURE')=='1' or os.getenv('GMF_API_TOKENS'):
        raise RuntimeError('此入口仅用于本机开发。独立认证/QA 服务请使用明确的独立配置启动，不能复用本机管理员入口。')
    root=Path(os.getenv('GMF_DATA_DIR',ROOT/'runtime/v4')).resolve();origin=f'http://localhost:{args.port}'
    if running_service(origin,root):initialize_browser(origin,root,args.open,args.link_file);return 0
    # A closed Windows port may time out on connect rather than refuse immediately.
    # Probe binding, without listening or leaving a process behind.
    try:
        with socket.socket(socket.AF_INET6 if ':' in args.host else socket.AF_INET) as probe:
            if hasattr(socket,'SO_EXCLUSIVEADDRUSE'):probe.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
            probe.bind((args.host,args.port))
    except OSError as error:raise RuntimeError(f'端口 {args.port} 已被占用，且不是本项目的完整服务。请关闭占用程序或用 --port 指定其他端口。') from error
    from backend.app import create_app
    import uvicorn
    app=create_app(root)
    def ready():
        try:
            for _ in range(100):
                try:
                    if running_service(origin,root):break
                except OSError:pass
                time.sleep(.1)
            else:raise RuntimeError('服务未在十秒内就绪。请查看启动窗口中的服务错误。')
            initialize_browser(origin,root,args.open,args.link_file)
        except Exception as error:print('启动入口未完成：'+str(error),file=sys.stderr,flush=True)
    threading.Thread(target=ready,daemon=True).start()
    print('正在启动完整 GiveMeFive；请保留此窗口。按 Ctrl+C 停止。',flush=True)
    uvicorn.run(app,host=args.host,port=args.port,access_log=True)
    return 0

if __name__=='__main__':
    if not sys.flags.utf8_mode:os.execv(sys.executable,[sys.executable,'-X','utf8',*sys.argv])
    try:raise SystemExit(main())
    except KeyboardInterrupt:pass
    except (RuntimeError,OSError) as error:print('无法启动：'+str(error),file=sys.stderr);raise SystemExit(1)
