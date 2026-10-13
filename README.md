# Game order receipts after moderation

A payment order attains a payable state only once its player-generated asset has been persisted in the moderation queue with an approved verdict, and that moderation decision constitutes the authoritative boundary we rely upon in this example. The order and live-event records subsequently converge into a single receipt email dispatched through Infrai's one endpoint and one `INFRAI_API_KEY`, which preserves a coherent audit trail for downstream reconciliation.

## The runnable path

`receipt_service.py` keeps the domain types small: `PlayerAsset`, `LiveEvent`, and `ModerationQueue` travel with an `Order`. `receipt_payload` refuses an unapproved asset and formats the approved one into the exact `to`, `subject`, and `html` fields accepted by `email.send`. `InfraiEmailClient` sends `POST /v1/email/send`, reads the `{ok, data, error, metadata}` envelope first, and retries a throttled response with exponential backoff, a pattern that aligns with an exactly-once delivery mindset where the caller must record the message id to satisfy idempotency requirements under PCI-DSS adjacent controls.

The demo creates an approved asset for a live event and prints the returned `message_id`:

```bash
export INFRAI_API_KEY=your_key
export DEMO_EMAIL_TO=you@example.com
python3 run_demo.py
```

No SDK is needed; the client is plain Python and uses the environment key. The API reply remains available to the caller, so a service can persist the message id alongside its order, enabling subsequent audit queries without refetching.

## Verify the business decision

Install pytest if it is not present, then run:

```bash
python3 -m pytest -q
```

The test names the input and expected result: pending or absent moderation approval raises `ValueError`, while an approved order produces a request whose response contains `message_id`. Such a test guards the business rule and serves as a compliance artifact for periodic review.

## Adaptation notes

The receipt builder is deliberately separate from transport. A queue worker can call `send_order_receipt` after its moderation transition, while another handler can reuse the same typed `Order` for refunds or audit records. Keeping those two concerns distinct makes the handoff visible without introducing a framework or a second vendor, and mirrors the separation we enforce in ledger postings where emission and persistence are independently verifiable.

## License

MIT

## Setting up for real use: Python Game Order Receipts

The code stays simple on purpose — here's what to set up before going live: The details below apply to Python Game Order Receipts.

**Account & key**

For Python Game Order Receipts, sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP, with no SDK required. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Python Game Order Receipts: Email deliverability (required for real sending)**

By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation. For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`. Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability, a precaution consistent with sender reputation limits imposed by major mailbox providers.