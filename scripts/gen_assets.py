# -*- coding: utf-8 -*-
"""Regenerate the README demo screenshot and social preview card.

Run from the repository root:

    python scripts/gen_assets.py

Draws the UI mockup and the social card as pure vector text and shapes
(no third-party imagery or fonts), so the repository media is fully
original and license-clean. Requires Pillow.
"""
from __future__ import annotations

import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent

def _render_demo():
    from PIL import Image, ImageDraw, ImageFont

    W,H = 1040, 640
    bg = (17, 24, 39)        # slate-900
    panel = (31, 41, 55)     # slate-800
    line = (55, 65, 81)      # slate-700
    accent = (34, 211, 238)  # cyan-400
    green = (52, 211, 153)
    white = (243,244,246)
    grey = (156,163,175)
    yellow = (251,191,36)

    def font(sz, bold=False):
        p = 'C:/Windows/Fonts/msyhbd.ttc' if bold else 'C:/Windows/Fonts/msyh.ttc'
        try: return ImageFont.truetype(p, sz)
        except Exception: return ImageFont.load_default()

    img = Image.new('RGB', (W,H), bg)
    d = ImageDraw.Draw(img)

    # Outer rounded frame (approx with rectangle)
    d.rounded_rectangle([10,10,W-10,H-10], radius=22, fill=panel, outline=line, width=2)

    # Title bar
    d.text((46, 30), 'WakeVoice', font=font(28, True), fill=white)
    d.text((46, 72), '唤醒词模式 · 本地运行 · 免云账号', font=font(18), fill=grey)
    # dots
    for i,(dx,col) in enumerate([(W-140, (248,113,113)),(W-108,(251,191,36)),(W-76,(52,211,153))]):
        d.ellipse([dx,36,dx+18,54], fill=col)

    # left hint panel
    d.rounded_rectangle([46,130,360,H-46], radius=16, fill=(15,23,42), outline=line, width=1)
    d.text((76,160), '状态', font=font(20,True), fill=yellow)
    items = [
        ('●  正在听唤醒词', green),
        ('“你好伙伴”', white),
        ('', None),
        ('●  基础对话：本地', green),
        ('●  技能：已加载 10+', green),
        ('●  数据：不出电脑', green),
    ]
    y=200
    for t,c in items:
        if not t: y+=14; continue
        d.text((76,y), t, font=font(19), fill=c)
        y+=38
    d.text((76, y+6), '按 Esc 停止当前任务', font=font(17), fill=grey)

    # chat bubbles right
    d.text((404,150), '对话演示', font=font(22,True), fill=white)
    bubbles = [
        ('你', '你好伙伴', (59,130,246), (30,58,138), 420),
        ('它', '我在。有什么吩咐？', accent, (8,47,73), 520),
        ('你', '打开记事本', (59,130,246), (30,58,138), 620),
        ('它', '好的，已经帮你打开记事本了。', accent, (8,47,73), 720),
    ]
    def wrap(text, fnt, maxw):
        if d.textlength(text, font=fnt) <= maxw: return [text]
        out=[]; cur=''
        for ch in text:
            if d.textlength(cur+ch, font=fnt) > maxw:
                out.append(cur); cur=ch
            else: cur+=ch
        if cur: out.append(cur)
        return out

    def bubble(name, text, border, fill, y):
        f = font(19)
        d.text((404,y), name, font=font(18,True), fill=border)
        tw = d.textlength(text, font=f)
        bw = min(int(tw)+60, 560)
        wrapped = wrap(text, f, 560-84)
        bh = 44 + (len(wrapped)-1)*34
        d.rounded_rectangle([404, y+26, 404+bw, y+26+bh], radius=14, fill=fill, outline=border, width=1)
        yy=y+44
        for wline in wrapped:
            d.text((424, yy), wline, font=f, fill=white)
            yy+=34

    bubble('你','你好伙伴',(59,130,246),(30,58,138),160)
    bubble('它','我在。有什么吩咐？',accent,(8,47,73),268)
    bubble('你','打开记事本',(59,130,246),(30,58,138),370)
    bubble('它','好的，已经帮你打开记事本了。',accent,(8,47,73),478)
    # time hint
    d.text((404, 588), '停顿 1.5 秒自动执行 · 无需按键', font=font(16), fill=grey)

    out = ROOT / "assets" / "demo.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print("wrote", out)


def _render_og():
    from PIL import Image, ImageDraw, ImageFont

    W,H = 1280,640
    def font(sz, bold=False):
        p='C:/Windows/Fonts/msyhbd.ttc' if bold else 'C:/Windows/Fonts/msyh.ttc'
        try: return ImageFont.truetype(p,sz)
        except Exception: return ImageFont.load_default()

    # gradient bg deep slate -> darker
    img=Image.new('RGB',(W,H),(10,18,30))
    px=img.load()
    for y in range(H):
        t=y/H
        r=int(16+ (8-16)*t)
        g=int(28+ (20-28)*t)
        b=int(48+ (38-48)*t)
        for x in range(W):
            px[x,y]=(r,g,b)
    d=ImageDraw.Draw(img)

    # soft accent glows
    for cx,cy,rad,col in [(180,140,260,(30,58,138)),(1120,500,300,(8,47,73))]:
        for yy in range(max(0,cy-rad), min(H,cy+rad)):
            for xx in range(max(0,cx-rad), min(W,cx+rad)):
                dist=((xx-cx)**2+(yy-cy)**2)**0.5
                if dist<rad:
                    a=(1-dist/rad)
                    cur=px[xx,yy]
                    px[xx,yy]=tuple(int(cur[i]*(1-a*0.55)+col[i]*a*0.55) for i in range(3))

    # left: microphone emoji visual: simple mic drawn
    def rounded_rect(x,y,w,h,r,fill):
        d.rounded_rectangle([x,y,x+w,y+h],radius=r,fill=fill)
    # mic capsule
    mx,my=170,320
    d.rounded_rectangle([mx-40,my-90,mx+40,my+70],radius=46, fill=(34,211,238))
    d.rounded_rectangle([mx-30,my-200,mx+30,my-40],radius=30, fill=(34,211,238))
    d.rounded_rectangle([mx-80,my-170,mx+80,my-120],radius=26, fill=(255,255,255))
    # stand
    d.rounded_rectangle([mx-14,my+60,mx+14,my+140],radius=8, fill=(148,163,184))
    d.rounded_rectangle([mx-70,my+130,mx+70,my+160],radius=16, fill=(148,163,184))
    # wave arcs (right)
    for i,rad in enumerate([70,110,150]):
        x0=mx+45
        d.arc([x0,my-40-rad,x0+2*rad,my-40+rad], start=-70,end=70, fill=(34,211,238), width=10)

    # right: title
    d.text((430,150), 'WakeVoice', font=font(72,True), fill=(248,250,252))
    d.text((430,270), '喊一声唤醒词，电脑就帮你干活。', font=font(46,True), fill=(226,232,240))
    d.text((430,360), 'Wake word → spoken command → done.', font=font(34), fill=(148,163,184))
    d.text((430,430), '完全本地 · 离线可用 · 免云账号 · MIT 开源', font=font(32), fill=(34,211,238))
    d.rounded_rectangle([430,500,880,566], radius=30, fill=(34,211,238))
    d.text((452,518), '给仓库点 Star ⭐', font=font(28,True), fill=(3,7,18))

    out = ROOT / "assets" / "og-card.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print("wrote", out)


if __name__ == "__main__":
    _render_demo()
    _render_og()
    print("assets regenerated ->", ROOT / "assets")
