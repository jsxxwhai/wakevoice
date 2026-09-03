"""Screen capture and OCR for understanding what's on the desktop."""
from __future__ import annotations

import logging
from pathlib import Path


log = logging.getLogger(__name__)


class ScreenReader:
    """Capture the screen and (optionally) run OCR over it."""

    def __init__(self, ocr_enabled: bool = True, ocr_lang: str = "chi_sim+eng",
                 backend: str = "mss"):
        self.ocr_enabled = ocr_enabled
        self.ocr_lang = ocr_lang
        self.backend = backend

    def capture(self, path: str | Path | None = None) -> Path:
        """Capture full screen to PNG; returns the file path.

        `self.backend` selects the capture engine; only "mss" is currently
        implemented (a lightweight, dependency-free choice).
        """
        if self.backend not in ("mss", ""):
            raise ValueError(f"unsupported screen backend: {self.backend!r}")
        import mss  # lazy import
        import mss.tools
        out = Path(path) if path else Path("screen.png")
        out = out.resolve()
        with mss.mss() as sct:
            shot = sct.grab(sct.monitors[1])  # primary monitor
            mss.tools.to_png(shot.rgb, shot.size, output=str(out))
        return out

    def ocr(self, image_path: str | Path) -> str:
        """Extract text from an image via Tesseract OCR."""
        if not self.ocr_enabled:
            return ""
        try:
            import pytesseract
            from PIL import Image
            return pytesseract.image_to_string(
                Image.open(image_path), lang=self.ocr_lang)
        except Exception as e:
            log.warning("OCR unavailable: %s", e)
            return ""

    def read_screen(self, save_path: str | Path | None = None) -> dict:
        """Convenience: capture + OCR in one call. Returns dict with text.

        If `save_path` is omitted, a temporary PNG is used and removed after
        OCR so no stray screenshot file is left behind.
        """
        import os
        import tempfile
        keep = save_path is not None
        if keep:
            png = self.capture(save_path)
        else:
            fd, tmp = tempfile.mkstemp(suffix=".png")
            os.close(fd)  # close the open handle immediately
            png = self.capture(tmp)
        try:
            text = self.ocr(png)
            return {"image": str(png), "text": text}
        finally:
            if not keep:
                try:
                    png.unlink(missing_ok=True)
                except Exception:
                    pass
