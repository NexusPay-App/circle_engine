#!/usr/bin/env python3
"""
Setup script for Circle Payments Engine Wallet Ecosystem
Creates the complete three-wallet architecture:
1. BackendMirror Wallet (EVM) - Main platform operations
2. Circle Engine Wallet (EVM) - Circle API operations  
3. Solana Wallet (EOA) - Solana-specific operations
"""

import sys
import os
import asyncio
import httpx
from datetime import datetime

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.circle_wallets import create_wallet_set, create_comprehensive_wallets
from app.utils.config import get_circle_api_key, get_backendmirror_wallet_address, get_wallet_ecosystem_config
from app.core.business import get_wallet_by_role
from app.utils.logger import logger

async def setup_wallet_ecosystem():
    """
    Setup the complete wallet ecosystem
    """
    print("🚀 Setting up Circle Payments Engine Wallet Ecosystem")
    print("=" * 60)
    
    try:
        # Step 1: Create wallet set
        print("\n📦 Step 1: Creating wallet set...")
        wallet_set_name = f"NexusPay-WalletSet-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        wallet_set_id = create_wallet_set(wallet_set_name)
        print(f"✅ Wallet set created: {wallet_set_id}")
        
        # Step 2: Create comprehensive wallet ecosystem
        print("\n🔑 Step 2: Creating comprehensive wallet ecosystem...")
        wallets = create_comprehensive_wallets(wallet_set_id)
        
        print(f"✅ Successfully created {len(wallets)} wallets:")
        for wallet in wallets:
            role = wallet['role']
            wallet_type = wallet['type']
            account_type = wallet['accountType']
            address = wallet['wallet']['address']
            blockchain = wallet['wallet']['blockchain']
            
            print(f"   • {role} ({wallet_type} - {account_type})")
            print(f"     Address: {address}")
            print(f"     Blockchain: {blockchain}")
            print()
        
        # Step 3: Verify ecosystem status
        print("\n🔍 Step 3: Verifying ecosystem status...")
        ecosystem_config = get_wallet_ecosystem_config()
        required_wallets = ecosystem_config['required_wallets']
        
        missing_wallets = []
        for role in required_wallets:
            wallet = get_wallet_by_role(role)
            if wallet:
                print(f"✅ {role} wallet exists: {wallet.address}")
            else:
                print(f"❌ {role} wallet missing")
                missing_wallets.append(role)
        
        if missing_wallets:
            print(f"\n⚠️  Warning: Missing wallets: {missing_wallets}")
            return False
        else:
            print("\n🎉 All required wallets created successfully!")
        
        # Step 4: Display configuration
        print("\n📋 Step 4: Configuration Summary")
        print("-" * 40)
        print(f"Wallet Set ID: {wallet_set_id}")
        print(f"Wallet Set Name: {wallet_set_name}")
        print(f"Total Wallets: {len(wallets)}")
        print(f"BackendMirror Address: {get_backendmirror_wallet_address()}")
        
        # Step 5: Save configuration
        print("\n💾 Step 5: Saving configuration...")
        config_data = {
            "wallet_set_id": wallet_set_id,
            "wallet_set_name": wallet_set_name,
            "created_at": datetime.now().isoformat(),
            "wallets": wallets
        }
        
        config_file = f"wallet_ecosystem_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        import json
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        print(f"✅ Configuration saved to: {config_file}")
        
        # Step 6: Environment variables reminder
        print("\n🔧 Step 6: Environment Variables")
        print("-" * 40)
        print("Make sure these environment variables are set in your .env file:")
        print(f"BACKENDMIRROR_WALLET_ADDRESS={get_backendmirror_wallet_address()}")
        print("SOLANA_WALLET_ADDRESS=<your_solana_wallet_address>")
        print("CIRCLE_API_KEY=<your_circle_api_key>")
        print("CIRCLE_ENTITY_SECRET=<your_entity_secret>")
        
        print("\n🎯 Wallet Ecosystem Setup Complete!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error setting up wallet ecosystem: {str(e)}")
        logger.error(f"Wallet ecosystem setup failed: {str(e)}")
        return False

async def verify_ecosystem():
    """
    Verify the current wallet ecosystem status
    """
    print("🔍 Verifying Wallet Ecosystem Status")
    print("=" * 40)
    
    try:
        ecosystem_config = get_wallet_ecosystem_config()
        required_wallets = ecosystem_config['required_wallets']
        
        status = {
            "ecosystem_status": "complete",
            "wallets": {}
        }
        
        for role in required_wallets:
            wallet = get_wallet_by_role(role)
            if wallet:
                status["wallets"][role] = {
                    "exists": True,
                    "address": wallet.address,
                    "blockchain": wallet.blockchain,
                    "account_type": wallet.account_type,
                    "wallet_type": wallet.wallet_type,
                    "state": wallet.state
                }
                print(f"✅ {role}: {wallet.address} ({wallet.blockchain})")
            else:
                status["wallets"][role] = {
                    "exists": False,
                    "address": None,
                    "blockchain": None,
                    "account_type": None,
                    "wallet_type": None,
                    "state": None
                }
                status["ecosystem_status"] = "incomplete"
                print(f"❌ {role}: Missing")
        
        print(f"\n📊 Ecosystem Status: {status['ecosystem_status'].upper()}")
        return status
        
    except Exception as e:
        print(f"❌ Error verifying ecosystem: {str(e)}")
        return None

async def main():
    """
    Main function
    """
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "setup":
            success = await setup_wallet_ecosystem()
            sys.exit(0 if success else 1)
        elif command == "verify":
            status = await verify_ecosystem()
            sys.exit(0 if status and status['ecosystem_status'] == 'complete' else 1)
        elif command == "help":
            print("Circle Payments Engine Wallet Ecosystem Setup")
            print("=" * 50)
            print("Usage:")
            print("  python setup_wallet_ecosystem.py setup    - Create complete wallet ecosystem")
            print("  python setup_wallet_ecosystem.py verify   - Verify current ecosystem status")
            print("  python setup_wallet_ecosystem.py help     - Show this help")
        else:
            print(f"Unknown command: {command}")
            print("Use 'help' for usage information")
            sys.exit(1)
    else:
        # Default to setup
        success = await setup_wallet_ecosystem()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main()) 