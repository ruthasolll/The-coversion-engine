from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class EmailWebhookTracer:
    def __init__(self) -> None:
        self._client: Any | None = None
        self._trace: Any | None = None
        self._enabled = bool(os.getenv("LANGFUSE_PUBLIC_KEY"))
        if not self._enabled:
            return
        try:
            from langfuse import Langfuse

            kwargs: dict[str, Any] = {}
            secret_key = os.getenv("LANGFUSE_SECRET_KEY")
            host = os.getenv("LANGFUSE_HOST")
            if secret_key:
                kwargs["secret_key"] = secret_key
            if host:
                kwargs["host"] = host
            self._client = Langfuse(public_key=os.getenv("LANGFUSE_PUBLIC_KEY"), **kwargs)
        except Exception:
            logger.exception("langfuse_init_failed")
            self._enabled = False

    @property
    def enabled(self) -> bool:
        return self._enabled and self._client is not None

    def start_trace(self, *, provider: str, raw_event_type: str) -> None:
        if not self.enabled:
            return
        try:
            if hasattr(self._client, "trace"):
                self._trace = self._client.trace(
                    name="email_webhook_event",
                    metadata={
                        "provider": provider,
                        "raw_event_type": raw_event_type,
                    },
                )
            else:
                # Some Langfuse SDK versions expose only OpenTelemetry-style
                # observation helpers; in that case we skip without error.
                logger.info("langfuse_trace_api_unavailable")
                self._trace = None
        except Exception:
            logger.exception("langfuse_trace_start_failed")
            self._trace = None

    def start_span(self, *, name: str, metadata: dict | None = None) -> Any | None:
        if not self._trace:
            return None
        try:
            return self._trace.span(name=name, metadata=metadata or {})
        except Exception:
            logger.exception("langfuse_span_start_failed")
            return None

    def end_span(self, span: Any | None, *, metadata: dict | None = None, level: str = "DEFAULT") -> None:
        if not span:
            return
        try:
            if metadata and hasattr(span, "update"):
                span.update(metadata=metadata, level=level)
            if hasattr(span, "end"):
                span.end()
        except Exception:
            logger.exception("langfuse_span_end_failed")

    def finalize(self, *, success: bool, metadata: dict) -> None:
        if not self._trace:
            return
        try:
            if hasattr(self._trace, "update"):
                self._trace.update(metadata=metadata)
            if hasattr(self._client, "flush"):
                self._client.flush()
        except Exception:
            logger.exception("langfuse_trace_finalize_failed")
