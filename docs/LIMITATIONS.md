# Limitations

- **Payments**: entitlement UX exists; checkout is not implemented and must not be faked.
- **Auctions**: removed. No live or demo auction catalog.
- **AI engine**: this tree does not contain a LangGraph/Groq V2 orchestrator. Feasibility remains deterministic calculator + workspace. Do not claim live agentic studies until that engine exists in this repo.
- **Arabic PDF**: Helvetica-based PDF remains a known limitation for native Arabic shaping; DOCX is the more reliable Arabic export.
- **Catalogs**: funding/opportunity/franchise rows may be verified, under review, or demo/unverified. Labels must stay visible.
- **Email**: verification/reset depend on SMTP configuration.
- **Object storage**: funding documents need Cloudflare R2 variables in production.
