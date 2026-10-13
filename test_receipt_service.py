import pytest

from receipt_service import InfraiEmailClient, LiveEvent, ModerationQueue, Order, PlayerAsset, receipt_payload


def make_order(state="approved", approved=("asset-1",)):
    return Order("o-1", "player@example.com", 500, PlayerAsset("asset-1", "Crystal", state), LiveEvent("e-1", "Launch Night"), ModerationQueue("q-1", approved))


def test_receipt_requires_moderation_approval():
    with pytest.raises(ValueError, match="awaiting moderation"):
        receipt_payload(make_order(state="pending"))
    with pytest.raises(ValueError, match="awaiting moderation"):
        receipt_payload(make_order(approved=()))


def test_send_reads_message_id_from_envelope():
    calls = []
    def transport(method, body, headers):
        calls.append((method, body, headers))
        return 200, {"ok": True, "data": {"message_id": "msg-9"}}, {}
    client = InfraiEmailClient(api_key="test-key", transport=transport)
    result = client.send(receipt_payload(make_order()))
    assert result["message_id"] == "msg-9"
    assert calls[0][0] == "POST"
