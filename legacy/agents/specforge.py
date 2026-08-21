"""
SPECFORGE agent: triggered when @lore is mentioned in a GitLab issue. Reads the
issue, finds relevant LORE memories, and generates a full engineering spec
posted as a structured comment. Also handles spec approval and MR spec compliance.
"""

import json
import logging
import re

from config import LORE_SPEC_SLUG_PREFIX
from core.gitlab_client import GitLabClient
from core.llm_gateway import LLMGateway
from core.memory import MemoryStore
from core.telemetry import EventType, get_default_recorder, new_trace_id

logger = logging.getLogger("lore.specforge")

# Stop words for keyword extraction (Step 4).
_STOP_WORDS = frozenset([
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above", "below",
    "and", "or", "but", "if", "then", "that", "this", "it", "its", "we",
    "i", "you", "he", "she", "they", "what", "which", "who", "when",
    "where", "how", "all", "any", "both", "each", "few", "more", "most",
    "other", "some", "such", "no", "not", "only", "same", "so", "than",
    "too", "very", "just", "new", "add", "update", "change", "get", "use",
])


def _extract_keywords(text: str) -> set[str]:
    """
    Extracts meaningful keywords from text for memory relevance matching.
    Lowercases, splits on non-alphanumeric characters, removes stop words
    and short tokens.
    """
    tokens = re.split(r"[^a-z0-9]+", text.lower())
    return {
        t for t in tokens
        if len(t) > 3 and t not in _STOP_WORDS
    }


