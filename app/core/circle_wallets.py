import uuid
from circle.web3 import developer_controlled_wallets, utils
from app.utils.config import get_circle_api_key, get_entity_secret, get_backendmirror_wallet_address
from app.utils.logger import logger
from app.core.business.wallet_business import save_wallet_set, save_wallet
from app.core.business.transaction_business import save_transaction
from app.core.business.balance_business import get_multi_chain_balance, get_aggregated_balance
from app.core.business.gas_station_business import estimate_gas_fees, sponsor_transaction
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

# 2. Create Comprehensive Wallet Ecosystem (Three-Wallet Architecture)

def create_comprehensive_wallets(wallet_set_id: str):
    """
    Create a complete wallet ecosystem for multi-chain operations:
    1. BackendMirror Wallet (EVM) - Main platform operations
    2. Circle Engine Wallet (EVM) - Circle API operations  
    3. Solana Wallet (EOA) - Solana-specific operations
    """
    client = get_circle_client()
    api_instance = developer_controlled_wallets.WalletsApi(client)
    backendmirror_address = get_backendmirror_wallet_address()
    result = []
    
    # Step 1: Create EVM wallets (BackendMirror + Circle Engine)
    logger.info(f"Creating EVM wallets for wallet set: {wallet_set_id}")
    evm_request = developer_controlled_wallets.CreateWalletRequest.from_dict({
        "accountType": "SCA",  # Smart Contract Account for EVM
        "blockchains": ["ETH", "POLYGON", "ARBITRUM", "BASE", "OPTIMISM", "CELO"],
        "count": 2,  # BackendMirror + Circle Engine
        "walletSetId": wallet_set_id,
        "idempotencyKey": str(uuid.uuid4()),
        "entitySecretCiphertext": get_entity_secret()
    })
    
    evm_response = api_instance.create_wallet(evm_request)
    
    # Process EVM wallets
    for wallet in evm_response.data.wallets:
        save_wallet(wallet.id, wallet.address, wallet.blockchain, 
                   wallet.accountType, wallet.state, wallet.custodyType, wallet.walletSetId)
        
        if wallet.address == backendmirror_address:
            result.append({
                "role": "backendMirror", 
                "type": "EVM", 
                "accountType": "SCA",
                "wallet": wallet.to_dict()
            })
            log_audit("backendmirror_wallet_created", wallet.to_dict())
        else:
            result.append({
                "role": "circleEngine", 
                "type": "EVM", 
                "accountType": "SCA",
                "wallet": wallet.to_dict()
            })
            log_audit("circle_engine_wallet_created", wallet.to_dict())
    
    # Step 2: Create Solana wallet (EOA only)
    logger.info(f"Creating Solana wallet for wallet set: {wallet_set_id}")
    solana_request = developer_controlled_wallets.CreateWalletRequest.from_dict({
        "accountType": "EOA",  # Externally Owned Account (required for Solana)
        "blockchains": ["SOL"],  # Solana only
        "count": 1,  # Single Solana wallet
        "walletSetId": wallet_set_id,
        "idempotencyKey": str(uuid.uuid4()),
        "entitySecretCiphertext": get_entity_secret()
    })
    
    solana_response = api_instance.create_wallet(solana_request)
    
    # Process Solana wallet
    for wallet in solana_response.data.wallets:
        save_wallet(wallet.id, wallet.address, wallet.blockchain, 
                   wallet.accountType, wallet.state, wallet.custodyType, wallet.walletSetId)
        result.append({
            "role": "solanaOperations", 
            "type": "SOLANA", 
            "accountType": "EOA",
            "wallet": wallet.to_dict()
        })
        log_audit("solana_wallet_created", wallet.to_dict())
    
    logger.info(f"Successfully created {len(result)} wallets: {[w['role'] for w in result]}")
    return result

# 2.1 Legacy function for backward compatibility
def create_wallets(wallet_set_id: str, blockchains: list, account_type: str, count: int):
    """
    Legacy function - now redirects to create_comprehensive_wallets
    """
    logger.warning("Using legacy create_wallets function. Consider using create_comprehensive_wallets instead.")
    
    # If this is a Solana request, handle it specially
    if "SOL" in blockchains or account_type == "EOA":
        return create_solana_wallet(wallet_set_id, count)
    
    # For EVM requests, use the comprehensive function
    return create_comprehensive_wallets(wallet_set_id)

