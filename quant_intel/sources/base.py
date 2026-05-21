from __future__ import annotations

from abc import ABC, abstractmethod

from quant_intel.models import Item


class Source(ABC):
    name: str

    @abstractmethod
    def fetch(self) -> list[Item]:
        raise NotImplementedError
