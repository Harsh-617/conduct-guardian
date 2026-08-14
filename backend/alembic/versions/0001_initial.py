"""initial schema

Creates all six tables from app/models.py in FK-safe order: parents before
children (agencies/collectors/accounts before messages; messages before
screening_results and hardship_signals; screening_results before
evidence_ledger), and every table before the indexes that reference it.

Enums (Channel, HardshipType) are declared with native_enum=False in the
ORM, so they land here as plain sa.String columns sized to the longest
member, not a Postgres ENUM type — that's what keeps this schema portable to
the SQLite test database.

Revision ID: 0001
Revises:
Create Date: 2026-08-13

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Parent tables (no FK dependencies) --------------------------------

    op.create_table(
        "agencies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("name", name="uq_agencies_name"),
    )

    op.create_table(
        "collectors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("role", sa.String(length=60), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_id", sa.String(length=60), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_accounts_external_id", "accounts", ["external_id"], unique=True
    )

    # --- messages (FKs to all three parents above) --------------------------

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "account_id",
            sa.Integer(),
            sa.ForeignKey("accounts.id"),
            nullable=False,
        ),
        sa.Column(
            "collector_id",
            sa.Integer(),
            sa.ForeignKey("collectors.id"),
            nullable=False,
        ),
        sa.Column(
            "agency_id",
            sa.Integer(),
            sa.ForeignKey("agencies.id"),
            nullable=False,
        ),
        # Channel enum (native_enum=False) -> plain VARCHAR(16).
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column(
            "is_customer", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_messages_account_id", "messages", ["account_id"])
    op.create_index("ix_messages_collector_id", "messages", ["collector_id"])
    op.create_index("ix_messages_agency_id", "messages", ["agency_id"])
    op.create_index("ix_messages_occurred_at", "messages", ["occurred_at"])
    # Powers the R5 contacts-per-week check and the timeline burst heuristic.
    op.create_index(
        "ix_messages_account_occurred",
        "messages",
        ["account_id", "occurred_at"],
    )

    # --- screening_results (FK to messages) ---------------------------------

    op.create_table(
        "screening_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "message_id", sa.Integer(), sa.ForeignKey("messages.id"), nullable=False
        ),
        sa.Column("violation", sa.Boolean(), nullable=False),
        sa.Column("rule", sa.String(length=60), nullable=True),
        sa.Column("quoted_phrase", sa.Text(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("suggested_rewrite", sa.Text(), nullable=True),
        sa.Column(
            "model", sa.String(length=60), nullable=False, server_default=""
        ),
        sa.Column(
            "latency_ms", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_screening_results_message_id",
        "screening_results",
        ["message_id"],
        unique=True,
    )
    op.create_index(
        "ix_screening_results_violation", "screening_results", ["violation"]
    )
    op.create_index("ix_screening_results_rule", "screening_results", ["rule"])

    # --- evidence_ledger (FK to screening_results) ---------------------------

    op.create_table(
        "evidence_ledger",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "screening_result_id",
            sa.Integer(),
            sa.ForeignKey("screening_results.id"),
            nullable=False,
        ),
        sa.Column("entry_hash", sa.String(length=64), nullable=False),
        sa.Column("prev_hash", sa.String(length=64), nullable=True),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_evidence_ledger_screening_result_id",
        "evidence_ledger",
        ["screening_result_id"],
        unique=True,
    )
    op.create_index(
        "ix_evidence_ledger_entry_hash", "evidence_ledger", ["entry_hash"]
    )

    # --- hardship_signals (FK to messages) -----------------------------------

    op.create_table(
        "hardship_signals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "message_id", sa.Integer(), sa.ForeignKey("messages.id"), nullable=False
        ),
        # HardshipType enum (native_enum=False) -> plain VARCHAR(24).
        sa.Column("signal_type", sa.String(length=24), nullable=False),
        sa.Column("quoted_text", sa.Text(), nullable=False),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_hardship_signals_message_id", "hardship_signals", ["message_id"]
    )
    op.create_index(
        "ix_hardship_signals_signal_type", "hardship_signals", ["signal_type"]
    )


def downgrade() -> None:
    # Reverse order: children before parents.
    op.drop_table("hardship_signals")
    op.drop_table("evidence_ledger")
    op.drop_table("screening_results")
    op.drop_table("messages")
    op.drop_table("accounts")
    op.drop_table("collectors")
    op.drop_table("agencies")
