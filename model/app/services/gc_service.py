import logging
import numpy as np
from datetime import datetime, timezone
from typing import Dict, Any, List, Set

from app.config import (
    MAX_VERSION_HISTORY,
    DUPLICATE_SIMILARITY_THRESHOLD,
)
from app.schemas.chunk_metadata_schema import ChunkMetadata, ChunkStatus
from app.services.qdrant_service import QdrantService
from app.services.archive_service import ArchiveService
from app.utils.embeddings import embed_text

logger = logging.getLogger("evorag.gc")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

qdrant_service = QdrantService()
archive_service = ArchiveService()


def parse_dt(dt_val: Any) -> datetime:
    """Helper to parse datetime or ISO string to UTC datetime object."""
    if isinstance(dt_val, datetime):
        return dt_val if dt_val.tzinfo else dt_val.replace(tzinfo=timezone.utc)
    if isinstance(dt_val, str):
        try:
            dt = datetime.fromisoformat(dt_val)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


class GCService:
    """
    Garbage Collection and Storage Compaction Service for EvoRAG.
    Keeps active Qdrant vector collection lean by offloading obsolete, old versioned,
    and duplicate chunks to SQLite cold storage.
    """

    def __init__(self):
        self.qdrant = qdrant_service
        self.archive = archive_service

    def run_garbage_collection(self) -> Dict[str, Any]:
        """
        Executes three-pass garbage collection & compaction pipeline:
        1. Archives obsolete chunks and purges them from Qdrant.
        2. Archives old superseded chunks beyond MAX_VERSION_HISTORY history cap.
        3. Archives true duplicate active chunks exceeding similarity threshold.

        Returns:
            Dict[str, Any]: Summary stats of GC execution.
        """
        logger.info("=== Starting EvoRAG Garbage Collection & Compaction ===")
        obsolete_archived = 0
        old_versions_archived = 0
        duplicates_removed = 0

        # PASS 1 — Archive and delete obsolete chunks
        try:
            logger.info("[GC Pass 1] Searching for obsolete chunks...")
            all_chunks = self.qdrant.list_all_chunks()
            obsolete_chunks = [c for c in all_chunks if str(c.metadata.status).lower() in ("obsolete", "chunkstatus.obsolete")]

            for item in obsolete_chunks:
                chunk_id = item.metadata.chunk_id
                self.archive.archive_chunk(item.metadata)
                self.qdrant.delete_chunk(chunk_id)
                obsolete_archived += 1
                logger.info(f"[GC Pass 1] Archived & deleted obsolete chunk '{chunk_id}'.")
        except Exception as e:
            logger.error(f"[GC Pass 1] Error during obsolete chunk archiving: {e}")

        # PASS 2 — Archive old superseded chunks beyond MAX_VERSION_HISTORY cap
        try:
            logger.info(f"[GC Pass 2] Enforcing version history cap (MAX_VERSION_HISTORY={MAX_VERSION_HISTORY})...")
            all_chunks = self.qdrant.list_all_chunks()
            superseded_chunks = [c for c in all_chunks if str(c.metadata.status).lower() in ("superseded", "chunkstatus.superseded")]

            processed_ids: Set[str] = set()

            for item in superseded_chunks:
                chunk_id = item.metadata.chunk_id
                if chunk_id in processed_ids:
                    continue

                # Build version lineage chain for this chunk
                chain = self.qdrant.get_version_chain(chunk_id)
                for cid in chain:
                    processed_ids.add(cid)

                # Filter chain items to only superseded chunks
                chain_superseded = []
                for cid in chain:
                    node = self.qdrant.get_by_id(cid)
                    if node and str(node.metadata.status).lower() in ("superseded", "chunkstatus.superseded"):
                        chain_superseded.append(node.metadata)

                # Sort by version ascending
                chain_superseded.sort(key=lambda m: m.version)

                # If superseded versions count > MAX_VERSION_HISTORY, prune oldest ones
                if len(chain_superseded) > MAX_VERSION_HISTORY:
                    excess_count = len(chain_superseded) - MAX_VERSION_HISTORY
                    to_prune = chain_superseded[:excess_count]

                    for old_meta in to_prune:
                        self.archive.archive_chunk(old_meta)
                        self.qdrant.delete_chunk(old_meta.chunk_id)
                        old_versions_archived += 1
                        logger.info(f"[GC Pass 2] Archived & deleted old superseded version (v{old_meta.version}) chunk '{old_meta.chunk_id}'.")

        except Exception as e:
            logger.error(f"[GC Pass 2] Error during superseded version pruning: {e}")

        # PASS 3 — Remove true active duplicate chunks
        try:
            logger.info(f"[GC Pass 3] Detecting duplicate active chunks (similarity threshold >= {DUPLICATE_SIMILARITY_THRESHOLD})...")
            active_chunks = self.qdrant.list_all_chunks(status_filter="active")

            if len(active_chunks) > 1:
                # Precompute embeddings
                embeddings_list = []
                for c in active_chunks:
                    emb = embed_text(c.metadata.content)
                    norm = np.linalg.norm(emb)
                    norm_emb = (np.array(emb) / norm) if norm > 0 else np.array(emb)
                    embeddings_list.append(norm_emb)

                deleted_active_ids: Set[str] = set()

                for i in range(len(active_chunks)):
                    chunk_a = active_chunks[i].metadata
                    if chunk_a.chunk_id in deleted_active_ids:
                        continue

                    for j in range(i + 1, len(active_chunks)):
                        chunk_b = active_chunks[j].metadata
                        if chunk_b.chunk_id in deleted_active_ids:
                            continue

                        # Skip if already explicitly linked via supersedes or conflicts_with
                        if (chunk_a.supersedes == chunk_b.chunk_id or chunk_b.supersedes == chunk_a.chunk_id or
                            (chunk_a.conflicts_with and chunk_b.chunk_id in chunk_a.conflicts_with) or
                            (chunk_b.conflicts_with and chunk_a.chunk_id in chunk_b.conflicts_with)):
                            continue

                        # Cosine similarity calculation
                        sim = float(np.dot(embeddings_list[i], embeddings_list[j]))
                        if sim >= DUPLICATE_SIMILARITY_THRESHOLD:
                            # Retain newer chunk by updated_at date
                            dt_a = parse_dt(chunk_a.updated_at)
                            dt_b = parse_dt(chunk_b.updated_at)

                            if dt_a >= dt_b:
                                older_chunk = chunk_b
                                newer_chunk = chunk_a
                                deleted_active_ids.add(chunk_b.chunk_id)
                            else:
                                older_chunk = chunk_a
                                newer_chunk = chunk_b
                                deleted_active_ids.add(chunk_a.chunk_id)

                            self.archive.archive_chunk(older_chunk)
                            self.qdrant.delete_chunk(older_chunk.chunk_id)
                            duplicates_removed += 1
                            logger.info(
                                f"[GC Pass 3] Archived duplicate active chunk '{older_chunk.chunk_id}' "
                                f"(similarity {sim:.4f} with '{newer_chunk.chunk_id}')."
                            )

        except Exception as e:
            logger.error(f"[GC Pass 3] Error during duplicate active chunk removal: {e}")

        # Compute remaining active chunks count
        remaining_active = len(self.qdrant.list_all_chunks(status_filter="active"))

        summary = {
            "obsolete_archived": obsolete_archived,
            "old_versions_archived": old_versions_archived,
            "duplicates_removed": duplicates_removed,
            "total_active_remaining": remaining_active
        }
        logger.info(f"=== EvoRAG Garbage Collection Complete: {summary} ===")
        return summary


