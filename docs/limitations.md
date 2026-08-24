# Security and product limitations

LORE is a competitive prototype, not a production security certification.

- Demonstrations use synthetic identifiers, secrets, issues, and decisions.
- Protegrity Developer Edition credentials and official service images are required for the real protection path.
- The canonical protected envelope is currently produced and verified inside the gateway but not persisted or exposed through a reveal workflow; organizational memory stores the minimized protected representation.
- Project/tool authorization uses the configured GitLab or GitHub integration context. Production multi-tenant use requires an independent identity, consent, role, and tenant-isolation review.
- Semantic classifiers and language models can make mistakes. LORE layers deterministic secret detection, fail-closed postconditions, output scanning, and human review around them.
- Carbon estimates are directional engineering estimates, not audited sustainability measurements.
- Production use requires independent security testing, legal/privacy review, retention and deletion policy, incident response, monitoring, availability, backup, and disaster-recovery work.
