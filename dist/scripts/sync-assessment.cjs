// Refresh the integrated build from the verified original GMF build; keep integration theme files.
const fs=require('node:fs'),path=require('node:path');
const source=process.argv[2];if(!source)throw new Error('Usage: node scripts/sync-assessment.cjs <original-GMF-build-directory>');
const from=path.resolve(source),root=path.resolve(__dirname,'..'),target=path.join(root,'assessment');
if(!fs.existsSync(path.join(from,'index.html'))||!fs.existsSync(path.join(from,'assets')))throw new Error('An existing GMF static build is required');
if(!target.startsWith(root+path.sep))throw new Error('Invalid integration target');
for(const file of ['learning-bridge.js','learning-bridge.css'])if(!fs.existsSync(path.join(target,file)))throw new Error('Missing tracked integration theme: '+file);
fs.cpSync(from,target,{recursive:true});
const index=path.join(target,'index.html'),html=fs.readFileSync(index,'utf8');
fs.writeFileSync(index,html.replace('</head>','<link rel="stylesheet" href="../shared-shell.css"><link rel="stylesheet" href="./learning-bridge.css"><script src="../learning-store.js"></script><script src="../study-sessions.js"></script><script src="../shared-shell.js"></script><script src="./learning-bridge.js"></script></head>'));
fs.writeFileSync(path.join(root,'data','app-shell.json'),JSON.stringify([...fs.readdirSync(path.join(target,'assets')).filter(f=>fs.statSync(path.join(target,'assets',f)).isFile()).map(f=>'assessment/assets/'+f),'data/app-shell.json','mind-flow/pathline-bridge.js']));
console.log('Assessment build updated locally. No publication or upload.');