async def run_specforge(payload: dict, trace_id: str | None = None) -> None:
    """
    Run SPECFORGE: read issue, find relevant memories, generate engineering
    spec via Claude, and post as issue comments.
    """
    issue_iid: int | None = None
    trace_id = trace_id or new_trace_id()
    telemetry = get_default_recorder()
    telemetry.emit(
        EventType.AGENT_STARTED,
        trace_id,
        agent_id="specforge",
        agent_name="SPECFORGE",
        source="lore",
        destination="agent",
    )
    def finish(result: str) -> None:
        telemetry.emit(
            EventType.AGENT_FINISHED,
            trace_id,
            agent_id="specforge",
            agent_name="SPECFORGE",
            metadata={"issue_iid": issue_iid, "result": result},
        )

    try:
        # — Step 1: Extract data from webhook payload —
        issue_iid = int(payload["object_attributes"]["iid"])
        issue_title = payload["object_attributes"]["title"]
        issue_description = payload["object_attributes"]["description"] or ""
        issue_author = payload["user"]["username"]
        issue_url = payload["object_attributes"]["url"]

        # — Step 2: Initialise clients —
        gitlab = GitLabClient(trace_id=trace_id)
        llm = LLMGateway(trace_id=trace_id)
        memory_store = MemoryStore(gitlab, trace_id=trace_id)

        # — Step 3: Post immediate acknowledgement comment (before any heavy work) —
        gitlab.post_issue_comment(
            issue_iid,
            f"🧠 LORE — SPECFORGE\n\n"
            f"*@{issue_author} — Analysing your issue and generating an engineering "
            "specification. This will take about 30 seconds...*",
        )

        # — Step 4: Find relevant memories —
        all_memories = memory_store.get_all_memories()
        if not all_memories:
            relevant_memories: list[dict] = []
        else:
            combined_issue_text = f"{issue_title} {issue_description}"
            issue_keywords = _extract_keywords(combined_issue_text)
            relevant_memories = []
            for mem in all_memories:
                decision_lower = (mem.get("decision") or "").lower()
                implication_lower = (mem.get("future_implication") or "").lower()
                governs_lower = [ (p or "").lower() for p in (mem.get("governs_files") or []) ]
                searchable = f"{decision_lower} {implication_lower} {' '.join(governs_lower)}"
                if any(kw in searchable for kw in issue_keywords):
                    relevant_memories.append(mem)
            relevant_memories = relevant_memories[:10]

        # — Step 5: Build the user message for Claude —
        if not relevant_memories:
            relevant_block = (
                "None found. Generate the spec based on the issue description alone."
            )
        else:
            parts = []
            for m in relevant_memories:
                governs = ", ".join(m.get("governs_files") or [])
                parts.append(
                    f"---\n"
                    f"Memory #{m.get('id', '')}\n"
                    f"Decision: {m.get('decision', '')}\n"
                    f"Future implication: {m.get('future_implication', '')}\n"
                    f"Governs files: {governs}\n"
                    f"---"
                )
            relevant_block = "\n\n".join(parts)

        user_message = (
            f"ISSUE TITLE: {issue_title}\n"
            f"ISSUE AUTHOR: @{issue_author}\n"
            f"ISSUE DESCRIPTION:\n{issue_description}\n\n"
            f"RELEVANT MEMORIES:\n{relevant_block}"
        )

        # — Step 6: Call Claude —
        system_prompt = llm.load_prompt("specforge")
        response = llm.call(
            system_prompt=system_prompt,
            user_message=user_message,
            max_tokens=3000,
            agent_id="specforge",
            agent_name="SPECFORGE",
        )

        # — Step 7: Validate the response —
        if len(response) <= 100 or "Acceptance Criteria" not in response:
            gitlab.post_issue_comment(
                issue_iid,
                "🧠 LORE — SPECFORGE\n\n"
                "*Spec generation produced an incomplete result. "
                "Please try again by editing the issue description with more detail.*",
            )
            finish("incomplete_spec")
            return

        # — Step 8: Post the spec and then the summary comment —
        gitlab.post_issue_comment(issue_iid, response)

        gitlab.add_issue_label(issue_iid, "lore-spec-pending")

        mem_ids_str = "none" if not relevant_memories else ", ".join(
            f"#{m.get('id', '')}" for m in relevant_memories
        )
        gitlab.post_issue_comment(
            issue_iid,
            f"🧠 LORE — SPECFORGE\n\n"
            f"✅ Spec generated. {len(relevant_memories)} relevant memories considered.\n\n"
            "**Next step:** Review the spec above, make any edits needed, then reply "
            "`lore: spec approved` or `approved` to lock this as the implementation contract.\n\n"
            f"*Relevant memories: {mem_ids_str}*",
        )
        finish("spec_generated")

    except Exception as e:
        logger.error("SPECFORGE failed: %s", e, exc_info=True)
        telemetry.emit(
            EventType.ERROR_OCCURRED,
            trace_id,
            agent_id="specforge",
            agent_name="SPECFORGE",
            metadata={"error_type": type(e).__name__},
        )
        try:
            if issue_iid is not None:
                gitlab = GitLabClient(trace_id=trace_id)
                gitlab.post_issue_comment(
                    issue_iid,
                    "🧠 LORE — SPECFORGE\n\n"
                    "*An error occurred during spec generation. Check server logs.*",
                )
            else:
                issue_iid = payload.get("object_attributes", {}).get("iid")
                if issue_iid is not None:
                    gitlab = GitLabClient(trace_id=trace_id)
                    gitlab.post_issue_comment(
                        int(issue_iid),
                        "🧠 LORE — SPECFORGE\n\n"
                        "*An error occurred during spec generation. Check server logs.*",
                    )
        except Exception:
            pass


def _find_spec_comment_body(notes: list[dict]) -> str | None:
    """Find the first note that looks like the SPECFORGE spec (has Engineering Specification + Acceptance Criteria)."""
    for n in notes:
        body = (n.get("body") or "").strip()
        if "Engineering Specification" in body and "Acceptance Criteria" in body:
            return body
    return None


