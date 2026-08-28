from __future__ import annotations
import asyncio, json, os, re, shutil, sys, textwrap, urllib.request
from pathlib import Path
from datetime import datetime, timezone
from PIL import Image
import qrcode
import cv2
import fitz
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from playwright.async_api import async_playwright

BASE='https://dpromstk2000-lab.github.io/dpro-buyback-line/'
GUIDE=BASE+'guide-center.html'
TUTORIAL=BASE+'tutorial.html'
CANONICAL=BASE+'tutorial-first10.json'
DEMO_GUIDE=BASE+'demo-guide.html'
STORAGE='dpro_tutorial_buyback_v1_1'
OUT=Path('r5-manual-output')
SHOT=OUT/'_live_screenshots'
TMP=OUT/'_tmp'
OUT.mkdir(exist_ok=True); SHOT.mkdir(exist_ok=True); TMP.mkdir(exist_ok=True)
WRITE={'POST','PUT','PATCH','DELETE'}
SESSION_PATTERNS=[re.compile(r'/api/admin/login(?:\\?|$)'),re.compile(r'/api/staff/session/(?:issue|revoke)(?:\\?|$)')]

pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
FONT='HeiseiKakuGo-W5'
PAGE_W,PAGE_H=A4


def fetch_json(url:str):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode('utf-8'))


def qr_png(url:str,name:str)->Path:
    p=TMP/name
    img=qrcode.make(url).convert('RGB')
    img.save(p)
    return p


def draw_wrapped(c, text, x, y, max_width, font_size=9.5, leading=None, bold=False, max_lines=None):
    leading=leading or font_size*1.55
    c.setFont(FONT,font_size)
    lines=[]; cur=''
    for ch in str(text):
        if ch=='\n':
            lines.append(cur);cur='';continue
        if pdfmetrics.stringWidth(cur+ch,FONT,font_size) <= max_width:
            cur += ch
        else:
            if cur: lines.append(cur)
            cur=ch
    if cur: lines.append(cur)
    if max_lines and len(lines)>max_lines:
        lines=lines[:max_lines]
        if lines:
            t=lines[-1]
            while pdfmetrics.stringWidth(t+'…',FONT,font_size)>max_width and t:
                t=t[:-1]
            lines[-1]=t+'…'
    for line in lines:
        c.drawString(x,y,line)
        y-=leading
    return y


def draw_title(c, kicker, title, subtitle=None):
    c.setFillColorRGB(0.03,0.25,0.20)
    c.rect(0,PAGE_H-104,PAGE_W,104,fill=1,stroke=0)
    c.setFillColorRGB(1,1,1);c.setFont(FONT,8.5);c.drawString(36,PAGE_H-34,kicker)
    c.setFont(FONT,22);c.drawString(36,PAGE_H-62,title)
    if subtitle:
        c.setFont(FONT,9.3);draw_wrapped(c,subtitle,36,PAGE_H-80,PAGE_W-72,9.3,12)


def fit_image(c, path:Path, x,y,w,h):
    im=Image.open(path); iw,ih=im.size
    scale=min(w/iw,h/ih); nw,nh=iw*scale,ih*scale
    c.drawImage(ImageReader(im),x+(w-nw)/2,y+(h-nh)/2,nw,nh,preserveAspectRatio=True,mask='auto')


def draw_qr(c, qr_path:Path, url:str, x,y,size=78,label=''):
    c.setFillColorRGB(1,1,1);c.roundRect(x-5,y-20,size+10,size+44,7,fill=1,stroke=0)
    c.drawImage(str(qr_path),x,y,size,size,mask='auto')
    c.setFillColorRGB(0.08,0.15,0.13);c.setFont(FONT,7.5)
    if label: c.drawCentredString(x+size/2,y-10,label)
    c.setFont(FONT,5.7);draw_wrapped(c,url,x,y-19,size,5.7,7,max_lines=2)


def draw_footer(c, page_no=None):
    c.setStrokeColorRGB(.82,.86,.84);c.line(36,27,PAGE_W-36,27)
    c.setFillColorRGB(.32,.38,.36);c.setFont(FONT,6.8)
    c.drawString(36,15,'DPRO TUTORIAL / BUYBACK / STANDARD V1.1 / business mutation 0')
    if page_no: c.drawRightString(PAGE_W-36,15,f'{page_no}')


