from app.db.session import SessionLocal
from app.models.wallet import Transaction
from app.utils.audit import log_audit
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def save_transaction(tx_id, wallet_id, token_id, destination_address, amount, status, tx_hash=None, blockchain=None, gas_fee=None, gas_station_used=None):
    """Save transaction to database with enhanced tracking"""
    db = SessionLocal()
    try:
        # Get confirmation requirements based on blockchain
        confirmation_required = get_confirmation_requirements(blockchain)
        
        t = Transaction(
            id=tx_id, 
            wallet_id=wallet_id, 
            token_id=token_id, 
            destination_address=destination_address,
            amount=amount, 
            status=status, 
            tx_hash=tx_hash,
            blockchain=blockchain,
            confirmation_required=confirmation_required,
            gas_fee=gas_fee,
            gas_station_used=gas_station_used
        )
        db.add(t)
        db.commit()
        log_audit("transaction_initiated", {
            "tx_id": tx_id, 
            "wallet_id": wallet_id, 
            "amount": amount, 
            "status": status,
            "blockchain": blockchain,
            "gas_fee": gas_fee,
            "gas_station_used": gas_station_used
        })
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving transaction: {str(e)}")
        raise
    finally:
        db.close()

def get_confirmation_requirements(blockchain):
    """Get confirmation requirements based on blockchain"""
    confirmation_map = {
        "ETH": 12,
        "POLYGON": 50,
        "ARBITRUM": 12,
        "BASE": 12,
        "OPTIMISM": 12,
        "SOL": 33,
        "AVALANCHE": 1,
        "CELO": 12
    }
    return confirmation_map.get(blockchain, 12)

async def update_transaction_status(transaction_id: str, status: str, notification_data: dict):
    """Update transaction status based on webhook notification"""
    db = SessionLocal()
    try:
        transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if transaction:
            old_status = transaction.status
            transaction.status = status
            transaction.updated_at = datetime.utcnow()
            
            # Update additional fields based on notification
            if "txHash" in notification_data:
                transaction.tx_hash = notification_data["txHash"]
            if "confirmations" in notification_data:
                transaction.confirmations = notification_data["confirmations"]
            if "gasUsed" in notification_data:
                transaction.gas_fee = notification_data["gasUsed"]
            
            db.commit()
            log_audit("transaction_status_updated", {
                "transaction_id": transaction_id,
                "old_status": old_status,
                "new_status": status,
                "blockchain": transaction.blockchain
            })
        else:
            logger.warning(f"Transaction not found: {transaction_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating transaction status: {str(e)}")
        raise
    finally:
        db.close()

def get_transactions_by_blockchain(blockchain: str, limit: int = 100):
    """Get transactions by blockchain"""
    db = SessionLocal()
    try:
        transactions = db.query(Transaction).filter(
            Transaction.blockchain == blockchain
        ).order_by(Transaction.created_at.desc()).limit(limit).all()
        return transactions
    except Exception as e:
        logger.error(f"Error getting transactions by blockchain: {str(e)}")
        return []
    finally:
        db.close()

def get_pending_transactions():
    """Get all pending transactions"""
    db = SessionLocal()
    try:
        transactions = db.query(Transaction).filter(
            Transaction.status.in_(["PENDING", "CONFIRMED"])
        ).order_by(Transaction.created_at.asc()).all()
        return transactions
    except Exception as e:
        logger.error(f"Error getting pending transactions: {str(e)}")
        return []
    finally:
        db.close()

def get_transaction_by_id(transaction_id: str):
    """Get transaction by ID"""
    db = SessionLocal()
    try:
        transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        return transaction
    except Exception as e:
        logger.error(f"Error getting transaction: {str(e)}")
        return None
    finally:
        db.close()

def get_transactions_by_wallet(wallet_id: str, limit: int = 50):
    """Get transactions by wallet ID"""
    db = SessionLocal()
    try:
        transactions = db.query(Transaction).filter(
            Transaction.wallet_id == wallet_id
        ).order_by(Transaction.created_at.desc()).limit(limit).all()
        return transactions
    except Exception as e:
        logger.error(f"Error getting transactions by wallet: {str(e)}")
        return []
    finally:
        db.close()

def get_transactions_by_status(status: str, limit: int = 100):
    """Get transactions by status"""
    db = SessionLocal()
    try:
        transactions = db.query(Transaction).filter(
            Transaction.status == status
        ).order_by(Transaction.created_at.desc()).limit(limit).all()
        return transactions
    except Exception as e:
        logger.error(f"Error getting transactions by status: {str(e)}")
        return []
    finally:
        db.close()

def update_transaction_gas_info(transaction_id: str, gas_fee: str, gas_station_used: str):
    """Update transaction gas information"""
    db = SessionLocal()
    try:
        transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if transaction:
            transaction.gas_fee = gas_fee
            transaction.gas_station_used = gas_station_used
            transaction.updated_at = datetime.utcnow()
            db.commit()
            
            log_audit("transaction_gas_updated", {
                "transaction_id": transaction_id,
                "gas_fee": gas_fee,
                "gas_station_used": gas_station_used
            })
            return True
        return False
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating transaction gas info: {str(e)}")
        return False
    finally:
        db.close()

def get_transaction_statistics(blockchain: str = None, days: int = 30):
    """Get transaction statistics"""
    db = SessionLocal()
    try:
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = db.query(Transaction).filter(Transaction.created_at >= cutoff_date)
        
        if blockchain:
            query = query.filter(Transaction.blockchain == blockchain)
        
        transactions = query.all()
        
        stats = {
            "total_transactions": len(transactions),
            "pending": len([t for t in transactions if t.status == "PENDING"]),
            "confirmed": len([t for t in transactions if t.status == "CONFIRMED"]),
            "completed": len([t for t in transactions if t.status == "COMPLETED"]),
            "failed": len([t for t in transactions if t.status == "FAILED"]),
            "gas_station_usage": len([t for t in transactions if t.gas_station_used == "true"]),
            "blockchain_breakdown": {}
        }
        
        # Blockchain breakdown
        for tx in transactions:
            chain = tx.blockchain or "unknown"
            if chain not in stats["blockchain_breakdown"]:
                stats["blockchain_breakdown"][chain] = 0
            stats["blockchain_breakdown"][chain] += 1
        
        return stats
    except Exception as e:
        logger.error(f"Error getting transaction statistics: {str(e)}")
        return {}
    finally:
        db.close() 