async def handle_spec_approval(payload: dict, trace_id: str | None = None) -> None:
    """
    When someone replies 'lore: spec approved' or 'approved' on an issue, store the spec
    in the wiki and set label lore-spec-approved.
    """
    issue_iid: int | None = None
    trace_id = trace_id or new_trace_id()
    telemetry = get_default_recorder()
    telemetry.emit(
        EventType.AGENT_STARTED,
        trace_id,
        agent_id="spec_approval",
        agent_name="SPECFORGE Spec Approval",
        source="lore",
        destination="agent",
    )
    def finish(result: str) -> None:
        telemetry.emit(
            EventType.AGENT_FINISHED,
            trace_id,
            agent_id="spec_approval",
            agent_name="SPECFORGE Spec Approval",
            metadata={"issue_iid": issue_iid, "result": result},
        )

    try:
        note_body = (payload.get("object_attributes") or {}).get("note", "").strip().lower()
        if "lore: spec approved" not in note_body and "approved" != note_body.strip():
            finish("ignored")
            return
        noteable_type = (payload.get("object_attributes") or {}).get("noteable_type", "")
        if noteable_type != "Issue":
            finish("ignored")
            return

        # Note Hook: issue IID is in payload.issue.iid (noteable_id is internal DB id)
        issue_iid = (payload.get("issue") or {}).get("iid") or (payload.get("object_attributes") or {}).get("noteable_id")
        if issue_iid is None:
            finish("missing_issue")
            return
        issue_iid = int(issue_iid)
        gitlab = GitLabClient(trace_id=trace_id)

        notes = gitlab.get_issue_notes(issue_iid)
        spec_body = _find_spec_comment_body(notes)
        if not spec_body:
            gitlab.post_issue_comment(
                issue_iid,
                "🧠 LORE — SPECFORGE\n\n*No prior spec comment found on this issue. "
                "Mention @lore in the issue description first to generate a spec.*",
            )
            finish("no_spec_found")
            return

        slug = f"{LORE_SPEC_SLUG_PREFIX}{issue_iid}"
        existing = gitlab.get_wiki_page(slug)
        if existing is None:
            gitlab.create_wiki_page(slug, slug, spec_body)
        else:
            gitlab.update_wiki_page(slug, spec_body)

        labels = list(gitlab.get_issue_labels(issue_iid))
        if "lore-spec-pending" in labels:
            labels.remove("lore-spec-pending")
        if "lore-spec-approved" not in labels:
            labels.append("lore-spec-approved")
        gitlab.set_issue_labels(issue_iid, labels)

        gitlab.post_issue_comment(
            issue_iid,
            "🧠 LORE — SPECFORGE\n\n✅ **Spec approved and stored.** This spec will be used to check "
            "compliance when MRs linked to this issue are opened.",
        )
        finish("spec_stored")
    except Exception as e:
        logger.error("Spec approval failed: %s", e, exc_info=True)
        telemetry.emit(
            EventType.ERROR_OCCURRED,
            trace_id,
            agent_id="spec_approval",
            agent_name="SPECFORGE Spec Approval",
            metadata={"error_type": type(e).__name__},
        )
        if issue_iid is not None:
            try:
                gitlab = GitLabClient(trace_id=trace_id)
                gitlab.post_issue_comment(
                    issue_iid,
                    "🧠 LORE — SPECFORGE\n\n*Failed to store approved spec. Check server logs.*",
                )
            except Exception:
                pass


