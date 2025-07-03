from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, JSON, Enum, func
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()

class CustodyType(str, enum.Enum):
    DEVELOPER = "DEVELOPER"
    USER = "USER"

class WalletSet(Base):
    __tablename__ = "wallet_sets"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    custody_type = Column(Enum(CustodyType), nullable=False)
    create_date = Column(DateTime, server_default=func.now())
    update_date = Column(DateTime, server_default=func.now(), onupdate=func.now())
    wallets = relationship("Wallet", back_populates="wallet_set")

class Wallet(Base):
    __tablename__ = "wallets"
    id = Column(String, primary_key=True, index=True)
    address = Column(String, nullable=False, index=True)
    blockchain = Column(String, nullable=False)
    account_type = Column(String, nullable=False)
    state = Column(String, nullable=False)
    custody_type = Column(Enum(CustodyType), nullable=False)
    wallet_set_id = Column(String, ForeignKey("wallet_sets.id"))
    create_date = Column(DateTime, server_default=func.now())
    update_date = Column(DateTime, server_default=func.now(), onupdate=func.now())
    wallet_set = relationship("WalletSet", back_populates="wallets")

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(String, primary_key=True, index=True)
    wallet_id = Column(String, ForeignKey("wallets.id"))
    token_id = Column(String, nullable=False)
    destination_address = Column(String, nullable=False)
    amount = Column(String, nullable=False)
    status = Column(String, nullable=False)
    tx_hash = Column(String, nullable=True)
    create_date = Column(DateTime, server_default=func.now())
    update_date = Column(DateTime, server_default=func.now(), onupdate=func.now())
    wallet = relationship("Wallet")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False)
    event_data = Column(JSON, nullable=False)
    create_date = Column(DateTime, server_default=func.now())
