"""初始化数据库基线表结构"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_initial_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "history_records",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("topic", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("outline_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("images_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("content_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("thumbnail", sa.String(length=512), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("task_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_history_records_status_created_at", "history_records", ["status", "created_at"])
    op.create_index("ix_history_records_task_id", "history_records", ["task_id"])

    op.create_table(
        "concept_records",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("article_preview", sa.Text(), nullable=False, server_default=""),
        sa.Column("article_full", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="in_progress"),
        sa.Column("task_id", sa.String(length=128), nullable=False),
        sa.Column("style", sa.String(length=64), nullable=True),
        sa.Column("thumbnail", sa.String(length=512), nullable=True),
        sa.Column("image_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pipeline_data_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_concept_records_status_created_at", "concept_records", ["status", "created_at"])
    op.create_index("ix_concept_records_task_id", "concept_records", ["task_id"])

    op.create_table(
        "publish_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("images_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("tags_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("message", sa.Text(), nullable=False, server_default=""),
        sa.Column("post_url", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_publish_records_status_created_at", "publish_records", ["status", "created_at"])

    op.create_table(
        "image_jobs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("task_id", sa.String(length=128), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("result_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("total_pages", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_pages", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_pages", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_image_jobs_status_created_at", "image_jobs", ["status", "created_at"])

    op.create_table(
        "image_job_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("job_id", sa.String(length=64), sa.ForeignKey("image_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_index", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("image_url", sa.String(length=1024), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("job_id", "page_index", name="uq_image_job_item_job_page"),
    )
    op.create_index("ix_image_job_items_job_id", "image_job_items", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_image_job_items_job_id", table_name="image_job_items")
    op.drop_table("image_job_items")

    op.drop_index("ix_image_jobs_status_created_at", table_name="image_jobs")
    op.drop_table("image_jobs")

    op.drop_index("ix_publish_records_status_created_at", table_name="publish_records")
    op.drop_table("publish_records")

    op.drop_index("ix_concept_records_task_id", table_name="concept_records")
    op.drop_index("ix_concept_records_status_created_at", table_name="concept_records")
    op.drop_table("concept_records")

    op.drop_index("ix_history_records_task_id", table_name="history_records")
    op.drop_index("ix_history_records_status_created_at", table_name="history_records")
    op.drop_table("history_records")
