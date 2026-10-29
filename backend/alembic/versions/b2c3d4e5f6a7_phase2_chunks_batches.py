"""phase2 chunks and ingestion_batches

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-10-29

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f6a7"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chunks",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("owner_id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("vector_id", sa.String(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("text_sha256", sa.String(), nullable=False),
        sa.Column("token_estimate", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "locator",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("chunker_version", sa.String(), nullable=True),
        sa.Column("embedding_model_id", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("vector_id", name="uq_chunks_vector_id"),
    )
    op.create_index("ix_chunks_owner_id", "chunks", ["owner_id"])
    op.create_index("ix_chunks_document_id", "chunks", ["document_id"])
    op.create_index("ix_chunks_vector_id", "chunks", ["vector_id"])
    op.create_index("ix_chunks_document_generation", "chunks", ["document_id", "generation"])

    op.create_table(
        "ingestion_batches",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("batch_number", sa.Integer(), nullable=False),
        sa.Column("manifest_key", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("retries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "result",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["ingestion_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "batch_number", name="uq_ingestion_batches_job_batch"),
    )
    op.create_index("ix_ingestion_batches_job_id", "ingestion_batches", ["job_id"])
    op.create_index("ix_ingestion_batches_document_id", "ingestion_batches", ["document_id"])
    op.create_index("ix_ingestion_batches_status", "ingestion_batches", ["status"])


def downgrade() -> None:
    op.drop_index("ix_ingestion_batches_status", table_name="ingestion_batches")
    op.drop_index("ix_ingestion_batches_document_id", table_name="ingestion_batches")
    op.drop_index("ix_ingestion_batches_job_id", table_name="ingestion_batches")
    op.drop_table("ingestion_batches")
    op.drop_index("ix_chunks_document_generation", table_name="chunks")
    op.drop_index("ix_chunks_vector_id", table_name="chunks")
    op.drop_index("ix_chunks_document_id", table_name="chunks")
    op.drop_index("ix_chunks_owner_id", table_name="chunks")
    op.drop_table("chunks")