def run_garbage_collection() -> Dict[str, Any]:
    """Standalone wrapper function for running garbage collection."""
    gc = GCService()
    return gc.run_garbage_collection()


if __name__ == "__main__":
    print("=== EvoRAG Garbage Collection & Compaction Manual Verification ===")

    gc_service = GCService()
    qservice = qdrant_service

    # Connect to Qdrant and seed test points
    qservice.connect()

    # 1. Seed obsolete chunk
    obsolete_chunk = ChunkMetadata(
        content="Obsolete facts about legacy EvoRAG 0.1 static index.",
        source="seed/legacy.md",
        status=ChunkStatus.OBSOLETE,
        version=1
    )
    qservice.upsert_chunk(obsolete_chunk, embed_text(obsolete_chunk.content))

    # 2. Seed version chain beyond MAX_VERSION_HISTORY (v1, v2, v3 superseded + v4 active)
    v1_chunk = ChunkMetadata(content="Fact v1", source="seed/v1.md", status=ChunkStatus.SUPERSEDED, version=1)
    v2_chunk = ChunkMetadata(content="Fact v2", source="seed/v2.md", status=ChunkStatus.SUPERSEDED, version=2, supersedes=v1_chunk.chunk_id)
    v3_chunk = ChunkMetadata(content="Fact v3", source="seed/v3.md", status=ChunkStatus.SUPERSEDED, version=3, supersedes=v2_chunk.chunk_id)
    v4_chunk = ChunkMetadata(content="Fact v4", source="seed/v4.md", status=ChunkStatus.ACTIVE, version=4, supersedes=v3_chunk.chunk_id)

    for c in [v1_chunk, v2_chunk, v3_chunk, v4_chunk]:
        qservice.upsert_chunk(c, embed_text(c.content))

    # 3. Seed duplicate active chunks
    dup1 = ChunkMetadata(content="Identical active factual statement for duplicate test.", source="seed/dup1.md", status=ChunkStatus.ACTIVE, version=1)
    dup2 = ChunkMetadata(content="Identical active factual statement for duplicate test.", source="seed/dup2.md", status=ChunkStatus.ACTIVE, version=1)

    qservice.upsert_chunk(dup1, embed_text(dup1.content))
    qservice.upsert_chunk(dup2, embed_text(dup2.content))

    before_total = len(qservice.list_all_chunks())
    before_active = len(qservice.list_all_chunks(status_filter="active"))

    print(f"\n[Test Seed] Total Qdrant points BEFORE GC:  {before_total}")
    print(f"[Test Seed] Active Qdrant points BEFORE GC: {before_active}")

    # Execute Garbage Collection
    summary_result = gc_service.run_garbage_collection()

    after_total = len(qservice.list_all_chunks())
    after_active = len(qservice.list_all_chunks(status_filter="active"))

    print(f"\n[GC Summary] Result: {summary_result}")
    print(f"[GC Summary] Total Qdrant points AFTER GC:  {after_total}")
    print(f"[GC Summary] Active Qdrant points AFTER GC: {after_active}")
