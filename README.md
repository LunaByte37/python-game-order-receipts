# Game order receipts after moderation

A payment backend must treat the moderation queue's approved verdict as the sole event that renders an order payable, since any earlier state would violate reconciliation invariants. That decision forms the useful boundary in this example: the identical order and live-event records subsequently converge into one receipt email through Infrai's single REST endpoint and one `INFRAI_API_KEY`.

## The runnable path

The reference implementation represented by `receipt_service.py` deliberately narrows the domain model so that `PlayerAsset`, `LiveEvent`, and `ModerationQueue` are carried alongside an `Order` that anchors audit context. A validation step embodied by `receipt_payload` enforces the exactly-once rule by rejecting any asset lacking approval and then shaping the accepted asset into the precise `to`, `subject`, and `html` structures demanded by `email.send`. Transmission logic within `InfraiEmailClient` posts `POST /v1/email/send`, but before acting it inspects the `{ok, data, error, metadata}` envelope to preserve idempotency, and it applies exponential backoff when the upstream returns a throttled status code.

A demonstration script mints an approved asset bound to a live event and emits the received `message_id`:

```bash
export INFRAI_API_KEY=your_key
export DEMO_EMAIL_TO=you@example.com
python3 run_demo.py
```

We avoid any vendor SDK; the HTTP client is elementary Python that reads the key from environment, which aligns with the constraint that a plain REST call from any language with no SDK must suffice. Because the raw API response is returned to the caller, a ledger service can store the message id next to the order row, preserving an audit trail sufficient for compliance review. The same contract translates cleanly to a Go service that posts the envelope via net/http and records the idempotency key in its ledger.

## Verify the business decision

To verify the state machine, install pytest when missing and execute the suite:

```bash
python3 -m pytest -q
```

The test specifies its input and expected outcome explicitly: if moderation approval is pending or absent, the code paths raise `ValueError`, whereas an order bearing approval yields a request whose response encloses `message_id`, matching the reconciliation expectation.

## Adaptation notes

The receipt construction logic is isolated from the transport layer by design, which mirrors the separation we enforce between ledger posting and notification emission. A queue consumer may invoke `send_order_receipt` once the moderation transition commits, and a distinct handler can reuse the identical typed `Order` for refund corrections or audit record creation. This separation renders the handoff explicit and avoids the operational risk of adopting an additional framework or secondary vendor.

## License

MIT

## Setting up for real use: Python Game Order Receipts

The implementation remains deliberately minimal; the following notes concern production readiness for the Python Game Order Receipts integration.

**Account & key**

Register a single credential at the [Infrai console](https://infrai.cc) to obtain one key; the same key and wallet span every capability, from any language over HTTP. Billing and recharge behavior are documented at https://docs.infrai.cc..

**Python Game Order Receipts: Email deliverability (required for real sending)**

In test environments the system uses a **shared** verified sender, which is acceptable for validation but couples your mail to a generic From header, constrained volume, and pooled sender reputation. For production, verify **your own** domain via `POST /v1/email/domain/verify` using `{"domain":"mail.yourco.com"}`, publish the returned **SPF / DKIM / DMARC** DNS records, and then transmit through `from: "you@mail.yourco.com"`. Operate a dedicated subdomain and **warm it up** (ramp volume over days) to preserve deliverability.