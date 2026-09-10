"""Shared schema primitives."""

from decimal import Decimal
from typing import Annotated

from pydantic import PlainSerializer

# Pydantic v2 serialises Decimal to a JSON *string* by default, which silently
# breaks arithmetic on the client (e.g. "79.98" + "79.98" -> "79.9879.98").
# Money emits a JSON number instead while keeping Decimal precision server-side.
Money = Annotated[Decimal, PlainSerializer(lambda v: float(v), return_type=float)]