def build_quick(canonical, shots, qrs, out_pdf):
    c=canvas.Canvas(str(out_pdf),pagesize=A4)
    draw_title(c,'DPRO TUTORIAL - QUICK START','総合買取・査定 First10 クイックスタート','10ステップで「受付 → 査定結果 → スタッフ査定 → オーナー管理」の全体像を安全に確認します。')
    y=PAGE_H-126
    c.setFillColorRGB(.05,.18,.15);c.setFont(FONT,12);c.drawString(36,y,'最初にやること');y-=17
    y=draw_wrapped(c,'1. Guide Centerを開く  2. StartでFirst10開始  3. Nextで10ステップを確認。途中終了はResume、最初から確認はReplay。',36,y,PAGE_W-72,9.2,14);y-=8
    fit_image(c,shots['guide'],36,y-235,PAGE_W-72,230);y-=247
    c.setFillColorRGB(.05,.18,.15);c.setFont(FONT,11.5);c.drawString(36,y,'First10（exactly 10）');y-=17
    groups=[('01','Guide','全体像'),('02-03','Customer','受付導線'),('04-05','Member','査定履歴・商品別状況'),('06-07','Staff','自分の仕事・査定ボード'),('08-10','Owner','ダッシュボード・案件・タスク')]
    x=36
    for num,role,label in groups:
        c.setFillColorRGB(.94,.97,.96);c.roundRect(x,y-46,99,43,6,fill=1,stroke=0)
        c.setFillColorRGB(.04,.32,.26);c.setFont(FONT,8);c.drawString(x+8,y-16,num+' '+role)
        c.setFillColorRGB(.12,.18,.16);c.setFont(FONT,7.5);draw_wrapped(c,label,x+8,y-29,83,7.5,10,max_lines=2)
        x+=103
    y-=64
    c.setFillColorRGB(.45,.29,.05);c.setFont(FONT,8.3)
    y=draw_wrapped(c,'安全ルール：First10は場所と流れを確認するチュートリアルです。送信、写真アップロード、査定保存、担当変更、タスク完了などの業務更新は行いません。',36,y,330,8.3,12,max_lines=4)
    draw_qr(c,qrs['guide'],GUIDE,PAGE_W-196,45,70,'Guide Center')
    draw_qr(c,qrs['tutorial'],TUTORIAL,PAGE_W-105,45,70,'Tutorial')
    draw_footer(c,'1 / 1');c.save()


def build_detailed(canonical, shots, qrs, out_pdf):
    steps=canonical['steps']
    c=canvas.Canvas(str(out_pdf),pagesize=A4)
    # Page 1
    draw_title(c,'DPRO TUTORIAL - DETAILED MANUAL','総合買取・査定 First10 詳細マニュアル','DPRO TUTORIAL STANDARD V1.1 / canonical First10 exactly 10')
    fit_image(c,shots['guide'],36,PAGE_H-405,PAGE_W-72,275)
    c.setFillColorRGB(.05,.18,.15);c.setFont(FONT,12);c.drawString(36,PAGE_H-430,'使い方')
    draw_wrapped(c,'Guide Centerの「Start」で開始します。途中まで進めた状態は「Resume」で再開できます。「Replay」はTutorial専用状態だけを初期化し、業務データや認証状態は消しません。',36,PAGE_H-449,330,9,13,max_lines=6)
    draw_qr(c,qrs['guide'],GUIDE,PAGE_W-196,78,70,'Guide Center')
    draw_qr(c,qrs['tutorial'],TUTORIAL,PAGE_W-105,78,70,'Tutorial')
    draw_footer(c,'1 / 6');c.showPage()

    pairs=[(0,1,'step2'),(2,3,'step4'),(4,5,'step6'),(6,7,'step8'),(8,9,'step10')]
    for page_idx,(a,b,shotkey) in enumerate(pairs,start=2):
        draw_title(c,f'FIRST10 / PAGE {page_idx}',f'STEP {steps[a]["step"]} - {steps[b]["step"]}',f'{steps[a]["role"].upper()} → {steps[b]["role"].upper()}')
        fit_image(c,shots[shotkey],36,PAGE_H-405,PAGE_W-72,275)
        y=PAGE_H-430
        for s in [steps[a],steps[b]]:
            c.setFillColorRGB(.04,.32,.26);c.setFont(FONT,11);c.drawString(36,y,f'STEP {s["step"]}  {s["title"]}');y-=16
            c.setFillColorRGB(.12,.18,.16);y=draw_wrapped(c,s['guidance'],36,y,PAGE_W-72,8.7,12,max_lines=4);y-=3
            c.setFillColorRGB(.45,.29,.05);y=draw_wrapped(c,'安全: '+s['safety'],36,y,PAGE_W-72,7.6,10.5,max_lines=4);y-=12
        if page_idx==6:
            c.setFillColorRGB(.05,.18,.15);c.setFont(FONT,9.5);c.drawString(36,88,'完了後')
            draw_wrapped(c,'First10完了はTutorial状態だけを完了扱いにします。業務データは変更しません。必要に応じてGuide CenterからReplayできます。',36,73,PAGE_W-72,8,11,max_lines=4)
        draw_footer(c,f'{page_idx} / 6');c.showPage()
    c.save()


