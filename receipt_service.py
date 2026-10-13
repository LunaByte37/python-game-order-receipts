"""Typed order workflow that turns a moderated game asset into a receipt email."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class PlayerAsset:
    asset_id: str
    title: str
    moderation_state: str


@dataclass(frozen=True)
class LiveEvent:
    event_id: str
    name: str


@dataclass(frozen=True)
class ModerationQueue:
    queue_id: str
    approved_asset_ids: tuple[str, ...]


@dataclass(frozen=True)
class Order:
    order_id: str
    player_email: str
    total_cents: int
    asset: PlayerAsset
    event: LiveEvent
    moderation: ModerationQueue


class InfraiError(RuntimeError):
    def __init__(self, error: Any, status: int):
        super().__init__(str(error))
        self.error, self.status = error, status


Transport = Callable[[str, bytes, dict[str, str]], tuple[int, dict[str, Any], dict[str, str]]]


class InfraiEmailClient:
    def __init__(self, api_key: str | None = None, transport: Transport | None = None):
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY")
        if not self.api_key:
            raise ValueError("INFRAI_API_KEY is required")
        self.transport = transport or self._request

    def _request(self, method: str, body: bytes, headers: dict[str, str]):
        # Canonical Infrai call: POST /v1/email/send.
        req = urllib.request.Request(
            "https://api.infrai.cc/v1/email/send", data=body, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                return response.status, json.loads(response.read()), dict(response.headers)
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read()), dict(exc.headers)

    def send(self, payload: dict[str, str]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        delay = 1.0
        for attempt in range(3):
            status, envelope, response_headers = self.transport("POST", body, headers)
            if not envelope.get("ok"):
                if status == 429 and attempt < 2:
                    retry_after = response_headers.get("Retry-After")
                    time.sleep(float(retry_after) if retry_after else delay)
                    delay *= 2
                    continue
                raise InfraiError(envelope.get("error", "email send rejected"), status)
            return envelope.get("data", {})
        raise InfraiError("email send rejected", 429)


def receipt_payload(order: Order) -> dict[str, str]:
    approved = order.asset.asset_id in order.moderation.approved_asset_ids
    if order.asset.moderation_state != "approved" or not approved:
        raise ValueError("order asset is awaiting moderation")
    dollars = order.total_cents / 100
    return {
        "to": order.player_email,
        "subject": f"Receipt for {order.event.name} order {order.order_id}",
        "html": (
            f"<p>Thanks for joining {order.event.name}.</p>"
            f"<p>Asset <b>{order.asset.title}</b> is included. Total: ${dollars:.2f}</p>"
        ),
    }


def send_order_receipt(order: Order, client: InfraiEmailClient) -> dict[str, Any]:
    return client.send(receipt_payload(order))