# 2.2 Solana-specific wallet creation
def create_solana_wallet(wallet_set_id: str, count: int = 1):
    """
    Create Solana-specific wallets (EOA only)
    """
    client = get_circle_client()
    api_instance = developer_controlled_wallets.WalletsApi(client)
    idempotency_key = str(uuid.uuid4())
    
    request = developer_controlled_wallets.CreateWalletRequest.from_dict({
        "accountType": "EOA",  # Externally Owned Account (required for Solana)
        "blockchains": ["SOL"],  # Solana only
        "count": count,
        "walletSetId": wallet_set_id,
        "idempotencyKey": idempotency_key,
        "entitySecretCiphertext": get_entity_secret()
    })
    
    logger.info(f"Creating {count} Solana wallet(s) in set {wallet_set_id} with idempotencyKey: {idempotency_key}")
    response = api_instance.create_wallet(request)
    
    result = []
    for wallet in response.data.wallets:
        save_wallet(wallet.id, wallet.address, wallet.blockchain, 
                   wallet.accountType, wallet.state, wallet.custodyType, wallet.walletSetId)
        log_audit("solana_wallet_created", wallet.to_dict())
        result.append({
            "role": "solanaOperations", 
            "type": "SOLANA", 
            "accountType": "EOA",
            "wallet": wallet.to_dict()
        })
    
    return result

# 3. Get Wallet Balance

def get_wallet_balance(wallet_id: str):
    client = get_circle_client()
    api_instance = developer_controlled_wallets.WalletsApi(client)
    logger.info(f"Fetching balance for wallet: {wallet_id}")
    response = api_instance.list_wallet_balance(id=wallet_id)
    log_audit("circle_wallet_balance_fetched", {"wallet_id": wallet_id, "balance": response.data})
    return response.data

# 3.1 Solana-specific balance checking
def get_solana_wallet_balance(wallet_id: str):
    """
    Get Solana wallet balance with SPL token support
    """
    client = get_circle_client()
    api_instance = developer_controlled_wallets.WalletsApi(client)
    logger.info(f"Fetching Solana balance for wallet: {wallet_id}")
    response = api_instance.list_wallet_balance(id=wallet_id)
    
    # Solana-specific balance processing
    balance_data = response.data
    log_audit("solana_wallet_balance_fetched", {
        "wallet_id": wallet_id, 
        "balance": balance_data,
        "blockchain": "SOL"
    })
    
    return balance_data

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

# 4.1 Solana-specific transaction handling
def transfer_tokens_solana(wallet_id: str, token_id: str, destination_address: str, amount: str):
    """
    Handle Solana-specific token transfers with ATA considerations
    """
    client = get_circle_client()
    api_instance = developer_controlled_wallets.TransactionsApi(client)
    idempotency_key = str(uuid.uuid4())
    
    # Solana-specific request parameters
    request = developer_controlled_wallets.CreateTransferTransactionForDeveloperRequest.from_dict({
        "walletId": wallet_id,
        "tokenId": token_id,
        "destinationAddress": destination_address,
        "amounts": [amount],
        "feeLevel": "MEDIUM",
        "idempotencyKey": idempotency_key,
        "entitySecretCiphertext": get_entity_secret(),
        # Solana-specific parameters
        "blockchain": "SOL",
        "feePayer": wallet_id  # Use wallet as fee payer for Gas Station
    })
    
    logger.info(f"Transferring {amount} of Solana token {token_id} from wallet {wallet_id} to {destination_address} with idempotencyKey: {idempotency_key}")
    response = api_instance.create_developer_transaction_transfer(request)
    tx = response.data
    
    # Enhanced logging for Solana transactions
    save_transaction(
        tx.id, wallet_id, token_id, destination_address, amount, 
        tx.status, getattr(tx, 'txHash', None), blockchain="SOL"
    )
    
    log_audit("solana_transaction_initiated", {
        "tx_id": tx.id,
        "wallet_id": wallet_id,
        "amount": amount,
        "destination": destination_address,
        "ata_auto_created": True,  # Solana automatically creates ATAs
        "blockchain": "SOL"
    })
    
    return tx

# 5. Get transaction confirmation status
def get_transaction_confirmation_status(tx_id: str, blockchain: str):
    """
    Track transaction confirmation status based on blockchain-specific requirements
    """
    confirmation_requirements = {
        "ETH": {"confirmations": 12, "time": "~3 minutes"},
        "POLYGON": {"confirmations": 50, "time": "~2 minutes"},
        "ARBITRUM": {"confirmations": 12, "time": "~3 minutes"},
        "BASE": {"confirmations": 12, "time": "~3 minutes"},
        "OPTIMISM": {"confirmations": 12, "time": "~4 minutes"},
        "SOL": {"confirmations": 33, "time": "~13 seconds"},
        "AVALANCHE": {"confirmations": 1, "time": "~2 seconds"},
        "CELO": {"confirmations": 12, "time": "~3 minutes"}
    }
    
    client = get_circle_client()
    api_instance = developer_controlled_wallets.TransactionsApi(client)
    response = api_instance.get_transaction(tx_id)
    
    tx = response.data
    requirements = confirmation_requirements.get(blockchain, {"confirmations": 12, "time": "~3 minutes"})
    
    return {
        "transaction_id": tx_id,
        "status": tx.status,  # PENDING, CONFIRMED, COMPLETED, FAILED
        "blockchain": blockchain,
        "confirmations_required": requirements["confirmations"],
        "estimated_completion": requirements["time"],
        "is_final": tx.status == "COMPLETED",
        "tx_hash": getattr(tx, 'txHash', None)
    }