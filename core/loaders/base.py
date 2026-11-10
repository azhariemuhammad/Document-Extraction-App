from abc import ABC, abstractmethod

from core.models import PageUnit


class DocumentLoader(ABC):
    mime_types: set[str]

    @abstractmethod
    def load(self, data: bytes) -> list[PageUnit]: ...
