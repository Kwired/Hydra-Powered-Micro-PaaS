# Security Architecture & Audit Attestation

**Auditing Entity**: Kush Innovation Labs — Engineering & Security Review  
**Target Release**: HydraLite Production Release v1.0.0  
**Container Digest**: `ghcr.io/kwired/hydralite@sha256:6b59e09ddb50cce2849d638050ecb16eac4a9f15106869a23a671c5f24a3e6c2`  
**Assessment Result**: Approved — Zero Open Critical or High Vulnerabilities  

---

## Official Audit Certificate

A signed 3-page formal security audit certificate is available for download:
- [Download Signed Audit Certificate (PDF)](../AUDIT-CERTIFICATE-v1.0.0.pdf)
- [View on GitHub](https://github.com/Kwired/Hydra-Powered-Micro-PaaS/blob/production/v1.0.0/AUDIT-CERTIFICATE-v1.0.0.pdf)
- [Direct Download via GitHub Raw](https://raw.githubusercontent.com/Kwired/Hydra-Powered-Micro-PaaS/production/v1.0.0/AUDIT-CERTIFICATE-v1.0.0.pdf)

---

## Vulnerability Summary Matrix

| Severity Level | Identified | Remediated | Unresolved Findings | Status |
|:---|:---:|:---:|:---:|:---:|
| **Critical** | 0 | 0 | **0** | Pass |
| **High** | 0 | 0 | **0** | Pass |
| **Medium** | 0 | 0 | **0** | Pass |
| **Low / Informational** | 2 | 2 | **0** | Pass (Resolved) |

### Informational Findings & Remediations
1. **Container Privilege Hardening**: Initial development Docker configurations ran under default root user context. Resolved in v1.0.0 by enforcing `USER 1000:1000` across all container execution layers.
2. **CORS Origin Validation**: Development templates included permissive CORS headers. Resolved in v1.0.0 by requiring explicit domain whitelists via `ALLOWED_ORIGINS` in production mode.

---

## Architecture Security Controls

### 1. Bring Your Own Keys (BYOK)
HydraLite enforces strict process and credential isolation:
- The public-facing FastAPI service (`hydralite-api`) **has no filesystem or volume access to signing keys**.
- Cryptographic keys (`cardano.sk` and `hydra.sk`) are mounted into `hydra-node` exclusively in **read-only mode (`:ro`)**.
- Private keys are generated locally on the host using standard `cardano-cli` and `gen-hydra-key` binaries, with host permissions restricted to `0400`.

### 2. Supply Chain & Image Immutability
All deployment templates reference the immutable container digest:
```
ghcr.io/kwired/hydralite@sha256:6b59e09ddb50cce2849d638050ecb16eac4a9f15106869a23a671c5f24a3e6c2
```
This ensures that running instances match the exact code evaluated during the security audit.

### 3. Network Isolation
- **External Exposure**: Only port `8000` (API) and port `5001` (Hydra P2P) require network accessibility.
- **Internal Only**: Port `4001` (Hydra administrative WebSocket) and port `1338` (Ogmios) are bound to internal Docker bridge networking and blocked from external ingress.

---

## 12-Point Security Verification Checklist

| # | Check Item | Evaluation Standard | Audit Result |
|:---:|:---|:---|:---:|
| 1 | Minimal Base Image | Python 3.11-slim, no compilation toolchains left in runtime layers | PASS |
| 2 | Non-Root Context | Explicit UID/GID `1000:1000` enforcement | PASS |
| 3 | Static Analysis Scan | Automated AST vulnerability scan (Bandit & Safety) | PASS |
| 4 | Supply Chain Verification | Locked dependencies and cryptographically pinned image digest | PASS |
| 5 | Key Permissions Hardening | Host key file modes verified at `0400` | PASS |
| 6 | API Secret Separation | Zero private keys mounted into the public HTTP container | PASS |
| 7 | Strict CORS Enforcement | Whitelist domain matching enforced; wildcard disabled | PASS |
| 8 | WebSocket Backpressure | Connection keep-alive timeouts and frame buffering limits | PASS |
| 9 | Contestation Enforcement | Minimum contestation window maintained during head closure | PASS |
| 10 | Ephemeral CLI Containers | Minting and admin containers executed with `--rm` flag | PASS |
| 11 | Mithril Snapshot Integrity | Genesis verification key check during bootstrap | PASS |
| 12 | Health Probe Isolation | Health probes execute unprivileged local socket checks | PASS |
