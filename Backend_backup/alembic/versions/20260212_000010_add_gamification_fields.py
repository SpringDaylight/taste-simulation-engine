"""Add gamification fields and tables."""
from alembic import op
import sqlalchemy as sa


revision = "20260212_000010"
down_revision = "20260212_000009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("level", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("users", sa.Column("exp", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("popcorn", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("main_flavor", sa.String(), nullable=False, server_default="Sweet"))
    op.add_column("users", sa.Column("stage", sa.String(), nullable=False, server_default="Egg"))
    op.add_column("users", sa.Column("last_feeding_date", sa.String(), nullable=True))
    op.add_column("users", sa.Column("last_question_date", sa.String(), nullable=True))
    op.add_column("users", sa.Column("current_question_index", sa.Integer(), nullable=False, server_default="0"))

    op.create_table(
        "flavor_stats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("flavor_name", sa.String(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "flavor_name", name="_user_flavor_uc"),
    )

    op.create_table(
        "theme_inventory",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("theme_id", sa.String(), nullable=False),
        sa.Column("is_applied", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("acquired_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "question_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("date", sa.String(), nullable=False),
        sa.Column("question", sa.String(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("question_history")
    op.drop_table("theme_inventory")
    op.drop_table("flavor_stats")
    op.drop_column("users", "current_question_index")
    op.drop_column("users", "last_question_date")
    op.drop_column("users", "last_feeding_date")
    op.drop_column("users", "stage")
    op.drop_column("users", "main_flavor")
    op.drop_column("users", "popcorn")
    op.drop_column("users", "exp")
    op.drop_column("users", "level")
