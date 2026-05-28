"""mt_gateway — unified translation API over multiple MT engines."""

from __future__ import annotations

from polydrive.core.models import MTResult
from polydrive.mt_gateway.gateway import MTGateway

__all__ = ["MTGateway", "MTResult"]
