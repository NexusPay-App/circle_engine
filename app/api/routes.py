from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.core.circle_wallets import (
    create_wallet_set, create_comprehensive_wallets, create_solana_wallet,
    get_wallet_balance, get_solana_wallet_balance, transfer_tokens, 
    transfer_tokens_solana, get_transaction_confirmation_status
)
from app.core.business.wallet_business import get_wallet_by_role, get_wallets_by_type
from app.core.business.transaction_business import get_transactions_by_blockchain
from app.core.business.balance_business import get_multi_chain_balance, get_aggregated_balance
from app.core.business.gas_station_business import estimate_gas_fees, sponsor_transaction

router = APIRouter()

class WalletSetRequest(BaseModel):
    name: str

class WalletsRequest(BaseModel):
    wallet_set_id: str
    blockchains: List[str]
    account_type: str
    count: int = 2

class ComprehensiveWalletsRequest(BaseModel):
    wallet_set_id: str

class SolanaWalletRequest(BaseModel):
    wallet_set_id: str
    count: int = 1

class TransferRequest(BaseModel):
    wallet_id: str
    token_id: str
    destination_address: str
    amount: str
    blockchain: Optional[str] = None

class SolanaTransferRequest(BaseModel):
    wallet_id: str
    token_id: str
    destination_address: str
    amount: str

@router.post("/wallet-sets")
def api_create_wallet_set(request: WalletSetRequest):
    try:
        wallet_set_id = create_wallet_set(request.name)
        return {"walletSetId": wallet_set_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/wallets")
def api_create_wallets(request: WalletsRequest):
    try:
        wallets = create_comprehensive_wallets(request.wallet_set_id)
        return {"wallets": wallets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/wallets/comprehensive")
def api_create_comprehensive_wallets(request: ComprehensiveWalletsRequest):
    """
    Create a complete wallet ecosystem (BackendMirror + Circle Engine + Solana)
    """
    try:
        wallets = create_comprehensive_wallets(request.wallet_set_id)
        return {
            "message": "Comprehensive wallet ecosystem created successfully",
            "wallets": wallets,
            "total_wallets": len(wallets)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/wallets/solana")
def api_create_solana_wallet(request: SolanaWalletRequest):
    """Create Solana-specific wallet (EOA only)"""
    try:
        wallets = create_solana_wallet(request.wallet_set_id, request.count)
        return {
            "message": "Solana wallet(s) created successfully",
            "wallets": wallets,
            "account_type": "EOA",
            "blockchain": "SOL"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/wallets/{wallet_id}/balance")
def api_get_wallet_balance(wallet_id: str):
    try:
        balance = get_wallet_balance(wallet_id)
        return {"balance": balance}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/wallets/{wallet_id}/solana-balance")
def api_get_solana_balance(wallet_id: str):
    """Get Solana wallet balance with SPL token support"""
    try:
        balance = get_solana_wallet_balance(wallet_id)
        return {
            "balance": balance,
            "blockchain": "SOL",
            "account_type": "EOA"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/transactions")
def api_transfer_tokens(request: TransferRequest):
    try:
        # Determine if this is a Solana transaction
        if request.blockchain == "SOL":
            tx = transfer_tokens_solana(
                request.wallet_id, 
                request.token_id, 
                request.destination_address, 
                request.amount
            )
        else:
            tx = transfer_tokens(
                request.wallet_id, 
                request.token_id, 
                request.destination_address, 
                request.amount
            )
        return {"transaction": tx}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/transactions/solana")
def api_transfer_solana_tokens(request: SolanaTransferRequest):
    """Handle Solana-specific token transfers"""
    try:
        tx = transfer_tokens_solana(
            request.wallet_id, 
            request.token_id, 
            request.destination_address, 
            request.amount
        )
        return {
            "transaction": tx,
            "blockchain": "SOL",
            "ata_auto_created": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/transactions/{tx_id}/confirmation-status")
def api_get_transaction_confirmation_status(tx_id: str, blockchain: str):
    """Get transaction confirmation status based on blockchain requirements"""
    try:
        status = get_transaction_confirmation_status(tx_id, blockchain)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/wallets/role/{role}")
def api_get_wallet_by_role(role: str):
    """Get wallet by role (backendMirror, circleEngine, solanaOperations)"""
    try:
        wallet = get_wallet_by_role(role)
        if wallet:
            return {
                "wallet": {
                    "id": wallet.id,
                    "address": wallet.address,
                    "blockchain": wallet.blockchain,
                    "account_type": wallet.account_type,
                    "role": wallet.role,
                    "wallet_type": wallet.wallet_type,
                    "state": wallet.state
                }
            }
        else:
            raise HTTPException(status_code=404, detail=f"Wallet with role '{role}' not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/wallets/type/{wallet_type}")
def api_get_wallets_by_type(wallet_type: str):
    """Get all wallets by type (EVM, SOLANA)"""
    try:
        wallets = get_wallets_by_type(wallet_type)
        return {
            "wallets": [
                {
                    "id": wallet.id,
                    "address": wallet.address,
                    "blockchain": wallet.blockchain,
                    "account_type": wallet.account_type,
                    "role": wallet.role,
                    "wallet_type": wallet.wallet_type,
                    "state": wallet.state
                }
                for wallet in wallets
            ],
            "total": len(wallets),
            "wallet_type": wallet_type
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/transactions/blockchain/{blockchain}")
def api_get_transactions_by_blockchain(blockchain: str, limit: int = 100):
    """Get transactions by blockchain"""
    try:
        transactions = get_transactions_by_blockchain(blockchain, limit)
        return {
            "transactions": [
                {
                    "id": tx.id,
                    "wallet_id": tx.wallet_id,
                    "token_id": tx.token_id,
                    "destination_address": tx.destination_address,
                    "amount": tx.amount,
                    "status": tx.status,
                    "blockchain": tx.blockchain,
                    "tx_hash": tx.tx_hash,
                    "confirmations": tx.confirmations,
                    "confirmation_required": tx.confirmation_required,
                    "created_at": tx.created_at.isoformat() if tx.created_at else None
                }
                for tx in transactions
            ],
            "total": len(transactions),
            "blockchain": blockchain
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/wallets/ecosystem/status")
def api_get_wallet_ecosystem_status():
    """Get status of the complete wallet ecosystem"""
    try:
        backendmirror_wallet = get_wallet_by_role("backendMirror")
        circle_engine_wallet = get_wallet_by_role("circleEngine")
        solana_wallet = get_wallet_by_role("solanaOperations")
        
        return {
            "ecosystem_status": "complete" if all([backendmirror_wallet, circle_engine_wallet, solana_wallet]) else "incomplete",
            "wallets": {
                "backendMirror": {
                    "exists": backendmirror_wallet is not None,
                    "address": backendmirror_wallet.address if backendmirror_wallet else None,
                    "blockchain": backendmirror_wallet.blockchain if backendmirror_wallet else None,
                    "account_type": backendmirror_wallet.account_type if backendmirror_wallet else None
                },
                "circleEngine": {
                    "exists": circle_engine_wallet is not None,
                    "address": circle_engine_wallet.address if circle_engine_wallet else None,
                    "blockchain": circle_engine_wallet.blockchain if circle_engine_wallet else None,
                    "account_type": circle_engine_wallet.account_type if circle_engine_wallet else None
                },
                "solanaOperations": {
                    "exists": solana_wallet is not None,
                    "address": solana_wallet.address if solana_wallet else None,
                    "blockchain": solana_wallet.blockchain if solana_wallet else None,
                    "account_type": solana_wallet.account_type if solana_wallet else None
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
