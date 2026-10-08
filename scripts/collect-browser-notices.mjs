import {readFileSync,readdirSync,writeFileSync,existsSync} from 'node:fs';
import {resolve,join} from 'node:path';

const root=resolve('sites');
const lock=JSON.parse(readFileSync(join(root,'package-lock.json'),'utf8'));
const notices=['Dove browser dependency notices\n\nOriginal Dove source uses the separate root MIT license. Dependencies retain their own terms. The sections below preserve license/notice files and package metadata from the installed locked browser runtime dependencies. Optional packages not installed on this platform are not copied. Vendored source notices remain beside their source files.\n'];
let count=0;
for(const [name,item] of Object.entries(lock.packages).sort(([a],[b])=>a.localeCompare(b))){
 if(!name||item.dev)continue;
 const location=join(root,name);
 if(!existsSync(location))continue;
 const metadata=JSON.parse(readFileSync(join(location,'package.json'),'utf8'));
 notices.push('\n'+'='.repeat(72)+'\n'+metadata.name+' '+metadata.version+'\n'+JSON.stringify({license:metadata.license,author:metadata.author,contributors:metadata.contributors,repository:metadata.repository},null,2)+'\n');
 const files=readdirSync(location).filter(filename=>/^(licen[sc]e|notice|copying|copyright)/i.test(filename));
 for(const filename of files){const path=join(location,filename);try{const text=readFileSync(path,'utf8');notices.push('\n--- '+filename+' ---\n'+text+'\n')}catch(error){if(error.code!=='EISDIR')throw error}}
 count++;
}
writeFileSync(join(root,'THIRD-PARTY-NOTICES.txt'),notices.join(''));
console.log('Collected installed runtime notices for '+count+' locked packages.');
