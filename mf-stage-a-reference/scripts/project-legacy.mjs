import {readFileSync,writeFileSync,realpathSync} from 'node:fs';
import {resolve} from 'node:path';
import {projectLegacyRun} from '../src/legacy.mjs';
const [input,sourceKey,output]=process.argv.slice(2);
if (!input || !sourceKey || !output) {
  console.error('Usage: node scripts/project-legacy.mjs INPUT.json IMMUTABLE_SOURCE_KEY OUTPUT.json');
  process.exitCode=2;
} else {
  try {
    if (realpathSync(input) === resolve(output)) throw Error('Output must not be the source');
    const projection=projectLegacyRun(readFileSync(input,'utf8'),sourceKey);
    writeFileSync(output,JSON.stringify(projection,null,2)+'\n',{flag:'wx'});
    console.log(projection.status);
  } catch(error) {console.error(error.message);process.exitCode=1;}
}
