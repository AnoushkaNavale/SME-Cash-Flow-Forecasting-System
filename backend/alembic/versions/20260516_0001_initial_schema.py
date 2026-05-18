"""initial schema

Revision ID: 20260516_0001
Revises:
Create Date: 2026-05-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260516_0001"
down_revision = None
branch_labels = None
depends_on = None

transaction_category = postgresql.ENUM(
    "invoice", "payment_received", "payroll", "vendor", "tax",
    "rent", "loan_emi", "misc_income", "misc_expense",
    name="transactioncategory",
)
transaction_source = postgresql.ENUM(
    "razorpay", "bank_csv", "gst", "tally", "manual",
    name="transactionsource",
)
alert_severity = postgresql.ENUM("low", "medium", "high", name="alertseverity")


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    transaction_category.create(op.get_bind(), checkfirst=True)
    transaction_source.create(op.get_bind(), checkfirst=True)
    alert_severity.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "businesses",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("gstin", sa.String(15), nullable=True, unique=True),
        sa.Column("email", sa.String(200), nullable=False, unique=True),
        sa.Column("phone", sa.String(15), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("category", transaction_category, nullable=False),
        sa.Column("source", transaction_source, nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("is_confirmed", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("due_date", sa.Date),
        sa.Column("invoice_number", sa.String(50)),
        sa.Column("counterparty", sa.String(200)),
        sa.Column("external_id", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_transactions_business_date", "transactions", ["business_id", "date"])
    op.create_index("idx_transactions_business_category", "transactions", ["business_id", "category"])
    op.create_index("idx_transactions_external_id", "transactions", ["external_id"], unique=True, postgresql_where=sa.text("external_id IS NOT NULL"))

    op.create_table(
        "forecast_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("horizon_days", sa.Numeric(3, 0), server_default="90"),
        sa.Column("forecast_data", sa.Text, nullable=False),
        sa.Column("current_balance", sa.Numeric(14, 2), nullable=False),
        sa.Column("minimum_safe_balance", sa.Numeric(14, 2), server_default="50000"),
    )
    op.create_index("idx_forecast_business", "forecast_snapshots", ["business_id", "generated_at"])

    op.create_table(
        "cashflow_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alert_date", sa.Date, nullable=False),
        sa.Column("severity", alert_severity, nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("projected_balance", sa.Numeric(14, 2), nullable=False),
        sa.Column("is_resolved", sa.Boolean, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("cashflow_alerts")
    op.drop_table("forecast_snapshots")
    op.drop_table("transactions")
    op.drop_table("businesses")
    alert_severity.drop(op.get_bind(), checkfirst=True)
    transaction_source.drop(op.get_bind(), checkfirst=True)
    transaction_category.drop(op.get_bind(), checkfirst=True)
