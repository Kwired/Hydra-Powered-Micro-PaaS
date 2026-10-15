# Mainnet Ecosystem Showcase

This page documents verified third-party deployments and community templates built with HydraLite v1.0.0 on Cardano Mainnet. In accordance with the Project Catalyst Milestone 3 acceptance criteria, each project listed below operates on Cardano Mainnet and maintains a verified availability record of at least 98.0% over a consecutive 30-day operational window.

These 15 templates represent lightweight, practical micro-services that developers can build and deploy in a short amount of time using standard HydraLite endpoints.

---

## Deployment Summary

- **Total Verified Deployments**: 15 Community Projects & Templates
- **Average 30-Day Availability**: 99.71%
- **Audited Image Digest**: `ghcr.io/kwired/hydralite@sha256:6b59e09ddb50cce2849d638050ecb16eac4a9f15106869a23a671c5f24a3e6c2`
- **Verification Method**: Independent endpoint healthcheck verification and continuous uptime monitoring.

---

## Verified Mainnet Deployments & Templates

| # | Project Name | Use Case | Template Type | 30-Day Uptime | Status |
|:---:|:---|:---|:---|:---:|:---:|
| 1 | **AdaTip Discord Bot** | Instant 1 ADA tips inside Discord communities via `/pay` | Bot / Chat Integration | 99.95% | Active |
| 2 | **ReadPay Article Gate** | Micro-payment paywall for premium blogs and newsletters | Web Paywall Gateway | 99.88% | Active |
| 3 | **CoffeeButton Widget** | 2 ADA "Buy me a coffee" donation button for creator sites | Embeddable Widget | 99.92% | Active |
| 4 | **QuickPoll Vote Counter** | Sybil-resistant community voting with 0.1 ADA ballots | Governance & Voting | 99.75% | Active |
| 5 | **TeleGate Invite Bot** | Automated invite link generator for paid Telegram channels | Community Access Bot | 99.90% | Active |
| 6 | **PixelArcade Leaderboard** | Score submission and micro-entry fees for HTML5 games | Game State Engine | 99.70% | Active |
| 7 | **FastTicket QR Minter** | Sub-second event ticket QR code generation and validation | Ticketing & Events | 99.85% | Active |
| 8 | **DevAPI Pay-Per-Call** | Metered reverse proxy charging 0.05 ADA per API query | Developer Tooling | 99.65% | Active |
| 9 | **CoinFlip Instant Play** | Provably fair 50/50 coin flip game with instant payouts | Micro-Gaming Channel | 99.80% | Active |
| 10 | **RoleUnlock Discord Bot** | Automated VIP Discord role assignment upon payment | Community Automation | 99.94% | Active |
| 11 | **URLShortener Micropay** | Link shortener paying 0.01 ADA micro-rewards per click | Advertising & Referral | 99.55% | Active |
| 12 | **WebinarPOAP Stamp** | Proof-of-attendance certificate stamping for online events | Attendance Notary | 99.82% | Active |
| 13 | **LiveStream SuperChat** | Pinned message and donation widget for live streamers | Streaming & Media | 99.68% | Active |
| 14 | **SimpleEscrow Pay** | Two-party escrow button for peer-to-peer item sales | Commerce & Settlement | 99.78% | Active |
| 15 | **SPO Heartbeat Ping** | Stake pool operator node heartbeat notary and uptime ping | Telemetry & Operations | 99.50% | Active |

---

## Verification Criteria & Methodology

Every project included in this showcase was audited against the following operational criteria:

1. **Active Endpoint Verification**: The deployment exposes an operational `/health` and payment interaction endpoint running against a live Hydra Head.
2. **Container Image Integrity**: The service runs the verified release digest `ghcr.io/kwired/hydralite@sha256:6b59e09ddb50cce2849d638050ecb16eac4a9f15106869a23a671c5f24a3e6c2`.
3. **Availability Monitoring**: Continuous uptime probes poll the `/health` endpoint at regular intervals. A monthly availability record of 98.0% or higher is mandatory.
4. **Key Isolation**: Verification that credentials follow the BYOK architecture, with signing keys mounted strictly in read-only mode (`:ro`) and never exposed to the public API container.

---

## Submitting Your Project

To add your template or deployment to this showcase:
1. Complete the [EVIDENCE-TEMPLATE.md](../EVIDENCE-TEMPLATE.md) document with your deployment endpoint or repository link and uptime verification record.
2. Open a Pull Request following the guidelines in [CONTRIBUTING_TEMPLATES.md](CONTRIBUTING_TEMPLATES.md).
