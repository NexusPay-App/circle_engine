from app.db.session import SessionLocal
from app.models.wallet import WalletSet, Wallet
from app.utils.audit import log_audit
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def save_wallet_set(wallet_set_id, name, custody_type):
    """Save wallet set to database"""
    db = SessionLocal()
    try:
        ws = WalletSet(id=wallet_set_id, name=name, custody_type=custody_type)
        db.add(ws)
        db.commit()
        log_audit("wallet_set_created", {
            "wallet_set_id": wallet_set_id, 
            "name": name, 
            "custody_type": custody_type
        })
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving wallet set: {str(e)}")
        raise
    finally:
        db.close()

def save_wallet(wallet_id, address, blockchain, account_type, state, custody_type, wallet_set_id, role=None, wallet_type=None, ref_id=None):
    """Save wallet to database with role, type, and ref_id tracking"""
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
            wallet_type=wallet_type,
            ref_id=ref_id
        )
        db.add(w)
        db.commit()
        log_audit("wallet_created", {
            "wallet_id": wallet_id, 
            "address": address, 
            "blockchain": blockchain,
            "account_type": account_type,
            "role": role,
            "wallet_type": wallet_type,
            "ref_id": ref_id
        })
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving wallet: {str(e)}")
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

def get_wallet_by_address(address: str):
    """Get wallet by address"""
    db = SessionLocal()
    try:
        wallet = db.query(Wallet).filter(Wallet.address == address).first()
        return wallet
    except Exception as e:
        logger.error(f"Error getting wallet by address: {str(e)}")
        return None
    finally:
        db.close()

def get_wallets_by_blockchain(blockchain: str):
    """Get all wallets by blockchain"""
    db = SessionLocal()
    try:
        wallets = db.query(Wallet).filter(Wallet.blockchain == blockchain).all()
        return wallets
    except Exception as e:
        logger.error(f"Error getting wallets by blockchain: {str(e)}")
        return []
    finally:
        db.close()

def update_wallet_state(wallet_id: str, new_state: str):
    """Update wallet state"""
    db = SessionLocal()
    try:
        wallet = db.query(Wallet).filter(Wallet.id == wallet_id).first()
        if wallet:
            old_state = wallet.state
            wallet.state = new_state
            db.commit()
            log_audit("wallet_state_updated", {
                "wallet_id": wallet_id,
                "old_state": old_state,
                "new_state": new_state
            })
            return True
        return False
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating wallet state: {str(e)}")
        return False
    finally:
        db.close()

def get_wallet_set_by_id(wallet_set_id: str):
    """Get wallet set by ID"""
    db = SessionLocal()
    try:
        wallet_set = db.query(WalletSet).filter(WalletSet.id == wallet_set_id).first()
        return wallet_set
    except Exception as e:
        logger.error(f"Error getting wallet set: {str(e)}")
        return None
    finally:
        db.close()

def get_all_wallets():
    """Get all wallets"""
    db = SessionLocal()
    try:
        wallets = db.query(Wallet).all()
        return wallets
    except Exception as e:
        logger.error(f"Error getting all wallets: {str(e)}")
        return []
    finally:
        db.close()

def get_wallet_ecosystem_status():
    """Get complete wallet ecosystem status"""
    db = SessionLocal()
    try:
        backendmirror_wallet = db.query(Wallet).filter(Wallet.role == "backendMirror").first()
        circle_engine_wallet = db.query(Wallet).filter(Wallet.role == "circleEngine").first()
        solana_wallet = db.query(Wallet).filter(Wallet.role == "solanaOperations").first()
        
        return {
            "ecosystem_status": "complete" if all([backendmirror_wallet, circle_engine_wallet, solana_wallet]) else "incomplete",
            "wallets": {
                "backendMirror": {
                    "exists": backendmirror_wallet is not None,
                    "address": backendmirror_wallet.address if backendmirror_wallet else None,
                    "blockchain": backendmirror_wallet.blockchain if backendmirror_wallet else None,
                    "account_type": backendmirror_wallet.account_type if backendmirror_wallet else None,
                    "state": backendmirror_wallet.state if backendmirror_wallet else None
                },
                "circleEngine": {
                    "exists": circle_engine_wallet is not None,
                    "address": circle_engine_wallet.address if circle_engine_wallet else None,
                    "blockchain": circle_engine_wallet.blockchain if circle_engine_wallet else None,
                    "account_type": circle_engine_wallet.account_type if circle_engine_wallet else None,
                    "state": circle_engine_wallet.state if circle_engine_wallet else None
                },
                "solanaOperations": {
                    "exists": solana_wallet is not None,
                    "address": solana_wallet.address if solana_wallet else None,
                    "blockchain": solana_wallet.blockchain if solana_wallet else None,
                    "account_type": solana_wallet.account_type if solana_wallet else None,
                    "state": solana_wallet.state if solana_wallet else None
                }
            }
        }
    except Exception as e:
        logger.error(f"Error getting ecosystem status: {str(e)}")
        return None
    finally:
        db.close() 


def update_wallet_ref_id(wallet_id: str, ref_id: str):
    """
    Update the ref_id for a wallet in the database.
    """
    db = SessionLocal()
    try:
        wallet = db.query(Wallet).filter(Wallet.id == wallet_id).first()
        if wallet:
            wallet.ref_id = ref_id
            db.commit()
            log_audit("wallet_ref_id_updated", {
                "wallet_id": wallet_id,
                "ref_id": ref_id
            })
            return True
        return False
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating wallet ref_id: {str(e)}")
        return False
    finally:
        db.close()
    