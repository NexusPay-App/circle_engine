from app.db.session import SessionLocal
from app.models.wallet import Balance, Wallet
from app.utils.audit import log_audit
from app.utils.config import get_blockchain_config
from datetime import datetime
import logging
import asyncio

logger = logging.getLogger(__name__)

async def update_wallet_balance(wallet_id: str, balances: list):
    """Update wallet balance from webhook notification"""
    db = SessionLocal()
    try:
        for balance_data in balances:
            token_id = balance_data.get("tokenId")
            amount = balance_data.get("amount")
            blockchain = balance_data.get("blockchain")
            
            if token_id and amount and blockchain:
                # Check if balance record exists
                existing_balance = db.query(Balance).filter(
                    Balance.wallet_id == wallet_id,
                    Balance.token_id == token_id,
                    Balance.blockchain == blockchain
                ).first()
                
                if existing_balance:
                    # Update existing balance
                    existing_balance.balance_amount = amount
                    existing_balance.last_updated = datetime.utcnow()
                else:
                    # Create new balance record
                    new_balance = Balance(
                        wallet_id=wallet_id,
                        token_id=token_id,
                        blockchain=blockchain,
                        balance_amount=amount,
                        last_updated=datetime.utcnow()
                    )
                    db.add(new_balance)
                
        db.commit()
        log_audit("wallet_balance_updated", {
            "wallet_id": wallet_id,
            "balances_count": len(balances)
        })
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating wallet balance: {str(e)}")
        raise
    finally:
        db.close()

