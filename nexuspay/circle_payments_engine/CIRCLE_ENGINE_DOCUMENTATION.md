# Circle Payments Engine Documentation

This document provides a comprehensive overview of the Circle Payments Engine integration for the NexusPay backend system.

## Features

The Circle Payments Engine includes the following core features:

1. **Developer-Controlled Wallets** – Custodial wallets for each user/business, managed by the platform.
2. **USDC On-Ramp/Off-Ramp** – Mint (fiat to USDC) and redeem (USDC to fiat) using Circle Mint API.
3. **Virtual Cards** – Issue and manage virtual cards for users (requires developer-controlled wallets).
4. **On-Chain Transfers** – Move USDC between wallets and blockchain addresses (Solana, Ethereum, Polygon, etc.).
5. **Transaction Status Tracking** – Comprehensive API for tracking transaction status with detailed information.
6. **Webhook Handling** – Receive and process Circle webhooks for all relevant events (mints, redeems, cards, transfers).
7. **Audit Logging & Reconciliation** – Track all operations for compliance and troubleshooting.
8. **Notifications** – Notify the main backendMirror of relevant events and status changes.
9. **Database Integration** – Store all Circle objects and transaction records for audit and business logic.

## Architecture

The Circle Payments Engine follows a modular, service-oriented architecture with the following components:

### API Layer
- **FastAPI App** – Main entry point for all REST endpoints.
- **Routes** – Define endpoints for wallets, mints, redeems, cards, transfers, webhooks, and health checks.
- **Middleware** – Handles authentication, rate limiting, and request validation.

### Business Logic
- **Wallet Service** – Manages creation and retrieval of developer-controlled wallets.
- **Mint/Redeem Service** – Handles minting (fiat to USDC) and redeeming (USDC to fiat) operations.
- **Card Service** – Issues and manages virtual cards for users.
- **Transfer Service** – Handles on-chain and off-chain USDC transfers.
- **Webhook Service** – Processes incoming webhooks from Circle and updates the database.
- **Audit & Notification Services** – Logs all critical events and notifies backendMirror of status changes.

### Circle SDK Integration
- **Circle Python SDK** – Used for all API calls to Circle Mint (wallets, mints, redeems, cards, transfers, webhooks).

### Data Layer
- **PostgreSQL** – Stores all Circle objects (wallets, mints, redeems, cards, transfers, audit logs, webhook DLQ).
- **SQLAlchemy Models** – ORM models for all entities.
- **Alembic Migrations** – Database schema migrations.

### Supporting Services
- **Audit Logging** – Tracks all operations for compliance and troubleshooting.
- **Notification Service** – Notifies backendMirror of relevant events.
- **Reconciliation Service** – Periodically checks and updates transaction statuses.

## Transaction Flows

### Mint Flow (Fiat to USDC)
1. User initiates a deposit via the `/mint` endpoint (called by backendMirror).
2. System checks available USD balance in the Circle treasury account.
3. Circle Mint API is called to mint USDC to the user's wallet.
4. Circle mints USDC and credits the wallet.
5. Webhook is received for mint completion; status is updated in the database.
6. Notification is sent to backendMirror.

### Redeem Flow (USDC to Fiat)
1. User initiates a withdrawal via the `/redeem` endpoint (called by backendMirror).
2. System checks available USDC balance in the user's wallet.
3. Circle Redeem API is called to redeem USDC for USD to the linked bank account.
4. Circle burns USDC and wires USD to the bank account.
5. Webhook is received for redeem completion; status is updated in the database.
6. Notification is sent to backendMirror.

### Virtual Card Flow
1. User requests a virtual card via the `/cards` endpoint.
2. System ensures the user has a developer-controlled wallet.
3. Circle Cards API is called to issue a virtual card.
4. Card details are stored in the database.
5. Webhook is received for card status updates; status is updated in the database.
6. Notification is sent to backendMirror.

### On-Chain Transfer Flow
1. User initiates a USDC transfer via the `/transfers` endpoint.
2. System checks available USDC balance in the source wallet.
3. Circle Transfers API is called to move USDC to the destination address (on-chain or off-chain).
4. Webhook is received for transfer completion; status is updated in the database.
5. Notification is sent to backendMirror.

