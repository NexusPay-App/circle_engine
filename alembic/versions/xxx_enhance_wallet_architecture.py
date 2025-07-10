"""Enhance wallet architecture with three-wallet support

Revision ID: xxx
Revises: afb5bee6e70e
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'xxx'
down_revision = 'afb5bee6e70e'
branch_labels = None
depends_on = None

def upgrade():
    # Add new columns to existing tables
    op.add_column('wallets', sa.Column('role', sa.String(), nullable=True))
    op.add_column('wallets', sa.Column('wallet_type', sa.String(), nullable=True))
    
    # Add new columns to transactions table
    op.add_column('transactions', sa.Column('blockchain', sa.String(), nullable=True))
    op.add_column('transactions', sa.Column('confirmations', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('transactions', sa.Column('confirmation_required', sa.Integer(), nullable=True, server_default='12'))
    op.add_column('transactions', sa.Column('updated_at', sa.DateTime(), nullable=True))
    
    # Create webhook_events table
    op.create_table('webhook_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('subscription_id', sa.String(), nullable=False),
        sa.Column('notification_id', sa.String(), nullable=False),
        sa.Column('notification_type', sa.String(), nullable=False),
        sa.Column('notification_data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_notification_id', 'webhook_events', ['notification_id'], unique=True)
    op.create_index('idx_notification_type', 'webhook_events', ['notification_type'], unique=False)
    op.create_index('idx_timestamp', 'webhook_events', ['timestamp'], unique=False)
    
    # Create webhook_attempts table
    op.create_table('webhook_attempts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('notification_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('payload', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('attempt_number', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_notification_id_status', 'webhook_attempts', ['notification_id', 'status'], unique=False)
    op.create_index('idx_created_at', 'webhook_attempts', ['created_at'], unique=False)
    
    # Create indexes for enhanced querying
    op.create_index('idx_wallet_address', 'wallets', ['address'], unique=False)
    op.create_index('idx_wallet_blockchain', 'wallets', ['blockchain'], unique=False)
    op.create_index('idx_wallet_role', 'wallets', ['role'], unique=False)
    op.create_index('idx_wallet_type', 'wallets', ['wallet_type'], unique=False)
    
    op.create_index('idx_transaction_wallet_id', 'transactions', ['wallet_id'], unique=False)
    op.create_index('idx_transaction_status', 'transactions', ['status'], unique=False)
    op.create_index('idx_transaction_blockchain', 'transactions', ['blockchain'], unique=False)
    op.create_index('idx_transaction_created_at', 'transactions', ['created_at'], unique=False)
    
    op.create_index('idx_audit_event_type', 'audit_logs', ['event_type'], unique=False)
    op.create_index('idx_audit_created_at', 'audit_logs', ['created_at'], unique=False)

def downgrade():
    # Drop indexes
    op.drop_index('idx_audit_created_at', table_name='audit_logs')
    op.drop_index('idx_audit_event_type', table_name='audit_logs')
    
    op.drop_index('idx_transaction_created_at', table_name='transactions')
    op.drop_index('idx_transaction_blockchain', table_name='transactions')
    op.drop_index('idx_transaction_status', table_name='transactions')
    op.drop_index('idx_transaction_wallet_id', table_name='transactions')
    
    op.drop_index('idx_wallet_type', table_name='wallets')
    op.drop_index('idx_wallet_role', table_name='wallets')
    op.drop_index('idx_wallet_blockchain', table_name='wallets')
    op.drop_index('idx_wallet_address', table_name='wallets')
    
    # Drop webhook tables
    op.drop_index('idx_created_at', table_name='webhook_attempts')
    op.drop_index('idx_notification_id_status', table_name='webhook_attempts')
    op.drop_table('webhook_attempts')
    
    op.drop_index('idx_timestamp', table_name='webhook_events')
    op.drop_index('idx_notification_type', table_name='webhook_events')
    op.drop_index('idx_notification_id', table_name='webhook_events')
    op.drop_table('webhook_events')
    
    # Drop columns from transactions table
    op.drop_column('transactions', 'updated_at')
    op.drop_column('transactions', 'confirmation_required')
    op.drop_column('transactions', 'confirmations')
    op.drop_column('transactions', 'blockchain')
    
    # Drop columns from wallets table
    op.drop_column('wallets', 'wallet_type')
    op.drop_column('wallets', 'role') 