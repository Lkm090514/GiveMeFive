"""Explicit remote sharing tool, NOT a normal local startup entry. Requires separate authorization."""
from __future__ import annotations
import argparse,json,os,platform,re,socket,subprocess,sys,time,urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def stop(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try:process.wait(timeout=8)
        except subprocess.TimeoutExpired:process.kill();process.wait()

def executable(override=None):
    if override:return Path(override).resolve()
    system=platform.system();machine=platform.machine().lower()
    arch={'amd64':'amd64','x86_64':'amd64','arm64':'arm64','aarch64':'arm64'}.get(machine)
    if system not in ('Windows','Linux') or not arch:
        raise RuntimeError('此启动器支持 Windows/Linux 64 位；其他系统请自行安装 cloudflared 后用 --cloudflared 指定。')
    filename=f'cloudflared-{system.lower()}-{arch}'+('.exe' if system=='Windows' else '')
    folder=ROOT/'runtime'/'preview-tools';folder.mkdir(parents=True,exist_ok=True)
    target=folder/filename
    if not target.exists():
        print('正在从 Cloudflare 官方 GitHub 下载临时隧道程序（首次运行）…',flush=True)
        partial=target.with_suffix('.download')
        try:
            with urllib.request.urlopen('https://github.com/cloudflare/cloudflared/releases/latest/download/'+filename,timeout=90) as response,partial.open('wb') as output:
                while block:=response.read(1024*1024):output.write(block)
            if partial.stat().st_size<1024*1024:raise RuntimeError('隧道程序下载不完整')
            partial.replace(target)
            if system!='Windows':target.chmod(0o700)
        finally:
            if partial.exists():partial.unlink()
    return target

def main():
    parser=argparse.ArgumentParser(description='GiveMeFive 临时 HTTPS 预览，不注册云账号，不修改线上站。')
    parser.add_argument('--email',help='唯一允许访问的邮箱，首次访问会收取 Cloudflare 验证码')
    parser.add_argument('--cloudflared',help='已安装的 cloudflared 可执行文件')
    parser.add_argument('--data-dir',type=Path,default=ROOT/'runtime'/'v4')
    args=parser.parse_args()
    email=(args.email or input('请输入唯一允许访问的邮箱（不是注册账号）：')).strip()
    if not re.fullmatch(r'[^\s,@*]+@[^\s,@*]+\.[^\s,@*]+',email):raise RuntimeError('请填写一个完整邮箱，不允许通配符。')
    binary=executable(args.cloudflared)
    help_text=subprocess.run([str(binary),'tunnel','--help'],capture_output=True,text=True,check=True).stdout
    if '--allowed-mail' not in help_text:
        raise RuntimeError('此 cloudflared 太旧，不支持邮箱保护。请更新；启动器不会降级为公开隧道。')
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    data=args.data_dir.resolve();data.mkdir(parents=True,exist_ok=True)
    environment=os.environ.copy();environment.pop('GMF_API_TOKENS',None)
    environment.update({'GMF_QA_FIXTURE':'0','GMF_DATA_DIR':str(data),'PYTHONUNBUFFERED':'1',
        'PYTHONPATH':str(ROOT)+os.pathsep+str(ROOT/'as-v3-reference')+os.pathsep+environment.get('PYTHONPATH','')})
    # A single server serves every UI route, API, original image and PDF upload.
    origin=f'http://127.0.0.1:{port}'
    local=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    server=tunnel=None
    log=(data/'preview-server.log').open('w',encoding='utf-8')
    try:
        server=subprocess.Popen([sys.executable,'-m','uvicorn','backend.app:create_app','--factory','--host','127.0.0.1','--port',str(port),'--no-access-log'],cwd=ROOT,env=environment,stdout=log,stderr=subprocess.STDOUT)
        for _ in range(100):
            if server.poll() is not None:raise RuntimeError('Python 服务启动失败，请查看 '+str(data/'preview-server.log'))
            try:
                with local.open(origin+'/api/v4/health',timeout=1) as response:
                    if response.status==200:break
            except OSError:time.sleep(.2)
        else:raise RuntimeError('Python 服务未在 20 秒内就绪，请查看 preview-server.log。')
        credentials=json.loads((data/'local-access.json').read_text())
        token=next((key for key,value in credentials.items() if value['role']=='admin'),None)
        if not token:raise RuntimeError('当前本地身份配置没有管理员。')
        print('Fusion 页面与真实 AS V4 API 已在同一入口就绪；正在申请邮箱保护的 HTTPS 链接…',flush=True)
        tunnel=subprocess.Popen([str(binary),'tunnel','--url',origin,'--allowed-mail',email,'--no-autoupdate'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',bufsize=1)
        shared=False;hostname=None
        for line in tunnel.stdout:
            # Error messages contain https://api.trycloudflare.com: it is NOT a preview URL.
            match=re.search(r'https://[a-z0-9]+(?:-[a-z0-9]+)+\.trycloudflare\.com\b',line)
            if match and 'failed' not in line.lower() and 'ERR' not in line:hostname=match.group(0)
            if hostname and 'Registered tunnel connection' in line and not shared:
                print('\n第一步，在 iPad Safari 打开邮箱验证入口：\n'+hostname+'/',flush=True)
                print('\n第二步，完成邮箱验证码后，在同一个 Safari 打开完整验收链接：\n'+hostname+'/local-login#'+token,flush=True)
                print('\n链接仅限本人验收，包含本机管理员权限，请勿转发。\n保持电脑联网、保持窗口打开；按 Ctrl+C 停止。\n链接每次启动可能变化，个人上传与作答保留在 runtime/v4。\n',flush=True)
                shared=True
            elif 'ERR' in line or 'failed' in line.lower():print(line.rstrip(),flush=True)
        if not shared:raise RuntimeError('未能建立临时 HTTPS 隧道。检查网络是否允许 Cloudflare Tunnel；没有改用公开隧道。')
        if tunnel.wait()!=0:raise RuntimeError('隧道已中断，重新启动可生成新链接。')
    finally:
        stop(tunnel);stop(server);log.close()

if __name__=='__main__':
    try:main()
    except KeyboardInterrupt:print('\n临时预览已停止，题库与作答保留。')
    except Exception as error:print('\n预览未建立：'+str(error),file=sys.stderr);sys.exit(1)
