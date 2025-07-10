# 🔑 Circle Payments Engine - Enhanced Wallet Ecosystem

This document describes the enhanced wallet architecture for the Circle Payments Engine, implementing a three-wallet ecosystem that supports both EVM and Solana blockchains.

## 🏗️ Architecture Overview

### Three-Wallet Ecosystem

The enhanced wallet architecture consists of three specialized wallets:

1. **BackendMirror Wallet (EVM)**
   - **Type**: Smart Contract Account (SCA)
   - **Blockchains**: ETH, Polygon, Arbitrum, Base, Optimism, Celo
   - **Purpose**: Main platform operations, user transactions
   - **Features**: Gas Station, account abstraction, complex transactions

2. **Circle Engine Wallet (EVM)**
   - **Type**: Smart Contract Account (SCA)
   - **Blockchains**: ETH, Polygon, Arbitrum, Base, Optimism, Celo
   - **Purpose**: Circle API operations, fee collection
   - **Features**: Circle-specific operations, webhook processing

3. **Solana Wallet (EOA)**
   - **Type**: Externally Owned Account (EOA) - **Required for Solana**
   - **Blockchains**: Solana only
   - **Purpose**: Solana-specific operations, SPL token handling
   - **Features**: ATA auto-creation, native fee sponsorship, SPL token support

## 🚀 Quick Start

### 1. Environment Setup

Copy the environment template and configure your variables:

```bash
cp env.example .env
```

Edit `.env` with your configuration:

```bash
# Circle API Configuration
CIRCLE_API_KEY=your_circle_api_key_here
CIRCLE_ENTITY_SECRET=your_64_character_entity_secret_here

# BackendMirror Integration
BACKENDMIRROR_WALLET_ADDRESS=0x1234567890abcdef1234567890abcdef12345678
SOLANA_WALLET_ADDRESS=your_solana_wallet_address_here

# Database Configuration
DATABASE_URL=postgresql://username:password@localhost/circle_engine
```

### 2. Database Setup

Run the database migrations:

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head
```

### 3. Create Wallet Ecosystem

Use the setup script to create the complete wallet ecosystem:

```bash
# Create complete ecosystem
python scripts/setup_wallet_ecosystem.py setup

# Verify ecosystem status
python scripts/setup_wallet_ecosystem.py verify
```

## 📋 API Endpoints

### Wallet Management

#### Create Comprehensive Wallet Ecosystem
```http
POST /wallets/comprehensive
Content-Type: application/json

{
  "wallet_set_id": "your_wallet_set_id"
}
```

**Response:**
```json
{
  "message": "Comprehensive wallet ecosystem created successfully",
  "wallets": [
    {
      "role": "backendMirror",
      "type": "EVM",
      "accountType": "SCA",
      "wallet": { ... }
    },
    {
      "role": "circleEngine", 
      "type": "EVM",
      "accountType": "SCA",
      "wallet": { ... }
    },
    {
      "role": "solanaOperations",
      "type": "SOLANA", 
      "accountType": "EOA",
      "wallet": { ... }
    }
  ],
  "total_wallets": 3
}
```

#### Create Solana Wallet
```http
POST /wallets/solana
Content-Type: application/json

{
  "wallet_set_id": "your_wallet_set_id",
  "count": 1
}
```

#### Get Wallet by Role
```http
GET /wallets/role/{role}
```

**Roles**: `backendMirror`, `circleEngine`, `solanaOperations`

#### Get Wallets by Type
```http
GET /wallets/type/{wallet_type}
```

**Types**: `EVM`, `SOLANA`

#### Get Ecosystem Status
```http
GET /wallets/ecosystem/status
```

### Balance Management

#### Get EVM Wallet Balance
```http
GET /wallets/{wallet_id}/balance
```

#### Get Solana Wallet Balance
```http
GET /wallets/{wallet_id}/solana-balance
```

### Transaction Management

#### Transfer Tokens (Auto-detect blockchain)
```http
POST /transactions
Content-Type: application/json

{
  "wallet_id": "wallet_id",
  "token_id": "token_id", 
  "destination_address": "destination_address",
  "amount": "amount",
  "blockchain": "SOL"  // Optional: auto-detected if not provided
}
```

#### Transfer Solana Tokens
```http
POST /transactions/solana
Content-Type: application/json

