# Security Policy

## Supported Versions

Only the `v1.0.0` production release is actively supported for security updates. 

| Version | Supported          |
| ------- | ------------------ |
| v1.0.x  | :white_check_mark: |
| < v1.0  | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability within this project, please send an email to the designated security contact (TBD). All security vulnerabilities will be promptly addressed.

**Do not** publicly disclose the issue until it has been resolved.

## Security Assumptions
- The server running the Hydra Node is secure and isolated.
- The `keys/` directory is heavily restricted (`chmod 600`) and never exposed publicly.
- The WebSocket and API endpoints of the Hydra Node should not be exposed to the public internet without proper authentication/proxy layers.
- No real credentials or wallet seed phrases should ever be committed to this repository.
