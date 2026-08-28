import { chromium } from 'playwright';
import fs from 'node:fs';
const BASE='https://dpromstk2000-lab.github.io/dpro-buyback-line/';
const WIDTHS=[1440,1024,390,320];
const heights={1440:1080,1024:768,390:720,320:720};
const WRITE_METHODS=new Set(['POST','PUT','PATCH','DELETE']);
const SESSION_PATTERNS=[/\/api\/admin\/login(?:\?|$)/,/\/api\/staff\/session\/(?:issue|revoke)(?:\?|$)/];
const results=[];let overall=true;
for(const width of WIDTHS){
  const browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width,height:heights[width]}});
  const pageErrors=[],consoleErrors=[],businessMutations=[],sessionRequests=[];
  page.on('pageerror',e=>pageErrors.push(String(e)));
  page.on('console',m=>{if(m.type()==='error')consoleErrors.push(m.text())});
  page.on('request',req=>{const method=req.method().toUpperCase();if(!WRITE_METHODS.has(method))return;const rec={method,url:req.url()};if(SESSION_PATTERNS.some(r=>r.test(req.url())))sessionRequests.push(rec);else businessMutations.push(rec)});
  const checks={};
  await page.goto(`${BASE}guide-center.html?qa=${Date.now()}-${width}`,{waitUntil:'domcontentloaded',timeout:30000});
  await page.waitForFunction(()=>window.__DPRO_GUIDE_QA__?.canonical?.steps?.length===10,null,{timeout:15000});
  checks.metrics=await page.evaluate(()=>({innerWidth,documentElementScrollWidth:document.documentElement.scrollWidth,bodyScrollWidth:document.body.scrollWidth,version:window.__DPRO_GUIDE_QA__.version,domCount:document.querySelectorAll('#first10Grid .first10-card').length,canonicalCount:window.__DPRO_GUIDE_QA__.canonical.steps.length}));
  checks.currentVersion=checks.metrics.version==='DPRO_TUTORIAL_R4_GUIDE_CENTER_V1_0';
  checks.exact10=checks.metrics.domCount===10&&checks.metrics.canonicalCount===10;
  checks.noOverflow=checks.metrics.documentElementScrollWidth<=checks.metrics.innerWidth&&checks.metrics.bodyScrollWidth<=checks.metrics.innerWidth;
  checks.canonicalContent=await page.evaluate(()=>window.__DPRO_GUIDE_QA__.canonical.steps.every((s,i)=>{const c=document.querySelectorAll('#first10Grid .first10-card')[i];return c&&Number(c.dataset.step)===s.step&&c.querySelector('h3')?.textContent===s.title&&c.querySelector('.guidance')?.textContent===s.guidance&&c.querySelector('.safety')?.textContent.includes(s.safety)}));
  checks.moreGuidesOutsideFirst10=await page.evaluate(()=>document.querySelectorAll('#moreGuides .first10-card').length===0&&document.querySelectorAll('#moreGuides .guide-link').length>=2);
  checks.routes=await page.evaluate(()=>({start:'tutorial.html',resume:'tutorial.html',replay:'tutorial.html',ownerIpad:document.getElementById('ownerIpadLink')?.getAttribute('href'),productSite:document.getElementById('productSiteLink')?.getAttribute('href')}));
  checks.guideRoutes=checks.routes.ownerIpad==='owner-ipad.html?demo=1'&&checks.routes.productSite==='https://dpromstk2000-lab.github.io/dpro-line-systems-site/systems/buyback.html';
  await page.evaluate(()=>localStorage.removeItem(window.__DPRO_GUIDE_QA__.storageKey));
  const startDest=await page.evaluate(()=>window.__DPRO_GUIDE_QA__.start(false));
  const startState=await page.evaluate(()=>window.__DPRO_GUIDE_QA__.state);
  checks.startAlignment=startDest==='tutorial.html'&&startState.step===0&&startState.completed===false&&startState.closed===false&&startState.skipped===false;
  await page.evaluate(()=>localStorage.setItem(window.__DPRO_GUIDE_QA__.storageKey,JSON.stringify({step:6,completed:false,closed:false,updatedAt:'qa'})));
  const beforeResume=await page.evaluate(()=>localStorage.getItem(window.__DPRO_GUIDE_QA__.storageKey));
  const resumeDest=await page.evaluate(()=>window.__DPRO_GUIDE_QA__.resume(false));
  const afterResume=await page.evaluate(()=>localStorage.getItem(window.__DPRO_GUIDE_QA__.storageKey));
  checks.resumeAlignment=resumeDest==='tutorial.html'&&beforeResume===afterResume&&JSON.parse(afterResume).step===6;
  const replayDest=await page.evaluate(()=>window.__DPRO_GUIDE_QA__.replay(false));
  const replayState=await page.evaluate(()=>localStorage.getItem(window.__DPRO_GUIDE_QA__.storageKey));
  checks.replayAlignment=replayDest==='tutorial.html'&&replayState===null;
  await page.keyboard.press('Home');
  await page.evaluate(()=>document.activeElement?.blur());
  let focusSequence=[];
  for(let i=0;i<5;i++){await page.keyboard.press('Tab');focusSequence.push(await page.evaluate(()=>({id:document.activeElement?.id||'',tag:document.activeElement?.tagName||'',outline:getComputedStyle(document.activeElement).outlineStyle})))}
  checks.keyboardFocus=focusSequence.slice(0,3).map(x=>x.id).join(',')==='startBtn,resumeBtn,replayBtn'&&focusSequence.slice(0,3).every(x=>x.outline!=='none');
  const linkRouteChecks=[];
  for(const path of ['guide-center.html','tutorial.html','demo-guide.html','owner-ipad.html?demo=1']){
    try{const res=await page.request.get(BASE+path,{timeout:20000});linkRouteChecks.push({path,status:res.status(),ok:res.ok()})}catch(e){linkRouteChecks.push({path,status:0,ok:false,error:String(e)})}
  }
  checks.linkRoutes=linkRouteChecks;
  checks.linkRoutesOk=linkRouteChecks.every(x=>x.ok);
  checks.businessMutation0=businessMutations.length===0;
  checks.pageErrors0=pageErrors.length===0;
  checks.consoleErrors0=consoleErrors.length===0;
  const pass=checks.currentVersion&&checks.exact10&&checks.noOverflow&&checks.canonicalContent&&checks.moreGuidesOutsideFirst10&&checks.guideRoutes&&checks.startAlignment&&checks.resumeAlignment&&checks.replayAlignment&&checks.keyboardFocus&&checks.linkRoutesOk&&checks.businessMutation0&&checks.pageErrors0&&checks.consoleErrors0;
  overall&&=pass;results.push({width,pass,checks,pageErrors,consoleErrors,businessMutations,sessionRequests});
  await browser.close();
}
const report={version:'DPRO_TUTORIAL_R4_QA_V1',checkedAt:new Date().toISOString(),base:BASE,overall,results};
fs.writeFileSync('r4-live-qa.json',JSON.stringify(report,null,2));
console.log(JSON.stringify(report,null,2));
if(!overall)process.exit(1);