## Retry & Reconciliation Mechanisms

- **Webhook Retry** – Failed webhook processing is retried with exponential backoff. If all retries fail, the event is stored in a dead-letter queue (DLQ) for manual review.
- **Reconciliation** – Periodic jobs check for transactions with incomplete status and resync with Circle via the SDK.

## API Endpoints

### Wallets
- **POST** `/wallets` – Create a developer-controlled wallet for a user.
- **GET** `/wallets/{wallet_id}` – Retrieve wallet details.
- **POST** `/wallets/address` – Create a blockchain address for a wallet.

### Mint
- **POST** `/mint` – Mint USDC to a wallet (fiat to USDC on-chain).
- **GET** `/mints/{mint_id}` – Get mint status/details.

### Redeem
- **POST** `/redeem` – Redeem USDC from a wallet (USDC to fiat).
- **GET** `/redeems/{redeem_id}` – Get redeem status/details.

### Virtual Cards
- **POST** `/cards` – Issue a virtual card for a user.
- **GET** `/cards/{card_id}` – Get card details/status.

### Transfers
- **POST** `/transfers` – Transfer USDC between wallets or to blockchain addresses.
- **GET** `/transfers/{transfer_id}` – Get transfer status/details.

### Webhooks
- **POST** `/webhook` – Receive and process webhooks from Circle (mints, redeems, cards, transfers).

### Health Check
- **GET** `/health` – Service health check endpoint.

## Webhooks

The engine exposes a `/webhook` endpoint to receive event notifications from Circle. Supported event types include:
- **mint.completed** – Mint operation completed.
- **redeem.completed** – Redeem operation completed.
- **card.created**, **card.updated** – Card issued or status changed.
- **transfer.completed** – Transfer operation completed.

Webhook events are validated for authenticity using Circle's signature. Failed events are retried; persistent failures are stored in a dead-letter queue.

## Error Handling

All operations include comprehensive error handling:

1. **Input Validation** – All inputs are validated before processing.
2. **Transaction Tracking** – All transactions are tracked, even if they fail.
3. **Retry Mechanism** – Failed webhook events are retried and stored in DLQ if necessary.
4. **Error Codes** – All errors are returned with appropriate error codes and messages.
5. **Audit Logging** – All critical events and errors are logged for compliance and troubleshooting.

## Testing

To test the Circle Payments Engine:

1. Use the FastAPI `/docs` endpoint for interactive API testing.
2. Use Circle's sandbox environment for safe payment/card testing.
3. Trigger webhook events using Circle's test tools or by simulating events.
4. Check the database for transaction and card records.

## Transaction Status Codes

- **pending**: Transaction has been initiated but not yet completed.
- **processing**: Transaction is being processed by Circle.
- **completed**: Transaction has been successfully completed.
- **failed**: Transaction has failed and may be retried or require manual intervention.

## Best Practices

1. Always check transaction status after initiating a transaction.
2. Handle webhook callbacks properly with immediate acknowledgment.
3. Properly validate all inputs to avoid transaction failures.
4. Use the database to track all transactions and card operations.
5. Check both Circle status and local status for complete transaction information.
6. Regularly reconcile transaction statuses with Circle for accuracy.
7. Secure all endpoints with authentication and rate limiting.
8. Store all sensitive keys and credentials securely (never in code).

## Developer Notes

- All Circle API calls should use the official Python SDK for reliability and future-proofing.
- The engine is designed to be called by the main backendMirror for all Circle-related operations.
- All webhook events should be processed idempotently to avoid duplicate processing.
- The engine is extensible for future features (e.g., CCTP, additional chains, new card products).

## References

- [Circle Mint API Overview](https://developers.circle.com/docs/mint)
- [Python SDK](https://github.com/circlefin/python-circle-sdk)
- [Mint USDC](https://developers.circle.com/reference/create-mint)
- [Redeem USDC](https://developers.circle.com/reference/create-redeem)
- [Cards API](https://developers.circle.com/docs/issuing)
- [Transfers API](https://developers.circle.com/reference/createtransfer)
- [Webhooks](https://developers.circle.com/docs/webhooks) 