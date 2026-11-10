import io

from PIL import Image, ImageOps, UnidentifiedImageError

from core.loaders.base import DocumentLoader
from core.models import PageUnit, UnsupportedInputError

MAX_SIDE = 4000


class ImageLoader(DocumentLoader):
    mime_types = {"image/png", "image/jpeg"}

    def load(self, data: bytes) -> list[PageUnit]:
        try:
            img = Image.open(io.BytesIO(data))
            img.load()  # open() is lazy; load() catches truncated files
        except (UnidentifiedImageError, OSError) as e:
            raise UnsupportedInputError(f"Could not read this image ({e}). Is the file corrupt?") from e
        if img.format not in ("PNG", "JPEG"):
            raise UnsupportedInputError(f"Unsupported image format {img.format}; use PNG or JPEG.")

        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
        if max(img.size) > MAX_SIDE:
            img.thumbnail((MAX_SIDE, MAX_SIDE))
        out = io.BytesIO()
        img.save(out, format="PNG")
        return [PageUnit(page_no=1, image_png=out.getvalue(), text_layer=None,
                         width=img.width, height=img.height)]
