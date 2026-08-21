import asyncio
import logging
import hmac
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import GITHUB_MEMORY_REPOSITORY, GITHUB_OWNER, WEBHOOK_SECRET, PORT
from core.protection import ProtectionBlocked, get_default_protection_gateway
from core.telemetry import (
    EventType,
    get_default_recorder,
    get_trace,
    list_traces,
    new_trace_id,
    read_events,
    security_overview,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("LORE server starting up")
    yield
    logger.info("LORE server shutting down")


app = FastAPI(
    title="LORE — Living Organisational Record Engine",
    description="Multi-agent GitLab automation for institutional memory",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_webhook_secret(token: str) -> bool:
    """Verify the GitLab webhook secret token."""
    if not WEBHOOK_SECRET:
        return True
    return hmac.compare_digest(token or "", WEBHOOK_SECRET)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "LORE"}


@app.get("/api/security/overview")
async def api_security_overview():
    """Dashboard aggregate for protection, telemetry, and trace activity."""
    return security_overview()


@app.get("/api/security/events")
async def api_security_events(limit: int = 100):
    """Recent telemetry events, already scrubbed by the telemetry sink."""
    return {"events": read_events(limit=max(1, min(limit, 500)))}


@app.get("/api/traces")
async def api_traces(limit: int = 50):
    """Trace summaries for the Security Control Center."""
    return {"traces": list_traces(limit=max(1, min(limit, 200)))}


@app.get("/api/traces/{trace_id}")
async def api_trace(trace_id: str):
    """Full ordered timeline for one trace."""
    trace = get_trace(trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace


@app.get("/api/memories")
async def api_memories():
    """Return protected LORE memories from the configured GitHub memory repository."""
    trace_id = new_trace_id()
    try:
        if not (GITHUB_OWNER and GITHUB_MEMORY_REPOSITORY):
            raise RuntimeError("GitHub memory is not configured")
        from core.github_memory_client import GitHubMemoryClient
        from core.memory import MemoryStore

        github = GitHubMemoryClient(trace_id=trace_id)
        memories = MemoryStore(github, trace_id=trace_id).get_all_memories()
        return {"memories": memories, "source": "github_repository", "trace_id": trace_id}
    except Exception as exc:
        return {
            "memories": [],
            "source": "unavailable",
            "trace_id": trace_id,
            "message": "GitHub memory is unavailable. Configure GitHub credentials to enable this endpoint.",
            "error_type": type(exc).__name__,
        }


@app.post("/api/demo/protect")
async def api_demo_protect(request: Request):
    """Run the LORE protection boundary on arbitrary demo text."""
    payload = await request.json()
    text = str(payload.get("text") or "")
    trace_id = str(payload.get("trace_id") or new_trace_id())
    gateway = get_default_protection_gateway()
    result = gateway.protect_text(text, {"boundary": "demo_protect", "trace_id": trace_id})
    return {"trace_id": trace_id, **result.to_public_dict()}


@app.post("/api/demo/attack")
async def api_demo_attack(request: Request):
    """Run semantic guardrails against a prompt-injection/exfiltration demo."""
    payload = await request.json()
    text = str(payload.get("text") or "")
    trace_id = str(payload.get("trace_id") or new_trace_id())
    gateway = get_default_protection_gateway()
    try:
        result = gateway.assess_prompt(text, {"trace_id": trace_id})
    except ProtectionBlocked as exc:
        return {
            "trace_id": trace_id,
            "text": "[PROMPT_BLOCKED]",
            "findings": [],
            "categories": [],
            "blocked": True,
            "risk_score": 0.96,
            "policy_result": "blocked",
            "reason": str(exc),
        }
    return {"trace_id": trace_id, **result.to_public_dict()}


@app.post("/webhook")
async def webhook(
    request: Request,
    x_gitlab_event: str = Header(None),
    x_gitlab_token: str = Header(None),
):
    """
    Main webhook receiver. Routes all GitLab events to the correct agent.
    """
    if not verify_webhook_secret(x_gitlab_token):
        logger.warning("Webhook received with invalid secret token")
        raise HTTPException(status_code=401, detail="Invalid webhook token")

    payload = await request.json()
    trace_id = new_trace_id()
    telemetry = get_default_recorder()
    logger.info("Received GitLab event: %s", x_gitlab_event)
    telemetry.emit(
        EventType.AGENT_STARTED,
        trace_id,
        agent_id="webhook",
        agent_name="GitLab Webhook",
        source="gitlab",
        destination="lore",
        metadata={"gitlab_event": x_gitlab_event},
    )

    try:
        if x_gitlab_event == "Merge Request Hook":
            action = payload.get("object_attributes", {}).get("action")
            logger.info("MR action: %s", action)

            if action == "merge":
                logger.info("Routing to LOREKEEPER")
                from agents.lorekeeper import run_lorekeeper

                await run_lorekeeper(payload, trace_id=trace_id)

            elif action == "open":
                logger.info("Routing to GUARDKEEPER and SPECFORGE compliance")
                from agents.guardkeeper import run_guardkeeper
                from agents.specforge import run_spec_compliance

                await asyncio.gather(
                    run_guardkeeper(payload, trace_id=trace_id),
                    run_spec_compliance(payload, trace_id=trace_id),
                )

            else:
                logger.info("MR action '%s' — no agent handles this", action)

        elif x_gitlab_event == "Note Hook":
            note_body = (payload.get("object_attributes", {}).get("note") or "").lower()
            noteable_type = payload.get("object_attributes", {}).get("noteable_type", "")
            logger.info("Note on %s: %s", noteable_type, note_body[:80])

            if noteable_type == "MergeRequest":
                if "lore: intentional" in note_body:
                    logger.info("Routing to GUARDKEEPER reply handler — intentional")
                    from agents.guardkeeper import run_guardkeeper

                    await run_guardkeeper(payload, reply_type="intentional", trace_id=trace_id)
                elif "lore: accidental" in note_body:
                    logger.info("Routing to GUARDKEEPER reply handler — accidental")
                    from agents.guardkeeper import run_guardkeeper

                    await run_guardkeeper(payload, reply_type="accidental", trace_id=trace_id)
                elif "lore: discuss" in note_body:
                    logger.info("Routing to GUARDKEEPER reply handler — discuss")
                    from agents.guardkeeper import run_guardkeeper

                    await run_guardkeeper(payload, reply_type="discuss", trace_id=trace_id)

            elif noteable_type == "Issue":
                if "lore: spec approved" in note_body or note_body.strip() == "approved":
                    logger.info("Routing to SPECFORGE spec approval")
                    from agents.specforge import handle_spec_approval

                    await handle_spec_approval(payload, trace_id=trace_id)
                if "lore health" in note_body or "@lore health" in note_body:
                    logger.info("Routing to LORECAST (triggered by @lore health)")
                    from agents.lorecast import run_lorecast

                    await run_lorecast(trace_id=trace_id)

        elif x_gitlab_event == "Issue Hook":
            issue_body = payload.get("object_attributes", {}).get("description", "") or ""
            title = payload.get("object_attributes", {}).get("title", "") or ""
            if "@lore" in issue_body or "@lore" in title:
                logger.info("Routing to SPECFORGE")
                from agents.specforge import run_specforge

                await run_specforge(payload, trace_id=trace_id)
            if "lore health" in (issue_body + " " + title).lower() or "@lore health" in (issue_body + title):
                logger.info("Routing to LORECAST (triggered by @lore health in issue)")
                from agents.lorecast import run_lorecast

                await run_lorecast(trace_id=trace_id)

        else:
            logger.info("Unhandled event type: %s", x_gitlab_event)

    except Exception as e:
        logger.error("Error processing webhook: %s", e, exc_info=True)
        telemetry.emit(
            EventType.ERROR_OCCURRED,
            trace_id,
            agent_id="webhook",
            agent_name="GitLab Webhook",
            metadata={"error_type": type(e).__name__},
        )
        return JSONResponse(
            status_code=200,
            content={"status": "error", "message": str(e)},
        )

    telemetry.emit(
        EventType.AGENT_FINISHED,
        trace_id,
        agent_id="webhook",
        agent_name="GitLab Webhook",
        source="lore",
        destination="gitlab",
        metadata={"gitlab_event": x_gitlab_event},
    )
    return JSONResponse(status_code=200, content={"status": "received"})


@app.post("/lorecast")
async def trigger_lorecast():
    """
    On-demand trigger for LORECAST health report.
    Hit this endpoint manually or for demo purposes.
    """
    logger.info("LORECAST triggered manually via /lorecast endpoint")
    trace_id = new_trace_id()
    try:
        from agents.lorecast import run_lorecast

        await run_lorecast(trace_id=trace_id)
        return JSONResponse(status_code=200, content={"status": "lorecast complete"})
    except Exception as e:
        logger.error("LORECAST failed: %s", e, exc_info=True)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