def render_pdf(pdf:Path, prefix:str):
    doc=fitz.open(pdf)
    pages=[]
    for i,page in enumerate(doc):
        pix=page.get_pixmap(matrix=fitz.Matrix(2.4,2.4),alpha=False)
        if prefix=='quick':
            out=OUT/'DPRO_TUTORIAL_BUYBACK_QUICK_START_V1.0.png'
        else:
            out=OUT/f'DPRO_TUTORIAL_BUYBACK_DETAILED_MANUAL_V1.0_PAGE{i+1:02d}.png'
        pix.save(out)
        pages.append(out)
    doc.close()
    if prefix=='detail':
        shutil.copy2(pages[0],OUT/'DPRO_TUTORIAL_BUYBACK_DETAILED_MANUAL_V1.0.png')
    return pages


def _decode_img(img):
    det=cv2.QRCodeDetector()
    values=[]
    try:
        ok, decoded, points, _ = det.detectAndDecodeMulti(img)
        if ok:
            values.extend(x for x in decoded if x)
    except Exception:
        pass
    if not values:
        try:
            v,_,_=det.detectAndDecode(img)
            if v: values.append(v)
        except Exception:
            pass
    return values


def _crop_pdf_region(img, x_pt, y_pt, size_pt=70, pad_pt=10):
    # ReportLab uses bottom-left PDF coordinates; rendered PNG uses top-left pixels.
    h,w=img.shape[:2]
    sx=w/PAGE_W; sy=h/PAGE_H
    x0=max(0,int((x_pt-pad_pt)*sx)); x1=min(w,int((x_pt+size_pt+pad_pt)*sx))
    y0=max(0,int((PAGE_H-(y_pt+size_pt+pad_pt))*sy)); y1=min(h,int((PAGE_H-(y_pt-pad_pt))*sy))
    return img[y0:y1,x0:x1]


def decode_qrs(image_path:Path, qr_regions=None):
    img=cv2.imread(str(image_path))
    if img is None:
        return []
    values=[]
    # Decode from the actual rendered QR regions when their PDF placement is known.
    # This verifies the embedded/rendered QR itself rather than the source PNG.
    for reg in (qr_regions or []):
        crop=_crop_pdf_region(img,**reg)
        values.extend(_decode_img(crop))
    # Also scan the full page and overlapping tiles so unexpected QR codes are detectable.
    values.extend(_decode_img(img))
    h,w=img.shape[:2]
    rows,cols=4,3
    overlap=.10
    for r in range(rows):
        for c in range(cols):
            x0=int(max(0,(c/cols-overlap/cols)*w)); x1=int(min(w,((c+1)/cols+overlap/cols)*w))
            y0=int(max(0,(r/rows-overlap/rows)*h)); y1=int(min(h,((r+1)/rows+overlap/rows)*h))
            values.extend(_decode_img(img[y0:y1,x0:x1]))
    return sorted(set(values))


