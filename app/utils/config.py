import os
import uuid
from dotenv import load_dotenv

load_dotenv()

ENV_FILE = os.path.join(os.path.dirname(__file__), '../../.env')

def get_circle_api_key():
    api_key = os.getenv("CIRCLE_API_KEY")
    if not api_key:
        raise Exception("CIRCLE_API_KEY must be set in your environment or .env file.")
    return api_key

def get_entity_secret():
    """
    Loads the entity secret from .env. If not present or invalid, generates a new one using the Circle SDK,
    writes it to .env, and returns it. If the SDK prints but does not return the secret, prompts the user to paste it.
    """
    entity_secret = os.getenv("CIRCLE_ENTITY_SECRET")
    if entity_secret and isinstance(entity_secret, str) and len(entity_secret) == 64 and all(c in '0123456789abcdefABCDEF' for c in entity_secret):
        print(f"Loaded entity secret from .env: {entity_secret}")
        return entity_secret

    # If not present or invalid, generate using the SDK
    from circle.web3 import utils
    print("Generating entity secret using Circle SDK...")
    entity_secret = utils.generate_entity_secret()
    if not entity_secret or not isinstance(entity_secret, str) or len(entity_secret) != 64 or not all(c in '0123456789abcdefABCDEF' for c in entity_secret):
        print("SDK did not return a valid entity secret. Please copy the entity secret printed above and paste it here.")
        entity_secret = input("Paste the 64-character entity secret: ").strip()
        if not entity_secret or len(entity_secret) != 64 or not all(c in '0123456789abcdefABCDEF' for c in entity_secret):
            raise Exception("Failed to obtain a valid entity secret.")
    print(f"Using entity secret: {entity_secret} (length: {len(entity_secret)})")

    # Write to .env
    lines = []
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, 'r') as f:
            lines = f.readlines()
    found = False
    for i, line in enumerate(lines):
        if line.startswith("CIRCLE_ENTITY_SECRET="):
            lines[i] = f"CIRCLE_ENTITY_SECRET={entity_secret}\n"
            found = True
            break
    if not found:
        lines.append(f"CIRCLE_ENTITY_SECRET={entity_secret}\n")
    with open(ENV_FILE, 'w') as f:
        f.writelines(lines)
    print(f"Entity Secret written to {ENV_FILE} as CIRCLE_ENTITY_SECRET")
    return entity_secret

def get_entity_secret_recovery_dir():
    path = os.getenv("ENTITY_SECRET_RECOVERY_DIR")
    if not path:
        raise Exception("ENTITY_SECRET_RECOVERY_DIR must be set in your environment or .env file.")
    return path

# This should match the DEV_PLATFORM_WALLET_ADDRESS from backendMirror .env
# and be set as BACKENDMIRROR_WALLET_ADDRESS in this .env

def get_backendmirror_wallet_address():
    address = os.getenv("BACKENDMIRROR_WALLET_ADDRESS")
    if not address:
        raise Exception("BACKENDMIRROR_WALLET_ADDRESS must be set in your environment or .env file.")
    return address

def get_solana_wallet_address():
    """
    Get Solana wallet address for Solana-specific operations
    """
    address = os.getenv("SOLANA_WALLET_ADDRESS")
    if not address:
        # If not set, we'll create one dynamically
        return None
    return address

def get_webhook_config():
    """Get webhook configuration"""
    return {
        "timeout_seconds": int(os.getenv("WEBHOOK_TIMEOUT_SECONDS", "5")),
        "max_retries": int(os.getenv("WEBHOOK_MAX_RETRIES", "3")),
        "retry_delay_seconds": int(os.getenv("WEBHOOK_RETRY_DELAY_SECONDS", "60")),
        "backendmirror_url": os.getenv("BACKENDMIRROR_WEBHOOK_URL", "http://backendmirror:8000/api/webhooks/circle"),
        "allowed_ips": [
            "54.243.112.156",
            "100.24.191.35", 
            "54.165.52.248",
            "54.87.106.46"
        ],
        "subscribed_events": [
            "transactions.inbound",
            "transactions.outbound",
            "mint.completed",
            "redeem.completed",
            "webhooks.test"
        ],
        "webhook_logs_enabled": True
    }

def get_blockchain_config():
    """Get blockchain-specific configuration"""
    return {
        "supported_evm_chains": ["ETH", "POLYGON", "ARBITRUM", "BASE", "OPTIMISM", "CELO"],
        "supported_solana_chains": ["SOL"],
        "confirmation_requirements": {
            "ETH": 12,
            "POLYGON": 50,
            "ARBITRUM": 12,
            "BASE": 12,
            "OPTIMISM": 12,
            "SOL": 33,
            "AVALANCHE": 1,
            "CELO": 12
        },
        "gas_station_support": {
            "ETH": True,
            "POLYGON": True,
            "ARBITRUM": True,
            "BASE": True,
            "OPTIMISM": True,
            "SOL": True,  # Native fee sponsorship
            "CELO": True
        }
    }

def get_wallet_ecosystem_config():
    """Get wallet ecosystem configuration"""
    return {
        "wallet_roles": {
            "backendMirror": {
                "type": "EVM",
                "account_type": "SCA",
                "blockchains": ["ETH", "POLYGON", "ARBITRUM", "BASE", "OPTIMISM", "CELO"],
                "description": "Main platform operations"
            },
            "circleEngine": {
                "type": "EVM", 
                "account_type": "SCA",
                "blockchains": ["ETH", "POLYGON", "ARBITRUM", "BASE", "OPTIMISM", "CELO"],
                "description": "Circle API operations"
            },
            "solanaOperations": {
                "type": "SOLANA",
                "account_type": "EOA",
                "blockchains": ["SOL"],
                "description": "Solana-specific operations"
            }
        },
        "required_wallets": ["backendMirror", "circleEngine", "solanaOperations"]
    }

