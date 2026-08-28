import { chromium } from 'playwright';
import fs from 'fs';
const BASE='https://dpromstk2000-lab.github.io/dpro-buyback-line/';
const widths=[1440,1024,390,320];
const results=[];
let overall=true;
const isWrite=m=>['POST','PUT','PATCH','DELETE'].includes(m);
const isSessionOnly=url=>{
  try{
    const u=new URL(url);
    return /\/api\/admin\/login$/.test(u.pathname)||/\/api\/staff\/session\/(issue|revoke)$/.test(u.pathname);
  }catch{return false}
};
for (const width of widths){
 const browser=await chromium.launch({headless:true});
 const context=await browser.newContext({viewport:{width,height:Math.max(720,Math.round(width*0.75))},hasTouch:width<=390,isMobile:false});
 const page=await context.newPage();
 const pageErrors=[],consoleErrors=[],businessMutations=[],sessionRequests=[];
 page.on('pageerror',e=>pageErrors.push(String(e)));
 page.on('console',m=>{if(m.type()==='error')consoleErrors.push(m.text())});
 page.on('request',r=>{if(isWrite(r.method())){const row={method:r.method(),url:r.url()};if(isSessionOnly(r.url()))sessionRequests.push(row);else businessMutations.push(row)}});
 const checks={};
 try{
  await page.goto(BASE+'tutorial.html?qa='+Date.now(),{waitUntil:'domcontentloaded',timeout:60000});
  await page.waitForFunction(()=>window.__DPRO_TUTORIAL_QA__?.stepCount===10,null,{timeout:30000});
  await page.waitForTimeout(1000);
  const metrics=await page.evaluate(()=>({innerWidth:window.innerWidth,innerHeight:window.innerHeight,documentElementScrollWidth:document.documentElement.scrollWidth,bodyScrollWidth:document.body.scrollWidth,stepCount:window.__DPRO_TUTORIAL_QA__.stepCount,version:window.__DPRO_TUTORIAL_QA__.version}));
  checks.metrics=metrics;
  checks.exact10=metrics.stepCount===10;
  checks.currentVersion=metrics.version==='DPRO_TUTORIAL_R3_V1_4';
  checks.noOverflow=metrics.documentElementScrollWidth<=metrics.innerWidth&&metrics.bodyScrollWidth<=metrics.innerWidth;
  const targets=[];
  for(let i=0;i<10;i++){
    await page.evaluate(i=>window.__DPRO_TUTORIAL_QA__.goTo(i),i);
    await page.waitForFunction(()=>window.__DPRO_TUTORIAL_QA__?.targetFound&&getComputedStyle(document.getElementById('dproTargetHighlight')).display!=='none',null,{timeout:18000}).catch(()=>{});
    targets.push(await page.evaluate(()=>({step:window.__DPRO_TUTORIAL_QA__.current+1,found:window.__DPRO_TUTORIAL_QA__.targetFound,highlight:getComputedStyle(document.getElementById('dproTargetHighlight')).display!=='none'})));
  }
  checks.targets=targets;
  checks.targetFallback=targets.every(x=>x.found&&x.highlight);
  await page.evaluate(()=>window.__DPRO_TUTORIAL_QA__.goTo(0));await page.waitForTimeout(400);
  let before=await page.evaluate(()=>window.__DPRO_TUTORIAL_QA__.cardRect);
  const h=page.locator('#dragHandle');
  const box=await h.boundingBox(); if(!box)throw new Error('drag handle not visible');
  await page.mouse.move(box.x+20,box.y+15);await page.mouse.down();await page.mouse.move(box.x+90,box.y+70,{steps:4});await page.mouse.up();
  let after=await page.evaluate(()=>window.__DPRO_TUTORIAL_QA__.cardRect);
  checks.mouseDrag=after.left!==before.left||after.top!==before.top;
  const tbox=await h.boundingBox(); if(!tbox)throw new Error('touch drag handle not visible');
  await h.dispatchEvent('pointerdown',{pointerId:77,pointerType:'touch',button:0,clientX:tbox.x+15,clientY:tbox.y+15});
  await h.dispatchEvent('pointermove',{pointerId:77,pointerType:'touch',clientX:tbox.x+55,clientY:tbox.y+55});
  await h.dispatchEvent('pointerup',{pointerId:77,pointerType:'touch',clientX:tbox.x+55,clientY:tbox.y+55});
  let touchAfter=await page.evaluate(()=>window.__DPRO_TUTORIAL_QA__.cardRect);
  checks.touchPointerDrag=touchAfter.left!==after.left||touchAfter.top!==after.top;
  await page.evaluate(()=>{const c=document.getElementById('tutorialCard');c.style.left='99999px';c.style.top='99999px';window.__DPRO_TUTORIAL_QA__.clampCard()});
  const cl=await page.evaluate(()=>{const r=window.__DPRO_TUTORIAL_QA__.cardRect;return {...r,innerWidth:window.innerWidth,innerHeight:window.innerHeight}});
  checks.viewportClamp=cl.left>=0&&cl.top>=0&&cl.right<=cl.innerWidth+0.5&&cl.bottom<=cl.innerHeight+0.5;
  await page.evaluate(()=>window.__DPRO_TUTORIAL_QA__.goTo(0));
  await page.locator('#nextBtn').focus();await page.keyboard.press('Enter');await page.waitForTimeout(500);
  checks.keyboardNext=(await page.evaluate(()=>window.__DPRO_TUTORIAL_QA__.current))===1;
  await page.locator('#backBtn').focus();await page.keyboard.press('Space');await page.waitForTimeout(250);
  checks.back=(await page.evaluate(()=>window.__DPRO_TUTORIAL_QA__.current))===0;
  const focusStyle=await page.locator('#nextBtn').evaluate(el=>{el.focus();const s=getComputedStyle(el);return {active:document.activeElement===el,outline:s.outlineStyle,outlineWidth:s.outlineWidth}});
  checks.focus=focusStyle.active&&focusStyle.outline!=='none'&&focusStyle.outlineWidth!=='0px';
  await page.keyboard.press('Escape');checks.escClose=await page.evaluate(()=>document.body.classList.contains('closed'));
  await page.locator('#reopen').press('Enter');checks.resumeReopen=await page.evaluate(()=>!document.body.classList.contains('closed'));
  await page.evaluate(()=>window.__DPRO_TUTORIAL_QA__.goTo(4));await page.waitForTimeout(500);
  await page.reload({waitUntil:'domcontentloaded'});await page.waitForFunction(()=>window.__DPRO_TUTORIAL_QA__?.stepCount===10);
  checks.crossPageResume=(await page.evaluate(()=>window.__DPRO_TUTORIAL_QA__.current))===4;
  await page.locator('#replayBtn').click();await page.waitForTimeout(300);checks.replay=(await page.evaluate(()=>window.__DPRO_TUTORIAL_QA__.current))===0;
  await page.locator('#skipBtn').click();checks.skip=await page.evaluate(()=>window.__DPRO_TUTORIAL_QA__.state.skipped===true);
  await page.evaluate(()=>window.__DPRO_TUTORIAL_QA__.replay());await page.waitForTimeout(300);
  const card0=await page.evaluate(()=>window.__DPRO_TUTORIAL_QA__.cardRect);
  const f=page.frames().find(fr=>fr!==page.mainFrame());
  if(f){const control=f.locator('button,input,a,select,textarea').first();if(await control.count()){const cb=await control.boundingBox();if(cb)await control.dispatchEvent('pointerdown',{pointerId:88,pointerType:'mouse',button:0,clientX:cb.x+2,clientY:cb.y+2})}}
  const card1=await page.evaluate(()=>window.__DPRO_TUTORIAL_QA__.cardRect);
  checks.businessControlsNoDrag=card0.left===card1.left&&card0.top===card1.top;
  checks.businessMutation0=businessMutations.length===0;
  checks.sessionRequestsOnly=sessionRequests.every(x=>isSessionOnly(x.url));
  checks.pageErrors0=pageErrors.length===0;
  checks.consoleErrors0=consoleErrors.length===0;
 }catch(e){checks.exception=String(e)}
 const pass=!checks.exception&&checks.exact10&&checks.currentVersion&&checks.noOverflow&&checks.targetFallback&&checks.mouseDrag&&checks.touchPointerDrag&&checks.viewportClamp&&checks.keyboardNext&&checks.back&&checks.focus&&checks.escClose&&checks.resumeReopen&&checks.crossPageResume&&checks.replay&&checks.skip&&checks.businessControlsNoDrag&&checks.businessMutation0&&checks.pageErrors0&&checks.consoleErrors0;
 overall=overall&&pass;
 results.push({width,pass,checks,pageErrors,consoleErrors,businessMutations,sessionRequests});
 await browser.close();
}
const report={version:'DPRO_TUTORIAL_R3_QA_V4',checkedAt:new Date().toISOString(),base:BASE,overall,results};
fs.writeFileSync('r3-live-qa.json',JSON.stringify(report,null,2));
console.log(JSON.stringify(report,null,2));
if(!overall)process.exit(1);
