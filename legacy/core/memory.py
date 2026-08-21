"""
LORE memory store: wiki-backed storage and indexing of architectural decisions.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from config import LORE_INDEX_SLUG, MEMORY_SLUG_PREFIX

from .models import MemoryRecord
from .protection import ProtectionGateway, get_default_protection_gateway
from .telemetry import EventType, TelemetryRecorder, get_default_recorder, new_trace_id

if TYPE_CHECKING:
    from .gitlab_client import GitLabClient

logger = logging.getLogger("lore.memory")


def _zero_pad_id(memory_id: str) -> str:
    """Return zero-padded 3-digit id for slug."""
    try:
        n = int(memory_id)
        return f"{n:03d}"
    except (TypeError, ValueError):
        return memory_id.zfill(3) if len(memory_id) < 3 else memory_id


class MemoryStore:
    """
    Handles all LORE memory operations using GitLab wiki via GitLabClient.
    """

    def __init__(
        self,
        gitlab: GitLabClient,
        telemetry: TelemetryRecorder | None = None,
        protection_gateway: ProtectionGateway | None = None,
        trace_id: str | None = None,
    ) -> None:
        """Store the GitLab client reference for wiki operations."""
        self._gitlab = gitlab
        self._telemetry = telemetry or get_default_recorder()
        self._protection = protection_gateway or get_default_protection_gateway()
        self._trace_id = trace_id or getattr(gitlab, "trace_id", None) or new_trace_id()

    def _parse_memory(self, content: str) -> dict:
        """
        Parse a wiki page string into a memory dict with keys: id, source_mr_number,
        source_mr_title, date, governs_files, decision, rejected, reason,
        future_implication, decided_by, confidence, status.
        """
        return self.after_memory_read(MemoryRecord.from_wiki_markdown(content)).to_legacy_dict()

    def _serialize_memory(self, memory: dict) -> str:
        """
        Convert a memory dict into the LORE wiki markdown format.
        """
        record = MemoryRecord.from_dict(memory)
        return record.to_wiki_markdown()

    def before_memory_write(self, record: MemoryRecord) -> MemoryRecord:
        """Memory write boundary for future protection."""
        return self._protection.protect(
            record,
            {"boundary": "pre_memory_write", "trace_id": self._trace_id},
        )

    def after_memory_read(self, record: MemoryRecord) -> MemoryRecord:
        """Memory read boundary that prevents raw sensitive data reaching agents."""
        return self._protection.protect(
            record,
            {"boundary": "post_memory_read", "trace_id": self._trace_id},
        )

    def save_memory(self, memory: dict) -> str:
        """
        Save memory to wiki, update LORE-INDEX, and return the page slug.
        """
        try:
            memory_id = str(memory.get("id", "")).strip()
            if not memory_id:
                pad = "001"
                slugs = self._gitlab.list_wiki_pages()
                existing = [s for s in slugs if s.startswith(MEMORY_SLUG_PREFIX)]
                if existing:
                    nums = []
                    for s in existing:
                        suffix = s.replace(MEMORY_SLUG_PREFIX, "")
                        if suffix.isdigit():
                            nums.append(int(suffix))
                    pad = f"{max(nums) + 1:03d}" if nums else "001"
                memory_id = pad
                memory["id"] = memory_id
            else:
                pad = _zero_pad_id(memory_id)
            slug = f"{MEMORY_SLUG_PREFIX}{pad}"
            record = self.before_memory_write(MemoryRecord.from_dict(memory))
            content = record.to_wiki_markdown()
            existing = self._gitlab.get_wiki_page(slug)
            if existing is None:
                self._gitlab.create_wiki_page(slug, slug, content)
            else:
                self._gitlab.update_wiki_page(slug, content)
            self._update_index(memory_id, record.governed_files)
            self._telemetry.emit(
                EventType.MEMORY_WRITE,
                self._trace_id,
                source="lore",
                destination="gitlab_wiki",
                resource=slug,
                metadata={"memory_id": memory_id, "governed_file_count": len(record.governed_files)},
            )
            return slug
        except RuntimeError:
            raise
        except Exception as e:
            logger.exception("Failed to save memory")
            raise RuntimeError(f"Failed to save memory: {e}") from e

    def get_memory(self, memory_id: str) -> dict | None:
        """
        Fetch and parse a single memory by id (e.g. '001'). Returns None if not found.
        """
        try:
            pad = _zero_pad_id(memory_id)
            slug = f"{MEMORY_SLUG_PREFIX}{pad}"
            content = self._gitlab.get_wiki_page(slug)
            if content is None or not content.strip():
                return None
            memory = self._parse_memory(content)
            self._telemetry.emit(
                EventType.MEMORY_READ,
                self._trace_id,
                source="gitlab_wiki",
                destination="lore",
                resource=slug,
                metadata={"memory_id": memory_id},
            )
            return memory
        except RuntimeError:
            raise
        except Exception as e:
            logger.exception("Failed to get memory %s", memory_id)
            raise RuntimeError(f"Failed to get memory {memory_id}: {e}") from e

    def get_memories_for_files(self, file_paths: list[str]) -> list[dict]:
        """
        Read LORE-INDEX, find all memory IDs that govern any of the given file paths,
        fetch and return those memories.
        """
        try:
            content = self._gitlab.get_wiki_page(LORE_INDEX_SLUG)
            if not content or not file_paths:
                return []
            path_set = set(f.strip() for f in file_paths if f and f.strip())
            if not path_set:
                return []
            index = self._parse_index(content)
            memory_ids: set[str] = set()
            for path in path_set:
                for fid in index.get(path, []):
                    memory_ids.add(fid)
            result: list[dict] = []
            for mid in memory_ids:
                mem = self.get_memory(mid)
                if mem:
                    result.append(mem)
            return result
        except RuntimeError:
            raise
        except Exception as e:
            logger.exception("Failed to get memories for files")
            raise RuntimeError(f"Failed to get memories for files: {e}") from e

    def _parse_index(self, content: str) -> dict[str, list[str]]:
        """Parse LORE-INDEX markdown table into dict: file_path -> list of memory ids."""
        index: dict[str, list[str]] = {}
        lines = content.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#") or "|" not in line:
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 2 and parts[0].lower() != "file path":
                path = parts[0]
                ids_str = parts[1]
                ids = [i.strip() for i in ids_str.replace(" ", "").split(",") if i.strip()]
                if path and ids:
                    index[path] = ids
        return index

    def get_all_memories(self) -> list[dict]:
        """
        Fetch and parse every LORE-MEMORY-* wiki page.
        """
        try:
            slugs = self._gitlab.list_wiki_pages()
            memory_slugs = sorted(s for s in slugs if s.startswith(MEMORY_SLUG_PREFIX))
            result: list[dict] = []
            for slug in memory_slugs:
                content = self._gitlab.get_wiki_page(slug)
                if content and content.strip():
                    result.append(self._parse_memory(content))
            self._telemetry.emit(
                EventType.MEMORY_READ,
                self._trace_id,
                source="gitlab_wiki",
                destination="lore",
                resource=MEMORY_SLUG_PREFIX,
                metadata={"memory_count": len(result)},
            )
            return result
        except RuntimeError:
            raise
        except Exception as e:
            logger.exception("Failed to get all memories")
            raise RuntimeError(f"Failed to get all memories: {e}") from e

    def update_memory_status(
        self, memory_id: str, status: str, append_note: str | None = None
    ) -> None:
        """
        Update the status field of a memory; optionally append a note to the reason field.
        """
        try:
            mem = self.get_memory(memory_id)
            if not mem:
                raise RuntimeError(f"Memory {memory_id} not found")
            mem["status"] = status
            if append_note:
                mem["reason"] = (mem.get("reason") or "").strip()
                if mem["reason"]:
                    mem["reason"] += "\n" + append_note
                else:
                    mem["reason"] = append_note
            pad = _zero_pad_id(memory_id)
            slug = f"{MEMORY_SLUG_PREFIX}{pad}"
            record = self.before_memory_write(MemoryRecord.from_dict(mem))
            self._gitlab.update_wiki_page(slug, record.to_wiki_markdown())
            self._telemetry.emit(
                EventType.MEMORY_WRITE,
                self._trace_id,
                source="lore",
                destination="gitlab_wiki",
                resource=slug,
                metadata={"memory_id": memory_id, "status": status},
            )
        except RuntimeError:
            raise
        except Exception as e:
            logger.exception("Failed to update memory status for %s", memory_id)
            raise RuntimeError(f"Failed to update memory status: {e}") from e

    def ensure_index_exists(self) -> None:
        """
        Create the LORE-INDEX wiki page if it does not exist yet.
        """
        try:
            content = self._gitlab.get_wiki_page(LORE_INDEX_SLUG)
            if content is not None:
                return
            initial = "# LORE Index\n\n| File Path | Memory IDs |\n"
            self._gitlab.create_wiki_page(LORE_INDEX_SLUG, LORE_INDEX_SLUG, initial)
        except RuntimeError:
            raise
        except Exception as e:
            logger.exception("Failed to ensure LORE-INDEX exists")
            raise RuntimeError(f"Failed to ensure index exists: {e}") from e

    def _update_index(self, memory_id: str, file_paths: list[str]) -> None:
        """
        Add the memory_id -> file_paths mapping to LORE-INDEX. Merges with existing rows.
        """
        try:
            self.ensure_index_exists()
            content = self._gitlab.get_wiki_page(LORE_INDEX_SLUG)
            if not content:
                raise RuntimeError("LORE-INDEX missing after ensure_index_exists")
            index = self._parse_index(content)
            pad = _zero_pad_id(memory_id)
            for path in file_paths:
                path = path.strip()
                if not path:
                    continue
                if path not in index:
                    index[path] = []
                if pad not in index[path]:
                    index[path].append(pad)
            lines = ["# LORE Index", "", "| File Path | Memory IDs |", "| --- | --- |"]
            for path in sorted(index.keys()):
                ids_str = ", ".join(sorted(index[path]))
                lines.append(f"| {path} | {ids_str} |")
            self._gitlab.update_wiki_page(LORE_INDEX_SLUG, "\n".join(lines) + "\n")
        except RuntimeError:
            raise
        except Exception as e:
            logger.exception("Failed to update LORE-INDEX")
            raise RuntimeError(f"Failed to update index: {e}") from e
