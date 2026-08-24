# LORE — Final submission

## GitHub repository

https://github.com/kris70lesgo/lore-app

## Architecture overview

LORE is a protected organizational-memory AI for software teams. It observes issues, merge requests, review discussions, code diffs, incidents, and architectural decisions; predicts likely failures; verifies implementation promises; catches security regressions; and preserves institutional knowledge for future agents and developers.

Protegrity is the mandatory control plane. The isolated Privacy Gateway is the only service holding Developer Edition credentials. It discovers sensitive data, protects the complete canonical source, creates a pseudonymized and minimum-necessary AI view, rescans the result, and runs input/output Semantic Guardrails. Only the protected view may reach memory, scoped tools, or the provider-neutral NVIDIA adapter. Provider requests produce payload hashes, sizes, and zero-match outcomes rather than logged contents. Responses are scanned again before protected release. Every stage appends a hash-chained Protection Receipt.

The working implementation includes the complete issue-to-production LORE agent lifecycle, protected GitLab/GitHub memory adapters, a centralized model gateway, a live Privacy Control Center, trace details, a protection lab, eight-scenario Attack Lab, fail-closed outages, credential isolation, and 60 passing automated tests across the agent/API/privacy and CLI packages.

Detailed references:

- [Protected AI architecture](protegrity-architecture.md)
- [Threat model](threat-model.md)
- [Judge quickstart](judge-quickstart.md)
- [Limitations](limitations.md)
- [Optional Developer Edition feedback](developer-feedback.md)

## Demo video

Add the final 10–15 minute video URL here after recording. The walkthrough should follow [demo-script.md](demo-script.md).

LORE uses synthetic data for evaluation and demonstration. It makes no compliance, certification, or production-readiness claim.
