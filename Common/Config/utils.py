from __future__ import annotations
from typing import Any
from dataclasses import dataclass as _dataclass


# decorator to add an __init__ method to a dataclass that parse a dict and validate the fields
def dataclass(cls: type) -> type:
    _dataclass(cls)

    old__init__ = cls.__init__ if hasattr(cls, "__init__") else None

    def new__init__(self, data: dict[str, Any]) -> None:
        for field in cls.__dataclass_fields__.values():
            if field.name not in data:
                raise ValueError(f"Missing field {field.name} in {cls.__name__} config")
            value = data[field.name]
            setattr(self, field.name, value)

        if old__init__ is not None:
            old__init__(self)

    setattr(cls, "__init__", new__init__)
    return cls
