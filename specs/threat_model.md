# Omega Runtime v0.1 Threat Model

## Protected boundary

Agent proposal -> verifier -> certificate -> proxy -> sandbox tool.

## Initial attacks

- Missing certificate
- Action tamper after certificate
- Replay using same nonce
- Path escape outside sandbox
- Unknown tool call

## Out of scope for v0.1

- Real cloud APIs
- Browser automation
- Real identity systems
- Ed25519 production keys
- Formal proof assistant verification