async def _frame_capture_state(page):
    return await page.evaluate("""() => {
      const f=document.getElementById('appFrame');
      const d=f?.contentDocument, w=f?.contentWindow;
      if(!d || !w) return {ready:false,reason:'iframe unavailable'};
      const visible=el=>{
        if(!el) return false;
        const cs=w.getComputedStyle(el), r=el.getBoundingClientRect();
        return r.width>0 && r.height>0 && cs.display!=='none' && cs.visibility!=='hidden' && Number(cs.opacity||1)>0.05;
      };
      const actualLoaders=[
        ...d.querySelectorAll('#pageLoading, #loadingScreen, .loading .spinner, [aria-busy="true"], [role="progressbar"]')
      ];
      const loaderVisible=actualLoaders.some(visible);
      const retry=[...d.querySelectorAll('button')].find(el=>visible(el) && (el.textContent||'').trim()==='再読み込み');
      const connectionError=[...d.querySelectorAll('.connection-badge.error,.connection.error')].some(visible);
      const visibleImgs=[...d.images].filter(visible);
      const imagesLoading=visibleImgs.some(img=>!img.complete);
      const bodyText=(d.body?.innerText||'');
      const databaseError=/Database request failed/i.test(bodyText);
      return {
        ready:!loaderVisible && !imagesLoading && !connectionError && !databaseError,
        loaderVisible,imagesLoading,connectionError,databaseError,
        retryVisible:!!retry,
        bodySample:bodyText.slice(0,600)
      };
    }""")


async def wait_product_settled(page, step_index:int):
    # Capture only a settled LIVE product page. Customer can occasionally receive a
    # transient read-only database error; an iframe reload is safe because it does not
    # click or submit any product/business control. At most two retries are allowed.
    retries=0
    deadline=asyncio.get_running_loop().time()+65
    while asyncio.get_running_loop().time()<deadline:
        state=await _frame_capture_state(page)
        if state.get('ready'):
            await page.wait_for_timeout(900)
            state2=await _frame_capture_state(page)
            if state2.get('ready'):
                return retries
        if state.get('retryVisible') or state.get('databaseError') or state.get('connectionError'):
            if retries>=2:
                raise RuntimeError(f'LIVE product read error persisted for step {step_index+1}: '+json.dumps(state,ensure_ascii=False))
            retries+=1
            await page.evaluate("""() => { const f=document.getElementById('appFrame'); if(f?.contentWindow) f.contentWindow.location.reload(); }""")
            await page.wait_for_timeout(1400)
            try:
                await page.wait_for_function(f"window.__DPRO_TUTORIAL_QA__?.current==={step_index} && window.__DPRO_TUTORIAL_QA__.targetFound",timeout=25000)
            except Exception as e:
                raise RuntimeError(f'LIVE Tutorial target not recovered after safe reload for step {step_index+1}') from e
            continue
        await page.wait_for_timeout(500)
    state=await _frame_capture_state(page)
    raise RuntimeError(f'LIVE product screen did not settle for step {step_index+1}: '+json.dumps(state,ensure_ascii=False))


async def capture_live():
    canonical=fetch_json(CANONICAL)
    if canonical.get('exactStepCount')!=10 or len(canonical.get('steps',[]))!=10:
        raise RuntimeError('canonical First10 is not exactly 10')
    business=[]; sessions=[]; errors=[]; capture_retries={}
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        page=await browser.new_page(viewport={'width':1440,'height':900},device_scale_factor=1)
        page.on('pageerror',lambda e: errors.append('pageerror:'+str(e)))
        def on_req(req):
            method=req.method.upper()
            if method not in WRITE: return
            rec={'method':method,'url':req.url}
            if any(rx.search(req.url) for rx in SESSION_PATTERNS): sessions.append(rec)
            else: business.append(rec)
        page.on('request',on_req)
        await page.goto(GUIDE,wait_until='networkidle',timeout=45000)
        await page.wait_for_function("window.__DPRO_GUIDE_QA__?.canonical?.steps?.length===10",timeout=20000)
        await page.screenshot(path=str(SHOT/'guide-center-live.png'),full_page=True)
        shots={'guide':SHOT/'guide-center-live.png'}
        await page.goto(TUTORIAL,wait_until='domcontentloaded',timeout=45000)
        await page.wait_for_function("window.__DPRO_TUTORIAL_QA__?.stepCount===10",timeout=20000)
        for step_index,key in [(1,'step2'),(3,'step4'),(5,'step6'),(7,'step8'),(9,'step10')]:
            await page.evaluate(f"window.__DPRO_TUTORIAL_QA__.goTo({step_index})")
            try:
                await page.wait_for_function(f"window.__DPRO_TUTORIAL_QA__?.current==={step_index} && window.__DPRO_TUTORIAL_QA__.targetFound",timeout=25000)
            except Exception:
                raise RuntimeError(f'LIVE Tutorial target not found for step {step_index+1}')
            capture_retries[str(step_index+1)]=await wait_product_settled(page,step_index)
            pth=SHOT/f'tutorial-step-{step_index+1:02d}-live.png'
            await page.screenshot(path=str(pth),full_page=False)
            shots[key]=pth
        await browser.close()
    if business:
        raise RuntimeError('business mutation request detected: '+json.dumps(business,ensure_ascii=False))
    return canonical,shots,business,sessions,errors,capture_retries


