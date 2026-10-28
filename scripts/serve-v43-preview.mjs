import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../',import.meta.url)),args=process.argv.slice(2),managed=args.includes('--strictPort');
const child=managed?spawn(root+'.venv/bin/python',['scripts/online-preview.py',...args.filter(x=>x!=='--open')],{cwd:root,stdio:'inherit',env:{...process.env,SITES_MANAGED_LINUX_CONTAINER:'1',PYTHONHOME:root+'preview-runtime-python',PYTHONPATH:root+'.venv/lib/python3.12/site-packages'}}):spawn(process.execPath,['scripts/serve.mjs',...args],{cwd:root,stdio:'inherit'});
child.on('exit',code=>process.exit(code??1));