{
  "wallet_id": "solana_wallet_id",
  "token_id": "spl_token_id",
  "destination_address": "solana_address", 
  "amount": "amount"
}
```

#### Get Transaction Confirmation Status
```http
GET /transactions/{tx_id}/confirmation-status?blockchain=SOL
```

### Transaction History

#### Get Transactions by Blockchain
```http
GET /transactions/blockchain/{blockchain}?limit=100
```

## 🔧 Configuration

### Blockchain Confirmation Requirements

| Blockchain | Confirmations | Time |
|------------|---------------|------|
| ETH | 12 | ~3 minutes |
| Polygon | 50 | ~2 minutes |
| Arbitrum | 12 | ~3 minutes |
| Base | 12 | ~3 minutes |
| Optimism | 12 | ~4 minutes |
| Solana | 33 | ~13 seconds |
| Celo | 12 | ~3 minutes |

### Gas Station Support

| Blockchain | Gas Station | Notes |
|------------|-------------|-------|
| ETH | ✅ | SCA required |
| Polygon | ✅ | SCA required |
| Arbitrum | ✅ | SCA required |
| Base | ✅ | SCA required |
| Optimism | ✅ | SCA required |
| Solana | ✅ | Native fee sponsorship |
| Celo | ✅ | SCA required |

## 🎯 Key Features

### 1. Multi-Chain Support
- **EVM Chains**: ETH, Polygon, Arbitrum, Base, Optimism, Celo
- **Solana**: Native SVM support with cross-chain bridging

### 2. Account Type Optimization
- **EVM**: Smart Contract Accounts (SCA) for advanced features
- **Solana**: Externally Owned Accounts (EOA) as required

### 3. Solana-Specific Features
- **ATA Auto-Creation**: Automatic Associated Token Account creation
- **Native Fee Sponsorship**: Built-in fee payer support
- **SPL Token Support**: Full Solana Program Library token support

### 4. Enhanced Transaction Tracking
- **Blockchain-Specific Confirmations**: Proper confirmation requirements per chain
- **Status Tracking**: Real-time transaction status updates
- **Audit Logging**: Comprehensive transaction audit trails

### 5. Role-Based Wallet Management
- **Specialized Roles**: Each wallet has a specific purpose
- **Easy Retrieval**: Get wallets by role or type
- **Ecosystem Monitoring**: Check complete ecosystem status

## 🔍 Monitoring & Debugging

### Ecosystem Status Check
```bash
python scripts/setup_wallet_ecosystem.py verify
```

### API Health Check
```http
GET /wallets/ecosystem/status
```

### Transaction Monitoring
```http
GET /transactions/blockchain/SOL?limit=50
```

## 🚨 Important Notes

### Solana Requirements
1. **EOA Only**: Solana only supports Externally Owned Accounts
2. **ATA Support**: Only Associated Token Accounts are supported
3. **Native Fees**: Solana has native fee sponsorship capabilities

### EVM Requirements
1. **SCA Support**: Smart Contract Accounts enable advanced features
2. **Gas Station**: Requires SCA for fee sponsorship
3. **Account Abstraction**: Full ERC-4337 support

### Security Considerations
1. **IP Whitelisting**: Only Circle's IP addresses are allowed
2. **Signature Verification**: All webhooks are cryptographically verified
3. **Audit Logging**: All operations are logged for compliance

## 🔄 Migration from Legacy

If you're upgrading from the previous two-wallet system:

1. **Backup Current Data**: Export existing wallet and transaction data
2. **Run Migration**: Execute the database migration
3. **Create Solana Wallet**: Use the setup script to add Solana support
4. **Update Configuration**: Add Solana-specific environment variables
5. **Test Integration**: Verify all three wallets work correctly

## 📚 Additional Resources

- [Circle Developer Documentation](https://developers.circle.com/)
- [Solana Wallet Integration](https://developers.circle.com/w3s/programmable-wallets-on-solana)
- [Blockchain Confirmations](https://developers.circle.com/w3s/blockchain-confirmations)
- [Webhook Notifications](https://developers.circle.com/docs/webhooks)

## 🆘 Troubleshooting

### Common Issues

1. **Solana Wallet Creation Fails**
   - Ensure `accountType` is set to "EOA"
   - Verify `blockchains` contains only "SOL"

2. **Transaction Confirmation Issues**
   - Check blockchain-specific confirmation requirements
   - Verify transaction status via Circle API

3. **Webhook Processing Errors**
   - Verify IP whitelist configuration
   - Check signature verification setup

### Support

For issues specific to this implementation, check the logs and audit trails. For Circle API issues, refer to the official Circle documentation. 