async def get_multi_chain_balance(wallet_id: str):
    """Get aggregated balance across all blockchains for a wallet"""
    db = SessionLocal()
    try:
        balances = db.query(Balance).filter(
            Balance.wallet_id == wallet_id
        ).all()
        
        # Group by blockchain
        blockchain_balances = {}
        for balance in balances:
            blockchain = balance.blockchain
            if blockchain not in blockchain_balances:
                blockchain_balances[blockchain] = []
            blockchain_balances[blockchain].append({
                "token_id": balance.token_id,
                "amount": balance.balance_amount,
                "last_updated": balance.last_updated.isoformat() if balance.last_updated else None
            })
        
        return {
            "wallet_id": wallet_id,
            "blockchain_balances": blockchain_balances,
            "total_blockchains": len(blockchain_balances),
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting multi-chain balance: {str(e)}")
        return None
    finally:
        db.close()

async def get_aggregated_balance(role: str = None, wallet_type: str = None):
    """Get aggregated balance across multiple wallets"""
    db = SessionLocal()
    try:
        # Build query based on filters
        query = db.query(Balance)
        
        if role:
            # Get wallets by role
            wallets = db.query(Wallet).filter(Wallet.role == role).all()
            wallet_ids = [w.id for w in wallets]
            query = query.filter(Balance.wallet_id.in_(wallet_ids))
        elif wallet_type:
            # Get wallets by type
            wallets = db.query(Wallet).filter(Wallet.wallet_type == wallet_type).all()
            wallet_ids = [w.id for w in wallets]
            query = query.filter(Balance.wallet_id.in_(wallet_ids))
        
        balances = query.all()
        
        # Aggregate by blockchain and token
        aggregated = {}
        for balance in balances:
            blockchain = balance.blockchain
            token_id = balance.token_id
            
            if blockchain not in aggregated:
                aggregated[blockchain] = {}
            
            if token_id not in aggregated[blockchain]:
                aggregated[blockchain][token_id] = {
                    "total_amount": "0",
                    "wallet_count": 0,
                    "wallets": []
                }
            
            # Add to total (assuming string amounts that need to be converted)
            try:
                current_total = float(aggregated[blockchain][token_id]["total_amount"])
                balance_amount = float(balance.balance_amount)
                aggregated[blockchain][token_id]["total_amount"] = str(current_total + balance_amount)
                aggregated[blockchain][token_id]["wallet_count"] += 1
                aggregated[blockchain][token_id]["wallets"].append({
                    "wallet_id": balance.wallet_id,
                    "amount": balance.balance_amount
                })
            except (ValueError, TypeError):
                logger.warning(f"Invalid balance amount: {balance.balance_amount}")
        
        return {
            "filter": {"role": role, "wallet_type": wallet_type},
            "aggregated_balances": aggregated,
            "total_blockchains": len(aggregated),
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting aggregated balance: {str(e)}")
        return None
    finally:
        db.close()

async def get_balance_by_blockchain(blockchain: str, role: str = None):
    """Get balance for a specific blockchain"""
    db = SessionLocal()
    try:
        query = db.query(Balance).filter(Balance.blockchain == blockchain)
        
        if role:
            # Get wallets by role
            wallets = db.query(Wallet).filter(Wallet.role == role).all()
            wallet_ids = [w.id for w in wallets]
            query = query.filter(Balance.wallet_id.in_(wallet_ids))
        
        balances = query.all()
        
        # Group by token
        token_balances = {}
        for balance in balances:
            token_id = balance.token_id
            if token_id not in token_balances:
                token_balances[token_id] = {
                    "total_amount": "0",
                    "wallet_count": 0,
                    "wallets": []
                }
            
            try:
                current_total = float(token_balances[token_id]["total_amount"])
                balance_amount = float(balance.balance_amount)
                token_balances[token_id]["total_amount"] = str(current_total + balance_amount)
                token_balances[token_id]["wallet_count"] += 1
                token_balances[token_id]["wallets"].append({
                    "wallet_id": balance.wallet_id,
                    "amount": balance.balance_amount,
                    "last_updated": balance.last_updated.isoformat() if balance.last_updated else None
                })
            except (ValueError, TypeError):
                logger.warning(f"Invalid balance amount: {balance.balance_amount}")
        
        return {
            "blockchain": blockchain,
            "role": role,
            "token_balances": token_balances,
            "total_tokens": len(token_balances),
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting balance by blockchain: {str(e)}")
        return None
    finally:
        db.close()

async def refresh_all_balances():
    """Refresh all wallet balances by calling Circle API"""
    try:
        from app.core.circle_wallets import get_wallet_balance, get_solana_wallet_balance
        from .wallet_business import get_all_wallets
        
        wallets = get_all_wallets()
        blockchain_config = get_blockchain_config()
        
        for wallet in wallets:
            try:
                if wallet.blockchain == "SOL":
                    # Solana balance
                    balance_data = get_solana_wallet_balance(wallet.id)
                else:
                    # EVM balance
                    balance_data = get_wallet_balance(wallet.id)
                
                if balance_data and hasattr(balance_data, 'data'):
                    balances = balance_data.data
                    if isinstance(balances, list):
                        await update_wallet_balance(wallet.id, balances)
                    else:
                        # Convert single balance to list format
                        await update_wallet_balance(wallet.id, [balances])
                
                # Add delay to avoid rate limiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error refreshing balance for wallet {wallet.id}: {str(e)}")
                continue
        
        logger.info(f"Completed balance refresh for {len(wallets)} wallets")
        
    except Exception as e:
        logger.error(f"Error in refresh_all_balances: {str(e)}")

def get_balance_statistics(days: int = 30):
    """Get balance statistics"""
    db = SessionLocal()
    try:
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        balances = db.query(Balance).filter(
            Balance.last_updated >= cutoff_date
        ).all()
        
        stats = {
            "total_balance_records": len(balances),
            "blockchain_breakdown": {},
            "token_breakdown": {},
            "wallet_breakdown": {}
        }
        
        for balance in balances:
            # Blockchain breakdown
            blockchain = balance.blockchain
            if blockchain not in stats["blockchain_breakdown"]:
                stats["blockchain_breakdown"][blockchain] = 0
            stats["blockchain_breakdown"][blockchain] += 1
            
            # Token breakdown
            token_id = balance.token_id
            if token_id not in stats["token_breakdown"]:
                stats["token_breakdown"][token_id] = 0
            stats["token_breakdown"][token_id] += 1
            
            # Wallet breakdown
            wallet_id = balance.wallet_id
            if wallet_id not in stats["wallet_breakdown"]:
                stats["wallet_breakdown"][wallet_id] = 0
            stats["wallet_breakdown"][wallet_id] += 1
        
        return stats
    except Exception as e:
        logger.error(f"Error getting balance statistics: {str(e)}")
        return {}
    finally:
        db.close()

async def get_ecosystem_balance_summary():
    """Get complete ecosystem balance summary"""
    try:
        # Get balances for each role
        backendmirror_balance = await get_aggregated_balance(role="backendMirror")
        circle_engine_balance = await get_aggregated_balance(role="circleEngine")
        solana_balance = await get_aggregated_balance(role="solanaOperations")
        
        # Get overall aggregated balance
        total_balance = await get_aggregated_balance()
        
        return {
            "ecosystem_summary": {
                "backendMirror": backendmirror_balance,
                "circleEngine": circle_engine_balance,
                "solanaOperations": solana_balance,
                "total": total_balance
            },
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting ecosystem balance summary: {str(e)}")
        return None 