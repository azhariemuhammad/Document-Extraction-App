from core.loaders.base import DocumentLoader
from core.loaders.image import ImageLoader
from core.loaders.pdf import PdfLoader
from core.models import PageUnit, UnsupportedInputError

_image = ImageLoader()
LOADERS: dict[str, DocumentLoader] = {
    "application/pdf": PdfLoader(),
    "image/png": _image,
    "image/jpeg": _image,
}


def load_document(data: bytes, mime: str) -> list[PageUnit]:
    loader = LOADERS.get(mime)
    if loader is None:
        raise UnsupportedInputError(f"Unsupported file type '{mime}'. Upload a PDF, PNG or JPEG.")
    return loader.load(data)
