// V7 recovery: verified V5 identities, latest V6 content, explicit CLI image replacement.
// No database/source changes. Journal every request; uncertain failures stop for readback.
import {readFile,writeFile,copyFile,mkdir} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {isDeepStrictEqual as eq} from 'node:util';
import {fileURLToPath} from 'node:url';
import {runCLI} from '/Users/zhaoolee/github/PicLex/deck-workbench/scripts/workbench-cli.mjs';
const root = new URL('../',import.meta.url), wf=new URL('workflow/',root);
const deckID='121d190a-5d4c-4a09-8d50-4741acdbbb1b';
const read=async p=>JSON.parse(await readFile(new URL(p,wf),'utf8'));
const save=async(p,x)=>writeFile(new URL(p,wf),JSON.stringify(x,null,2)+'\n');
const journalPath=new URL('V7-image-replacement-journal.json',wf);
const fail=m=>{throw new Error(m)};
const protectedFields=c=>Object.fromEntries(Object.entries(c).filter(([k])=>k!=='assetID'));
async function api(url,body){
 const r=await fetch('http://127.0.0.1:18100/api/decks/'+deckID+url,{method:'POST',headers:{'Content-Type':'application/json','X-Workbench':'1',Origin:'http://127.0.0.1:18100'},body:JSON.stringify(body)});
 const x=await r.json(); if(!r.ok) fail('Restore failed '+r.status+' '+JSON.stringify(x)); return x;
}
let journal;
try {
 const before=await read('V7-before-migration.json'), baseline=await read('inversion-current-before.json');
 const map=(await read('inversion-card-map.json')).cards;
 const manifest=(await read('inversion-manifest.json')).cards;
 const original=new Map(baseline.draft.cards.map(c=>[c.id,c]));
 const latest=new Map(before.draft.cards.map(c=>[c.id,c]));
 if(map.length!==32||before.draft.cards.length!==32) fail('Unexpected card count');
 for(const m of map){
  const a=original.get(m.originalID),b=latest.get(m.newID);
  if(!a||!b) fail('Missing mapped identity '+m.wid);
  const stripped=c=>Object.fromEntries(Object.entries(c).filter(([k])=>!['id','assetID','createdAt'].includes(k)));
  if(!eq(stripped(a),stripped(b))) fail('User content differs; review required '+m.wid);
  const file=await readFile(new URL('images/inverted/'+m.wid+'.png',root));
  const hash=createHash('sha256').update(file).digest('hex');
  if(hash!==manifest.find(x=>x.card===m.wid)?.invertedSHA256) fail('Image hash differs '+m.wid);
 }
 if(!eq({...before.draft,cards:[],coverID:null},{...baseline.draft,cards:[],coverID:null})) fail('Metadata differs; review required');
 if(existsSync(journalPath)) journal=JSON.parse(await readFile(journalPath,'utf8'));
 else journal={deckID,startedAtUTC:new Date().toISOString(),phase:'ready',cards:[]};
 if(journal.pending) fail('Pending request: read latest draft manually before resuming');
 let current=await runCLI(['decks','get','--deck',deckID]);
 if(journal.phase==='ready'){
  if(!eq(current,before)) fail('Draft changed since backup');
  journal.pending={operation:'restore',revision:current.revision}; await save('V7-image-replacement-journal.json',journal);
  current=await api('/releases/5/restore',{revision:current.revision});
  if(!eq(current.draft,baseline.draft)) fail('Restored V5 differs from reviewed baseline');
  await save('V7-restored-original-identities.json',current);
  journal.pending=null; journal.phase='replacing'; await save('V7-image-replacement-journal.json',journal);
 }
 await mkdir(new URL('V7-image-stage/',wf),{recursive:true});
 for(const m of map){
  const old=original.get(m.originalID), card=current.draft.cards.find(c=>c.id===m.originalID);
  if(!card||!eq(protectedFields(card),protectedFields(old))) fail('Protected fields changed '+m.wid);
  const done=journal.cards.find(x=>x.cardID===m.wid);
  if(done){ if(card.assetID!==done.assetID) fail('Completed card changed '+m.wid); continue; }
  if(card.assetID!==m.originalAssetID) fail('Unknown image binding '+m.wid);
  const file=new URL('V7-image-stage/'+encodeURIComponent(old.filename),wf);
  await copyFile(new URL('images/inverted/'+m.wid+'.png',root),file);
  journal.pending={operation:'replace',cardID:m.wid,photoID:old.id,revision:current.revision,expectedAssetID:card.assetID};
  await save('V7-image-replacement-journal.json',journal);
  const started=Date.now();
  const result=await runCLI(['photos','replace','--deck',deckID,'--photo',old.id,'--revision',String(current.revision),'--file',fileURLToPath(file)]);
  if(!eq(protectedFields(result.photo),protectedFields(old))) fail('Replacement changed protected fields '+m.wid);
  if(result.photo.assetID!==m.newAssetID) fail('Replacement transcoding differs from prior inverted resource '+m.wid);
  journal.cards.push({cardID:m.wid,photoID:old.id,previousAssetID:old.assetID,assetID:result.photo.assetID,revision:result.revision,wallMs:Date.now()-started,completedAtUTC:new Date().toISOString()});
  journal.pending=null; await save('V7-image-replacement-journal.json',journal);
  current.revision=result.revision;
  current.draft.cards=current.draft.cards.map(c=>c.id===old.id?result.photo:c);
  console.log(m.wid+' replaced, original ID preserved; revision '+current.revision);
 }
 current=await runCLI(['decks','get','--deck',deckID]);
 if(!eq(current.draft.cards.map(c=>c.id),baseline.draft.cards.map(c=>c.id))) fail('Card identity/order differs');
 for(const c of current.draft.cards){
  if(!eq(protectedFields(c),protectedFields(original.get(c.id)))) fail('Final protected content differs');
 }
 if(current.draft.coverID!==baseline.draft.coverID) fail('Cover identity differs');
 const check=await runCLI(['check','--deck',deckID]);
 await save('V7-after-image-replacement.json',current); await save('V7-check.json',check);
 journal.phase='done'; journal.finishedAtUTC=new Date().toISOString(); journal.finalRevision=current.revision;
 await save('V7-image-replacement-journal.json',journal);
 console.log(JSON.stringify({status:'done',cards:journal.cards.length,revision:current.revision,check}));
} catch(e){
 if(journal){journal.error=String(e.message); await save('V7-image-replacement-journal.json',journal);}
 console.error(e.message); process.exitCode=1;
}
