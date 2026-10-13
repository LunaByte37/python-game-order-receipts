import os

from receipt_service import InfraiEmailClient, LiveEvent, ModerationQueue, Order, PlayerAsset, send_order_receipt


def main() -> None:
    recipient = os.environ.get("DEMO_EMAIL_TO")
    if not recipient:
        raise SystemExit("Set DEMO_EMAIL_TO to receive the example receipt")
    order = Order(
        order_id="order-1042",
        player_email=recipient,
        total_cents=1299,
        asset=PlayerAsset("asset-sword-7", "Sunset Blade", "approved"),
        event=LiveEvent("event-arena-3", "Autumn Arena"),
        moderation=ModerationQueue("queue-eu-1", ("asset-sword-7",)),
    )
    result = send_order_receipt(order, InfraiEmailClient())
    print(f"Receipt sent with message_id={result.get('message_id')}")


if __name__ == "__main__":
    main()
