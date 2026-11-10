import os

import pymupdf  # AGPL: fine for this take-home, needs a licence review commercially

from core.loaders.base import DocumentLoader
from core.models import PageUnit, UnsupportedInputError

MAX_PAGES = 50


class PdfLoader(DocumentLoader):
    mime_types = {"application/pdf"}

    def load(self, data: bytes) -> list[PageUnit]:
        dpi = int(os.getenv("RENDER_DPI", "150"))
        try:
            doc = pymupdf.open(stream=data, filetype="pdf")
        except Exception as e:
            raise UnsupportedInputError(f"Could not open this PDF ({e}). Is the file corrupt?") from e
        if doc.needs_pass:
            raise UnsupportedInputError("This PDF is password-protected. Remove the password and upload again.")
        if doc.page_count == 0:
            raise UnsupportedInputError("This PDF has no pages.")
        if doc.page_count > MAX_PAGES:
            raise UnsupportedInputError(f"This PDF has {doc.page_count} pages; the limit is {MAX_PAGES}.")

        pages = []
        for i, page in enumerate(doc, start=1):
            pix = page.get_pixmap(dpi=dpi)
            # empty text layer (scan) -> None, so the grounding check is skipped for this page
            text = page.get_text().strip() or None
            pages.append(PageUnit(page_no=i, image_png=pix.tobytes("png"),
                                  text_layer=text, width=pix.width, height=pix.height))
        return pages
