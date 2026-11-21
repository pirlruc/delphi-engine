"""Postgres 16 catalog behind the Catalog protocol (SYS-002)."""

# psycopg's generic Connection is inferred as a typing special form, so
# execute and close look missing. The calls are real.
# pylint: disable=no-member

from __future__ import annotations

from datetime import date
from uuid import UUID

from delphi_contracts.batch import BatchCheckRequest, BatchCheckResponse, BatchCheckRow
from delphi_contracts.enums import EdgeKind, NeighborhoodMode
from delphi_contracts.extraction import Extraction
from delphi_contracts.graph import Edge
from delphi_contracts.identity import Identity
from delphi_contracts.json_tree import as_floats
from delphi_contracts.neighborhood import Neighborhood
from delphi_contracts.work import Work
from psycopg import Connection, connect
from psycopg.types.json import Jsonb

from delphi.catalog import Catalog, MemoryCatalog, scored_neighbors

__all__ = ["PostgresCatalog", "catalog_from_url"]

_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS works (
        id UUID PRIMARY KEY,
        payload JSONB NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS identities (
        kind TEXT NOT NULL,
        value TEXT NOT NULL,
        work_id UUID NOT NULL REFERENCES works (id) ON DELETE CASCADE,
        PRIMARY KEY (kind, value)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS edges (
        from_work UUID NOT NULL,
        to_work UUID NOT NULL,
        kind TEXT NOT NULL,
        score DOUBLE PRECISION,
        PRIMARY KEY (from_work, to_work, kind)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS embeddings (
        work_id UUID PRIMARY KEY REFERENCES works (id) ON DELETE CASCADE,
        model_id TEXT NOT NULL,
        vector DOUBLE PRECISION[] NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS extractions (
        id UUID PRIMARY KEY,
        content_hash TEXT UNIQUE NOT NULL,
        payload JSONB NOT NULL
    )
    """,
)

_DROP = (
    "DROP TABLE IF EXISTS embeddings CASCADE",
    "DROP TABLE IF EXISTS edges CASCADE",
    "DROP TABLE IF EXISTS identities CASCADE",
    "DROP TABLE IF EXISTS extractions CASCADE",
    "DROP TABLE IF EXISTS works CASCADE",
)


def catalog_from_url(url: str | None) -> Catalog:
    """Return a Postgres catalog when a DSN is set.

    Args:
        url: libpq DSN, or None for the in-memory catalog.

    Returns:
        Catalog implementation.
    """
    if url:
        return PostgresCatalog(url)
    return MemoryCatalog()


class PostgresCatalog:
    """Catalog stored in one Postgres database.

    The tables are works, cites, similar_to, and embeddings.
    """

    def __init__(self, conninfo: str, *, reset: bool = False) -> None:
        """Connect and apply the prototype schema.

        Args:
            conninfo: libpq DSN.
            reset: When true, drop and recreate tables (tests).
        """
        self._conn: Connection[tuple[object, ...]] = connect(conninfo, autocommit=True)
        if reset:
            for statement in _DROP:
                self._conn.execute(statement)
        for statement in _SCHEMA:
            self._conn.execute(statement)

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    def upsert_work(self, work: Work) -> Work:
        """Insert or replace a work and its identities.

        Args:
            work: Record to store.

        Returns:
            The stored work.
        """
        for identity in work.identities:
            owner = self._conn.execute(
                "SELECT work_id FROM identities WHERE kind = %s AND value = %s",
                (identity.kind.value, identity.value),
            ).fetchone()
            if owner is not None and owner[0] != work.id:
                raise ValueError(
                    "identity "
                    f"{identity.kind.value}:{identity.value} belongs to another work"
                )
        payload = Jsonb(work.model_dump(mode="json"))
        self._conn.execute(
            """
            INSERT INTO works (id, payload) VALUES (%s, %s)
            ON CONFLICT (id) DO UPDATE SET payload = EXCLUDED.payload
            """,
            (work.id, payload),
        )
        self._conn.execute("DELETE FROM identities WHERE work_id = %s", (work.id,))
        for identity in work.identities:
            self._conn.execute(
                """
            INSERT INTO identities (kind, value, work_id) VALUES (%s, %s, %s)
            ON CONFLICT (kind, value) DO UPDATE SET work_id = EXCLUDED.work_id
                """,
                (identity.kind.value, identity.value, work.id),
            )
        return work

    def get_work(self, work_id: UUID) -> Work | None:
        """Return a work by id.

        Args:
            work_id: Catalog UUID.

        Returns:
            The work, or None.
        """
        row = self._conn.execute(
            "SELECT payload FROM works WHERE id = %s", (work_id,)
        ).fetchone()
        if row is None:
            return None
        return Work.model_validate(row[0])

    def batch_check(self, request: BatchCheckRequest) -> BatchCheckResponse:
        """Exact-identifier existence check.

        Args:
            request: Identities in caller order.

        Returns:
            Known/unknown rows in the same order.
        """
        kinds = [identity.kind.value for identity in request.identities]
        values = [identity.value for identity in request.identities]
        found_rows = self._conn.execute(
            """
            SELECT kind, value, work_id FROM identities
            WHERE (kind, value) IN (
                SELECT * FROM unnest(%s::text[], %s::text[])
            )
            """,
            (kinds, values),
        ).fetchall()
        found: dict[tuple[str, str], UUID] = {}
        for kind, value, work_id in found_rows:
            if work_id is None:
                continue
            found[(str(kind), str(value))] = UUID(str(work_id))
        rows = tuple(
            BatchCheckRow(
                identity=identity,
                known=(identity.kind.value, identity.value) in found,
                work_id=found.get((identity.kind.value, identity.value)),
            )
            for identity in request.identities
        )
        return BatchCheckResponse(rows=rows)

    def add_edge(self, edge: Edge) -> None:
        """Store a directed edge, ignoring duplicates and self-loops.

        Args:
            edge: cites or similar_to row.
        """
        if edge.from_work == edge.to_work:
            return
        self._conn.execute(
            """
            INSERT INTO edges (from_work, to_work, kind, score)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (from_work, to_work, kind) DO UPDATE SET score = EXCLUDED.score
            """,
            (edge.from_work, edge.to_work, edge.kind.value, edge.score),
        )

    def edges(self, kind: EdgeKind | None = None) -> tuple[Edge, ...]:
        """Return stored edges.

        Args:
            kind: Optional kind filter.

        Returns:
            Matching edges.
        """
        if kind is None:
            result = self._conn.execute(
                "SELECT from_work, to_work, kind, score FROM edges"
            )
        else:
            result = self._conn.execute(
                "SELECT from_work, to_work, kind, score FROM edges WHERE kind = %s",
                (kind.value,),
            )
        return tuple(_edge_from_row(row) for row in result.fetchall())

    def put_embedding(
        self, work_id: UUID, vector: tuple[float, ...], model_id: str
    ) -> None:
        """Store an embedding for a work.

        Args:
            work_id: Catalog UUID.
            vector: Dense vector.
            model_id: Embedding model id.
        """
        self._conn.execute(
            """
            INSERT INTO embeddings (work_id, model_id, vector)
            VALUES (%s, %s, %s)
            ON CONFLICT (work_id) DO UPDATE
            SET model_id = EXCLUDED.model_id, vector = EXCLUDED.vector
            """,
            (work_id, model_id, list(vector)),
        )

    def get_embedding(self, work_id: UUID) -> tuple[float, ...] | None:
        """Return a stored embedding.

        Args:
            work_id: Catalog UUID.

        Returns:
            Vector or None.
        """
        row = self._conn.execute(
            "SELECT vector FROM embeddings WHERE work_id = %s", (work_id,)
        ).fetchone()
        if row is None:
            return None
        return _vector(row[0])

    def list_works(self) -> tuple[Work, ...]:
        """Return every work.

        Returns:
            Catalog works.
        """
        result = self._conn.execute("SELECT payload FROM works")
        return tuple(Work.model_validate(row[0]) for row in result.fetchall())

    def put_extraction(self, extraction: Extraction) -> Extraction:
        """Store extraction output.

        Args:
            extraction: Structured PDF fields.

        Returns:
            The stored extraction.
        """
        payload = Jsonb(extraction.model_dump(mode="json"))
        self._conn.execute(
            """
            INSERT INTO extractions (id, content_hash, payload)
            VALUES (%s, %s, %s)
            ON CONFLICT (id) DO UPDATE
            SET content_hash = EXCLUDED.content_hash, payload = EXCLUDED.payload
            """,
            (extraction.id, extraction.content_hash, payload),
        )
        return extraction

    def get_extraction(self, extraction_id: UUID) -> Extraction | None:
        """Return an extraction by id.

        Args:
            extraction_id: Extraction UUID.

        Returns:
            Extraction or None.
        """
        row = self._conn.execute(
            "SELECT payload FROM extractions WHERE id = %s", (extraction_id,)
        ).fetchone()
        if row is None:
            return None
        return Extraction.model_validate(row[0])

    def get_extraction_by_hash(self, content_hash: str) -> Extraction | None:
        """Return an extraction by PDF content hash.

        Args:
            content_hash: SHA-256 hex of the PDF bytes.

        Returns:
            Extraction or None.
        """
        row = self._conn.execute(
            "SELECT payload FROM extractions WHERE content_hash = %s", (content_hash,)
        ).fetchone()
        if row is None:
            return None
        return Extraction.model_validate(row[0])

    def neighborhood(
        self,
        seed_id: UUID,
        mode: NeighborhoodMode,
        subcategory: str,
        as_of: date | None = None,
        excluded_ids: frozenset[UUID] | None = None,
        k: int = 8,
    ) -> Neighborhood:
        """Return dated neighbors tagged by edge kind.

        Args:
            seed_id: Center work.
            mode: citation, content, or union.
            subcategory: Required SYS-009 filter.
            as_of: Inclusive publication bound.
            excluded_ids: Extra ids to drop (hindcast).
            k: Max similar_to neighbors per direction.

        Returns:
            Neighborhood around the seed.
        """
        mirror = MemoryCatalog()
        if as_of is None:
            payloads = self._conn.execute("SELECT id, payload FROM works").fetchall()
        else:
            payloads = self._conn.execute(
                """
                SELECT id, payload FROM works
                WHERE (payload->>'published_on')::date <= %s OR id = %s
                """,
                (as_of, seed_id),
            ).fetchall()
        for _work_id, payload in payloads:
            mirror.upsert_work(Work.model_validate(payload))
        ids = list(mirror._works)
        if ids:
            edge_rows = self._conn.execute(
                """
                SELECT from_work, to_work, kind, score FROM edges
                WHERE from_work = ANY(%s) AND to_work = ANY(%s)
                """,
                (ids, ids),
            ).fetchall()
            for row in edge_rows:
                mirror.add_edge(_edge_from_row(row))
            vectors = self._conn.execute(
                "SELECT work_id, vector, model_id FROM embeddings "
                "WHERE work_id = ANY(%s)",
                (ids,),
            ).fetchall()
            for work_id, vector, model_id in vectors:
                mirror.put_embedding(UUID(str(work_id)), _vector(vector), str(model_id))
        return mirror.neighborhood(seed_id, mode, subcategory, as_of, excluded_ids, k)

    def rebuild_similar_to(self, work_id: UUID, k: int = 8) -> None:
        """Replace similar_to edges for a work from stored embeddings.

        Args:
            work_id: Work to refresh.
            k: Neighbor count.
        """
        embeddings, models = self._embedding_state()
        source = embeddings.get(work_id)
        if source is None:
            return
        self._conn.execute(
            """
            DELETE FROM edges
            WHERE kind = %s AND from_work = %s
            """,
            (EdgeKind.SIMILAR_TO.value, work_id),
        )
        ranked = scored_neighbors(
            work_id, source, embeddings, models, models.get(work_id)
        )
        for other_id, score in ranked[:k]:
            self.add_edge(
                Edge(
                    from_work=work_id,
                    to_work=other_id,
                    kind=EdgeKind.SIMILAR_TO,
                    score=score,
                )
            )
            self.add_edge(
                Edge(
                    from_work=other_id,
                    to_work=work_id,
                    kind=EdgeKind.SIMILAR_TO,
                    score=score,
                )
            )

    def rebuild_all_similar_to(self, k: int = 8) -> None:
        """Recompute every similar_to edge from current embeddings.

        Args:
            k: Neighbor count per work.
        """
        self._conn.execute(
            "DELETE FROM edges WHERE kind = %s", (EdgeKind.SIMILAR_TO.value,)
        )
        embeddings, models = self._embedding_state()
        for work_id, source in embeddings.items():
            ranked = scored_neighbors(
                work_id, source, embeddings, models, models.get(work_id)
            )
            for other_id, score in ranked[:k]:
                self.add_edge(
                    Edge(
                        from_work=work_id,
                        to_work=other_id,
                        kind=EdgeKind.SIMILAR_TO,
                        score=score,
                    )
                )
                self.add_edge(
                    Edge(
                        from_work=other_id,
                        to_work=work_id,
                        kind=EdgeKind.SIMILAR_TO,
                        score=score,
                    )
                )

    def _check_identity(self, identity: Identity) -> BatchCheckRow:
        """Look up one identity.

        Args:
            identity: Query identity.

        Returns:
            Known or unknown row.
        """
        row = self._conn.execute(
            "SELECT work_id FROM identities WHERE kind = %s AND value = %s",
            (identity.kind.value, identity.value),
        ).fetchone()
        work_id = UUID(str(row[0])) if row is not None and row[0] is not None else None
        return BatchCheckRow(
            identity=identity, known=work_id is not None, work_id=work_id
        )

    def _embedding_state(
        self,
    ) -> tuple[dict[UUID, tuple[float, ...]], dict[UUID, str]]:
        """Load every stored embedding and its model id.

        Returns:
            Vectors and model ids keyed by work id.
        """
        result = self._conn.execute("SELECT work_id, vector, model_id FROM embeddings")
        vectors: dict[UUID, tuple[float, ...]] = {}
        models: dict[UUID, str] = {}
        for row in result.fetchall():
            key = UUID(str(row[0]))
            vectors[key] = _vector(row[1])
            models[key] = str(row[2])
        return vectors, models


def _edge_from_row(row: tuple[object, ...]) -> Edge:
    """Build an Edge from a SQL row.

    Args:
        row: from_work, to_work, kind, score.

    Returns:
        Edge model.
    """
    return Edge(
        from_work=UUID(str(row[0])),
        to_work=UUID(str(row[1])),
        kind=EdgeKind(str(row[2])),
        score=None if row[3] is None else float(str(row[3])),
    )


def _vector(raw: object) -> tuple[float, ...]:
    """Coerce a Postgres array into floats.

    Args:
        raw: Driver array value.

    Returns:
        Float tuple.
    """
    return as_floats(raw)
