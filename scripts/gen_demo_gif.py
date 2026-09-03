"""Generate assets/demo.gif - an animated WakeVoice conversation demo.

Pure Pillow vector drawing (no third-party imagery or fonts), so the media
is fully original and license-clean. Run from the repository root:

    python scripts/gen_demo_gif.py

Requires Pillow. Emits a looping GIF that shows: wake word -> assistant
answers -> user speaks a command -> pause detection -> skill executes.
"""
from __future__ import annotations

import pathlib

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent

BG = (15, 23, 42)
PANEL = (30, 41, 59)
LINE = (51, 65, 85)
ACCENT = (34, 211, 238)
BLUE = (59, 130, 246)
BLUE_D = (30, 58, 138)
GREEN = (52, 211, 153)
WHITE = (248, 250, 252)
GREY = (148, 163, 184)
YELLOW = (251, 191, 36)
W, H = 1040, 640


def _font(sz: int, bold: bool = False):
    path = "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc"
    try:
        return ImageFont.truetype(path, sz)
    except Exception:
        return ImageFont.load_default()


def _wrap(d: ImageDraw.ImageDraw, text: str, fnt, maxw: int) -> list[str]:
    lines, cur = [], ""
    for ch in text:
        if d.textlength(cur + ch, font=fnt) > maxw:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def _make_frame(phase: int) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    d.rounded_rectangle([10, 10, W - 10, H - 10], radius=22, fill=PANEL, outline=LINE, width=2)
    d.text((46, 28), "WakeVoice", font=_font(30, True), fill=WHITE)
    d.text((46, 72), "唤醒词模式 · 本地运行 · 免云账号", font=_font(18), fill=GREY)
    for dx, col in [(W - 140, (248, 113, 113)), (W - 108, (251, 191, 36)), (W - 76, (52, 211, 153))]:
        d.ellipse([dx, 34, dx + 18, 52], fill=col)

    d.rounded_rectangle([46, 128, 356, H - 44], radius=16, fill=(10, 17, 34), outline=LINE, width=1)
    d.text((76, 156), "状态", font=_font(20, True), fill=YELLOW)
    status_items = [
        ("正在听唤醒词", GREEN, 0),
        ("“你好伙伴” 已唤醒", ACCENT, 1),
        ("正在听指令…", GREEN, 2),
        ("已捕获：打开记事本", GREEN, 3),
        ("正在执行技能…", YELLOW, 4),
        ("已完成：记事本已打开", GREEN, 5),
    ]
    y = 200
    for txt, col, need in status_items:
        visible = phase >= need
        mark = "●" if visible else "○"
        d.text((76, y), mark + "  " + txt, font=_font(18), fill=col if visible else (71, 85, 105))
        y += 40
    d.text((76, y + 8), "按 Esc 可随时停止", font=_font(16), fill=GREY)

    d.text((404, 148), "对话演示", font=_font(22, True), fill=WHITE)

    def _bubble(name: str, text: str, border, fill, y):
        f = _font(19)
        d.text((404, y), name, font=_font(18, True), fill=border)
        wrapped = _wrap(d, text, f, 560 - 84)
        bw = min(int(d.textlength(text, font=f)) + 60, 560)
        bh = 44 + (len(wrapped) - 1) * 34
        d.rounded_rectangle([404, y + 26, 404 + bw, y + 26 + bh], radius=14, fill=fill,
                            outline=border, width=1)
        yy = y + 44
        for wline in wrapped:
            d.text((424, yy), wline, font=f, fill=WHITE)
            yy += 34
        return bh

    if phase >= 0:
        _bubble("你", "你好伙伴", BLUE, BLUE_D, 196)
    if phase >= 1:
        _bubble("它", "我在。有什么吩咐？", ACCENT, (8, 47, 73), 268)
    if phase >= 2:
        _bubble("你", "打开记事本", BLUE, BLUE_D, 350)
    if phase >= 3:
        d.text((404, 462), "（说完停顿 1.5 秒 → 自动执行…）", font=_font(17), fill=GREY)
    if phase >= 4:
        _bubble("它", "好的，已经帮你打开记事本了。", ACCENT, (8, 47, 73), 470)
    d.text((404, 596), "全程不用碰键盘 · 完全本地 · 隐私不出门", font=_font(16), fill=GREY)
    return img


def main() -> None:
    frames = [_make_frame(i) for i in range(6)]
    durations = [700, 850, 700, 900, 1100, 900]
    out = ROOT / "assets" / "demo.gif"
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=durations,
                   loop=0, optimize=False)
    print("wrote", out, "size", out.stat().st_size)


if __name__ == "__main__":
    main()
