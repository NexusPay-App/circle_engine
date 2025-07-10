from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Index, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSON
from datetime import datetime

Base = declarative_base()

class WalletSet(Base):
    __tablename__ = "wallet_sets"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    custody_type = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Wallet(Base):
    __tablename__ = "wallets"
    
    id = Column(String, primary_key=True)
    address = Column(String, nullable=False)
    blockchain = Column(String, nullable=False)
    account_type = Column(String, nullable=False)  # SCA or EOA
    state = Column(String, nullable=False)
    custody_type = Column(String, nullable=False)
    wallet_set_id = Column(String, ForeignKey("wallet_sets.id"))
    role = Column(String, nullable=True)  # backendMirror, circleEngine, solanaOperations
    wallet_type = Column(String, nullable=True)  # EVM, SOLANA
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_wallet_address', 'address'),
        Index('idx_wallet_blockchain', 'blockchain'),
        Index('idx_wallet_role', 'role'),
        Index('idx_wallet_type', 'wallet_type'),
    )

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(String, primary_key=True)
    wallet_id = Column(String, ForeignKey("wallets.id"))
    token_id = Column(String, nullable=False)
    destination_address = Column(String, nullable=False)
    amount = Column(String, nullable=False)
    status = Column(String, nullable=False)
    blockchain = Column(String, nullable=True)  # Add blockchain tracking
    tx_hash = Column(String)
    confirmations = Column(Integer, default=0)
    confirmation_required = Column(Integer, default=12)
    gas_fee = Column(String, nullable=True)  # Gas fee in wei/sol
    gas_station_used = Column(String, nullable=True)  # true, false
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_transaction_wallet_id', 'wallet_id'),
        Index('idx_transaction_status', 'status'),
        Index('idx_transaction_blockchain', 'blockchain'),
        Index('idx_transaction_created_at', 'created_at'),
    )

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String, nullable=False)
    event_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_audit_event_type', 'event_type'),
        Index('idx_audit_created_at', 'created_at'),
    )

class Balance(Base):
    __tablename__ = "balances"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    wallet_id = Column(String, ForeignKey("wallets.id"))
    token_id = Column(String, nullable=False)
    blockchain = Column(String, nullable=False)
    balance_amount = Column(String, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_balance_wallet_id', 'wallet_id'),
        Index('idx_balance_token_id', 'token_id'),
        Index('idx_balance_blockchain', 'blockchain'),
        Index('idx_balance_last_updated', 'last_updated'),
    )