async def main():
    canonical,shots,business,sessions,page_errors,capture_retries=await capture_live()
    qrs={'guide':qr_png(GUIDE,'qr-guide.png'),'tutorial':qr_png(TUTORIAL,'qr-tutorial.png')}
    quick=OUT/'DPRO_TUTORIAL_BUYBACK_QUICK_START_V1.0.pdf'
    detail=OUT/'DPRO_TUTORIAL_BUYBACK_DETAILED_MANUAL_V1.0.pdf'
    build_quick(canonical,shots,qrs,quick)
    build_detailed(canonical,shots,qrs,detail)
    qpages=render_pdf(quick,'quick')
    dpages=render_pdf(detail,'detail')
    quick_regions=[
      {'x_pt':PAGE_W-196,'y_pt':45,'size_pt':70,'pad_pt':10},
      {'x_pt':PAGE_W-105,'y_pt':45,'size_pt':70,'pad_pt':10},
    ]
    detail_regions=[
      {'x_pt':PAGE_W-196,'y_pt':78,'size_pt':70,'pad_pt':10},
      {'x_pt':PAGE_W-105,'y_pt':78,'size_pt':70,'pad_pt':10},
    ]
    qr_results={}
    qr_results[qpages[0].name]=decode_qrs(qpages[0],quick_regions)
    qr_results[dpages[0].name]=decode_qrs(dpages[0],detail_regions)
    for p in dpages[1:]:
        qr_results[p.name]=decode_qrs(p)
    expected={
      qpages[0].name:sorted([GUIDE,TUTORIAL]),
      dpages[0].name:sorted([GUIDE,TUTORIAL]),
    }
    qr_pass=True
    for name,urls in expected.items():
        if qr_results.get(name)!=urls: qr_pass=False
    # Pages without QR must decode none.
    for p in dpages[1:]:
        if qr_results.get(p.name): qr_pass=False
    evidence={
      'version':'DPRO_TUTORIAL_BUYBACK_R5_QA_V1_4',
      'checkedAt':datetime.now(timezone.utc).isoformat(),
      'canonicalUrl':CANONICAL,
      'canonicalExact10':canonical.get('exactStepCount')==10 and len(canonical.get('steps',[]))==10,
      'liveScreenshotSources':{
        'guide':GUIDE,
        'tutorial':TUTORIAL,
      },
      'liveScreenshots':[p.name for p in shots.values()],
      'quickStart':{'pdf':quick.name,'png':qpages[0].name,'pages':len(qpages)},
      'detailedManual':{'pdf':detail.name,'preview':'DPRO_TUTORIAL_BUYBACK_DETAILED_MANUAL_V1.0.png','pages':[p.name for p in dpages]},
      'qrExpected':expected,
      'qrDecoded':qr_results,
      'qrDecodeMethod':'Rendered PDF page: exact QR-region decode plus full-page/tiled scan',
      'qrPass':qr_pass,
      'businessMutations':business,
      'businessMutation0':len(business)==0,
      'sessionRequests':sessions,
      'pageErrorsDuringCapture':page_errors,
      'captureReloadRetries':capture_retries,
      'protectedBoundaries':'No Worker/DB/Supabase/Auth/Role/Permission/Feature Flag writes performed by this build.',
      'manualVisualInspection':'PENDING_ASSISTANT_POST_ARTIFACT_REVIEW',
      'screenshotSettledGate':'PASS: loader/error UI absent before capture; transient read-only Customer errors may be iframe-reloaded at most twice'
    }
    (OUT/'R5_QA_EVIDENCE.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if not evidence['canonicalExact10'] or not qr_pass or business:
        print(json.dumps(evidence,ensure_ascii=False,indent=2));sys.exit(1)
    print(json.dumps(evidence,ensure_ascii=False,indent=2))

if __name__=='__main__':
    asyncio.run(main())
