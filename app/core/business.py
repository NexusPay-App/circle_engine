from app.db.session import SessionLocal
from app.models.wallet import WalletSet, Wallet, Transaction, WebhookEvent, WebhookAttempt
from app.utils.audit import log_audit
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def save_wallet_set(wallet_set_id, name, custody_type):
    db = SessionLocal()
    try:
        ws = WalletSet(id=wallet_set_id, name=name, custody_type=custody_type)
        db.add(ws)
        db.commit()
        log_audit("wallet_set_created", {"wallet_set_id": wallet_set_id, "name": name, "custody_type": custody_type})
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving wallet set: {str(e)}")
        raise
    finally:
        db.close()

def save_wallet(wallet_id, address, blockchain, account_type, state, custody_type, wallet_set_id, role=None, wallet_type=None):
    db = SessionLocal()
    try:
        w = Wallet(
            id=wallet_id, 
            address=address, 
            blockchain=blockchain, 
            account_type=account_type,
            state=state, 
            custody_type=custody_type, 
            wallet_set_id=wallet_set_id,
            role=role,
            wallet_type=wallet_type
        )
        db.add(w)
        db.commit()
        log_audit("wallet_created", {
            "wallet_id": wallet_id, 
            "address": address, 
            "blockchain": blockchain,
            "account_type": account_type,
            "role": role,
            "wallet_type": wallet_type
        })
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving wallet: {str(e)}")
        raise
    finally:
        db.close()

def save_transaction(tx_id, wallet_id, token_id, destination_address, amount, status, tx_hash=None, blockchain=None):
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
            confirmation_required=confirmation_required
        )
        db.add(t)
        db.commit()
        log_audit("transaction_initiated", {
            "tx_id": tx_id, 
            "wallet_id": wallet_id, 
            "amount": amount, 
            "status": status,
            "blockchain": blockchain
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

async def save_webhook_event(subscription_id: str, notification_id: str, 
                           notification_type: str, notification_data: dict,
                           timestamp: str, version: int):
    """Save webhook event to database"""
    db = SessionLocal()
    try:
        # Parse timestamp
        parsed_timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        event = WebhookEvent(
            subscription_id=subscription_id,
            notification_id=notification_id,
            notification_type=notification_type,
            notification_data=notification_data,
            timestamp=parsed_timestamp,
            version=version
        )
        db.add(event)
        db.commit()
        log_audit("webhook_event_saved", {
            "notification_id": notification_id,
            "notification_type": notification_type
        })
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving webhook event: {str(e)}")
        raise
    finally:
        db.close()

async def save_webhook_attempt(notification_id: str, status: str, 
                             error_message: str = None, payload: dict = None):
    """Save webhook attempt for debugging"""
    db = SessionLocal()
    try:
        # Get attempt number
        attempt_count = db.query(WebhookAttempt).filter(
            WebhookAttempt.notification_id == notification_id
        ).count()
        
        attempt = WebhookAttempt(
            notification_id=notification_id,
            status=status,
            error_message=error_message,
            payload=payload or {},
            attempt_number=attempt_count + 1
        )
        db.add(attempt)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving webhook attempt: {str(e)}")
        raise
    finally:
        db.close()

def get_wallet_by_role(role: str):
    """Get wallet by role (backendMirror, circleEngine, solanaOperations)"""
    db = SessionLocal()
    try:
        wallet = db.query(Wallet).filter(Wallet.role == role).first()
        return wallet
    except Exception as e:
        logger.error(f"Error getting wallet by role: {str(e)}")
        return None
    finally:
        db.close()

def get_wallets_by_type(wallet_type: str):
    """Get all wallets by type (EVM, SOLANA)"""
    db = SessionLocal()
    try:
        wallets = db.query(Wallet).filter(Wallet.wallet_type == wallet_type).all()
        return wallets
    except Exception as e:
        logger.error(f"Error getting wallets by type: {str(e)}")
        return []
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
