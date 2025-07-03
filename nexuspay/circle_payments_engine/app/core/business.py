from app.db.session import SessionLocal
from app.models.wallet import WalletSet, Wallet, Transaction
from app.utils.audit import log_audit

def save_wallet_set(wallet_set_id, name, custody_type):
    db = SessionLocal()
    try:
        ws = WalletSet(id=wallet_set_id, name=name, custody_type=custody_type)
        db.add(ws)
        db.commit()
        log_audit("wallet_set_created", {"wallet_set_id": wallet_set_id, "name": name, "custody_type": custody_type})
    finally:
        db.close()

def save_wallet(wallet_id, address, blockchain, account_type, state, custody_type, wallet_set_id):
    db = SessionLocal()
    try:
        w = Wallet(
            id=wallet_id, address=address, blockchain=blockchain, account_type=account_type,
            state=state, custody_type=custody_type, wallet_set_id=wallet_set_id
        )
        db.add(w)
        db.commit()
        log_audit("wallet_created", {"wallet_id": wallet_id, "address": address, "blockchain": blockchain})
    finally:
        db.close()

def save_transaction(tx_id, wallet_id, token_id, destination_address, amount, status, tx_hash=None):
    db = SessionLocal()
    try:
        t = Transaction(
            id=tx_id, wallet_id=wallet_id, token_id=token_id, destination_address=destination_address,
            amount=amount, status=status, tx_hash=tx_hash
        )
        db.add(t)
        db.commit()
        log_audit("transaction_initiated", {"tx_id": tx_id, "wallet_id": wallet_id, "amount": amount, "status": status})
    finally:
        db.close()
