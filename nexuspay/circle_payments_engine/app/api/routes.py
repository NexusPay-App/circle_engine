from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from app.core.circle_wallets import (
    create_wallet_set, create_wallets, get_wallet_balance, transfer_tokens
)

router = APIRouter()

class WalletSetRequest(BaseModel):
    name: str

class WalletsRequest(BaseModel):
    wallet_set_id: str
    blockchains: List[str]
    account_type: str
    count: int = 2

class TransferRequest(BaseModel):
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
        wallets = create_wallets(request.wallet_set_id, request.blockchains, request.account_type, request.count)
        return {"wallets": wallets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/wallets/{wallet_id}/balance")
def api_get_wallet_balance(wallet_id: str):
    try:
        balance = get_wallet_balance(wallet_id)
        return {"balance": balance}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/transactions")
def api_transfer_tokens(request: TransferRequest):
    try:
        tx = transfer_tokens(request.wallet_id, request.token_id, request.destination_address, request.amount)
        return {"transaction": tx}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
