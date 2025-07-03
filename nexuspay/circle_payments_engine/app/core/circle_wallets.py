import uuid
from circle.web3 import developer_controlled_wallets, utils
from app.utils.config import get_circle_api_key, get_entity_secret, get_backendmirror_wallet_address
from app.utils.logger import logger
from app.core.business import save_wallet_set, save_wallet, save_transaction
from app.utils.audit import log_audit

# Helper to initialize the Circle client

def get_circle_client():
    api_key = get_circle_api_key()
    entity_secret = get_entity_secret()
    return utils.init_developer_controlled_wallets_client(api_key=api_key, entity_secret=entity_secret)

# 1. Create a Wallet Set

def create_wallet_set(name: str):
    client = get_circle_client()
    api_instance = developer_controlled_wallets.WalletSetsApi(client)
    idempotency_key = str(uuid.uuid4())
    request = developer_controlled_wallets.CreateWalletSetRequest.from_dict({
        "name": name,
        "idempotencyKey": idempotency_key,
        "entitySecretCiphertext": get_entity_secret()
    })
    logger.info(f"Creating wallet set: {name} with idempotencyKey: {idempotency_key}")
    response = api_instance.create_wallet_set(request)
    ws = response.data.walletSet
    save_wallet_set(ws.id, name, ws.custodyType)
    log_audit("circle_wallet_set_created", ws.to_dict())
    return ws.id

# 2. Create Wallets (EVM and Solana)

def create_wallets(wallet_set_id: str, blockchains: list, account_type: str, count: int):
    client = get_circle_client()
    api_instance = developer_controlled_wallets.WalletsApi(client)
    idempotency_key = str(uuid.uuid4())
    request = developer_controlled_wallets.CreateWalletRequest.from_dict({
        "accountType": account_type,
        "blockchains": blockchains,
        "count": count,
        "walletSetId": wallet_set_id,
        "idempotencyKey": idempotency_key,
        "entitySecretCiphertext": get_entity_secret()
    })
    logger.info(f"Creating {count} wallets in set {wallet_set_id} on {blockchains} with idempotencyKey: {idempotency_key}")
    response = api_instance.create_wallet(request)
    backendmirror_address = get_backendmirror_wallet_address()
    result = []
    for wallet in response.data.wallets:
        save_wallet(wallet.id, wallet.address, wallet.blockchain, wallet.accountType, wallet.state, wallet.custodyType, wallet.walletSetId)
        log_audit("circle_wallet_created", wallet.to_dict())
        if wallet.address == backendmirror_address:
            result.append({"role": "backendMirror", "wallet": wallet.to_dict()})
        else:
            result.append({"role": "circleEngine", "wallet": wallet.to_dict()})
    return result

# 3. Get Wallet Balance

def get_wallet_balance(wallet_id: str):
    client = get_circle_client()
    api_instance = developer_controlled_wallets.WalletsApi(client)
    logger.info(f"Fetching balance for wallet: {wallet_id}")
    response = api_instance.list_wallet_balance(id=wallet_id)
    log_audit("circle_wallet_balance_fetched", {"wallet_id": wallet_id, "balance": response.data})
    return response.data

# 4. Initiate Transaction

def transfer_tokens(wallet_id: str, token_id: str, destination_address: str, amount: str):
    client = get_circle_client()
    api_instance = developer_controlled_wallets.TransactionsApi(client)
    idempotency_key = str(uuid.uuid4())
    request = developer_controlled_wallets.CreateTransferTransactionForDeveloperRequest.from_dict({
        "walletId": wallet_id,
        "tokenId": token_id,
        "destinationAddress": destination_address,
        "amounts": [amount],
        "feeLevel": "MEDIUM",
        "idempotencyKey": idempotency_key,
        "entitySecretCiphertext": get_entity_secret()
    })
    logger.info(f"Transferring {amount} of token {token_id} from wallet {wallet_id} to {destination_address} with idempotencyKey: {idempotency_key}")
    response = api_instance.create_developer_transaction_transfer(request)
    tx = response.data
    save_transaction(tx.id, wallet_id, token_id, destination_address, amount, tx.status, getattr(tx, 'txHash', None))
    log_audit("circle_transaction_initiated", tx.to_dict())
    return tx