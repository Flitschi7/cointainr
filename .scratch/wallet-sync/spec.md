# Wallet sync

Status: needs-triage

Parked: not the current focus. Decisions below were settled on 2026-11-01 and
should be re-checked when this is picked up. Earlier local wallet code is lost;
this starts fresh.

Vocabulary follows [GLOSSARY.md](../../GLOSSARY.md) (**Wallet**, **Last sync**).

## Decisions

- A **wallet** is a location backed by an on-chain address (or a Bitcoin xpub),
  whose holding quantities are read from the blockchain.
- First scope: Bitcoin (single address or xpub) and Ethereum native ETH. Tokens
  (ERC-20) and other chains are later decisions.
- The first successful sync creates one holding per asset found at that wallet;
  later syncs update its quantity.
- Sync owns the quantity, which is read-only in the app. The user owns the
  purchase price; when it is empty, gain/loss and return are unavailable.
- Balance data comes from public explorers by default, with a configurable
  endpoint for the user's own node or indexer. The settings show a privacy note
  that public services learn which addresses are queried.
- When a sync fails, the quantities from the last sync stay in use with their age
  shown.

## Open questions

- Which public services for Bitcoin and Ethereum, and their rate limits.
- How often to sync, and whether syncing is manual, scheduled, or both.
- What happens to a wallet holding whose balance drops to zero, or when a wallet
  is deleted.
- Address and xpub validation, and xpub gap limit.