async def run_spec_compliance(payload: dict, trace_id: str | None = None) -> None:
    """
    When an MR is opened, if it links to an issue with an approved spec, compare the MR diff
    to the spec and post a compliance report on the MR.
    """
    mr_iid: int | None = None
    trace_id = trace_id or new_trace_id()
    telemetry = get_default_recorder()
    telemetry.emit(
        EventType.AGENT_STARTED,
        trace_id,
        agent_id="spec_compliance",
        agent_name="SPECFORGE Compliance",
        source="lore",
        destination="agent",
    )
    def finish(result: str) -> None:
        telemetry.emit(
            EventType.AGENT_FINISHED,
            trace_id,
            agent_id="spec_compliance",
            agent_name="SPECFORGE Compliance",
            metadata={"mr_iid": mr_iid, "result": result},
        )

    try:
        mr_iid = int(payload.get("object_attributes", {}).get("iid"))
        gitlab = GitLabClient(trace_id=trace_id)
        llm = LLMGateway(trace_id=trace_id)

        linked_issue_iids = gitlab.get_mr_linked_issue_iids(mr_iid)
        if not linked_issue_iids:
            finish("no_linked_issue")
            return

        spec_content: str | None = None
        issue_iid_used: int | None = None
        for iid in linked_issue_iids:
            slug = f"{LORE_SPEC_SLUG_PREFIX}{iid}"
            content = gitlab.get_wiki_page(slug)
            if content and "Acceptance Criteria" in content:
                spec_content = content
                issue_iid_used = iid
                break

        if not spec_content:
            finish("no_approved_spec")
            return

        try:
            full_diff = gitlab.get_mr_diff(mr_iid)
        except RuntimeError:
            full_diff = "(Diff unavailable.)"

        mr_title = payload.get("object_attributes", {}).get("title", "")
        mr_description = payload.get("object_attributes", {}).get("description", "")

        user_message = (
            f"APPROVED SPEC (from issue #{issue_iid_used}):\n```\n{spec_content[:30000]}\n```\n\n"
            f"MR TITLE: {mr_title}\n"
            f"MR DESCRIPTION:\n{mr_description}\n\n"
            f"DIFF:\n```\n{full_diff[:40000]}\n```"
        )

        system_prompt = llm.load_prompt("spec_compliance")
        response_str = llm.call(
            system_prompt=system_prompt,
            user_message=user_message,
            max_tokens=2000,
            agent_id="spec_compliance",
            agent_name="SPECFORGE Compliance",
        )

        try:
            result = json.loads(response_str)
        except json.JSONDecodeError:
            gitlab.post_mr_comment(
                mr_iid,
                "🧠 LORE — SPECFORGE Compliance\n\n*Compliance check could not parse result.*",
            )
            finish("parse_error")
            return

        criteria_met = result.get("criteria_met") or []
        criteria_missing = result.get("criteria_missing") or []
        undescribed = result.get("undescribed_changes") or []
        summary = result.get("summary", "")

        parts = [
            "🧠 LORE — SPECFORGE Compliance",
            "",
            f"*Spec from issue #{issue_iid_used}*",
            "",
            "## Acceptance criteria",
            "",
        ]
        for c in criteria_met:
            parts.append(f"- ✅ {c.get('criterion', '')} — {c.get('location', '')}")
        for c in criteria_missing:
            parts.append(f"- ❌ {c.get('criterion', '')} — {c.get('note', '')}")
        if undescribed:
            parts.append("")
            parts.append("## Undescribed changes")
            parts.append("")
            for u in undescribed:
                parts.append(f"- **{u.get('location', '')}**: {u.get('description', '')}")
                if u.get("question"):
                    parts.append(f"  *{u['question']}*")
        parts.append("")
        parts.append(f"**Summary:** {summary}")

        gitlab.post_mr_comment(mr_iid, "\n".join(parts))
        finish("compliance_posted")
    except Exception as e:
        logger.error("Spec compliance failed: %s", e, exc_info=True)
        telemetry.emit(
            EventType.ERROR_OCCURRED,
            trace_id,
            agent_id="spec_compliance",
            agent_name="SPECFORGE Compliance",
            metadata={"error_type": type(e).__name__},
        )
        if mr_iid is not None:
            try:
                gitlab = GitLabClient(trace_id=trace_id)
                gitlab.post_mr_comment(
                    mr_iid,
                    "🧠 LORE — SPECFORGE Compliance\n\n*Compliance check failed. Check server logs.*",
                )
            except Exception:
                pass
