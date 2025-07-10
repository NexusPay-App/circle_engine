from app.db.session import SessionLocal
from app.models.wallet import Transaction
from app.utils.audit import log_audit
from app.utils.config import get_blockchain_config, get_circle_api_key
from datetime import datetime
import logging
import httpx
import asyncio

logger = logging.getLogger(__name__)

async def estimate_gas_fees(blockchain: str, transaction_type: str = "transfer", gas_level: str = "MEDIUM"):
    """Estimate gas fees for a specific blockchain and transaction type"""
    try:
        blockchain_config = get_blockchain_config()
        gas_station_support = blockchain_config.get("gas_station_support", {})
        
        if not gas_station_support.get(blockchain, False):
            logger.warning(f"Gas station not supported for blockchain: {blockchain}")
            return {
                "supported": False,
                "message": f"Gas station not supported for {blockchain}"
            }
        
        # Circle Gas Station API endpoint
        api_key = get_circle_api_key()
        base_url = "https://api.circle.com/v1/w3s/gas-station"
        
        # Gas level mapping
        gas_levels = {
            "LOW": "slow",
            "MEDIUM": "standard", 
            "HIGH": "fast"
        }
        
        gas_level_param = gas_levels.get(gas_level, "standard")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}/{blockchain.lower()}/estimate",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                params={
                    "gasLevel": gas_level_param
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                log_audit("gas_fee_estimated", {
                    "blockchain": blockchain,
                    "gas_level": gas_level,
                    "estimated_fee": data.get("data", {}).get("gasEstimate")
                })
                return {
                    "supported": True,
                    "blockchain": blockchain,
                    "gas_level": gas_level,
                    "estimated_fee": data.get("data", {}).get("gasEstimate"),
                    "currency": data.get("data", {}).get("currency"),
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                logger.error(f"Failed to estimate gas fees: {response.status_code} - {response.text}")
                return {
                    "supported": True,
                    "error": f"API error: {response.status_code}",
                    "blockchain": blockchain
                }
                
    except Exception as e:
        logger.error(f"Error estimating gas fees: {str(e)}")
        return {
            "supported": False,
            "error": str(e),
            "blockchain": blockchain
        }

async def sponsor_transaction(transaction_id: str, wallet_id: str, blockchain: str, gas_level: str = "MEDIUM"):
    """Sponsor a transaction using Circle Gas Station"""
    try:
        blockchain_config = get_blockchain_config()
        gas_station_support = blockchain_config.get("gas_station_support", {})
        
        if not gas_station_support.get(blockchain, False):
            logger.warning(f"Gas station not supported for blockchain: {blockchain}")
            return {
                "sponsored": False,
                "message": f"Gas station not supported for {blockchain}"
            }
        
        # Circle Gas Station API endpoint
        api_key = get_circle_api_key()
        base_url = "https://api.circle.com/v1/w3s/gas-station"
        
        # Gas level mapping
        gas_levels = {
            "LOW": "slow",
            "MEDIUM": "standard", 
            "HIGH": "fast"
        }
        
        gas_level_param = gas_levels.get(gas_level, "standard")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/{blockchain.lower()}/sponsor",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "transactionId": transaction_id,
                    "walletId": wallet_id,
                    "gasLevel": gas_level_param
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                sponsorship_id = data.get("data", {}).get("sponsorshipId")
                
                # Update transaction with gas station info
                from .transaction_business import update_transaction_gas_info
                await update_transaction_gas_info(
                    transaction_id, 
                    data.get("data", {}).get("gasEstimate", "0"),
                    "true"
                )
                
                log_audit("transaction_sponsored", {
                    "transaction_id": transaction_id,
                    "wallet_id": wallet_id,
                    "blockchain": blockchain,
                    "sponsorship_id": sponsorship_id,
                    "gas_level": gas_level
                })
                
                return {
                    "sponsored": True,
                    "transaction_id": transaction_id,
                    "sponsorship_id": sponsorship_id,
                    "gas_estimate": data.get("data", {}).get("gasEstimate"),
                    "blockchain": blockchain,
                    "gas_level": gas_level
                }
            else:
                logger.error(f"Failed to sponsor transaction: {response.status_code} - {response.text}")
                return {
                    "sponsored": False,
                    "error": f"API error: {response.status_code}",
                    "transaction_id": transaction_id
                }
                
    except Exception as e:
        logger.error(f"Error sponsoring transaction: {str(e)}")
        return {
            "sponsored": False,
            "error": str(e),
            "transaction_id": transaction_id
        }

async def get_gas_station_status(blockchain: str = None):
    """Get gas station status for supported blockchains"""
    try:
        blockchain_config = get_blockchain_config()
        gas_station_support = blockchain_config.get("gas_station_support", {})
        
        if blockchain:
            # Check specific blockchain
            supported = gas_station_support.get(blockchain, False)
            return {
                "blockchain": blockchain,
                "supported": supported,
                "status": "active" if supported else "not_supported"
            }
        else:
            # Check all blockchains
            status = {}
            for chain, supported in gas_station_support.items():
                status[chain] = {
                    "supported": supported,
                    "status": "active" if supported else "not_supported"
                }
            
            return {
                "all_blockchains": status,
                "supported_count": sum(1 for s in gas_station_support.values() if s),
                "total_count": len(gas_station_support)
            }
            
    except Exception as e:
        logger.error(f"Error getting gas station status: {str(e)}")
        return {"error": str(e)}

async def get_gas_station_usage_statistics(days: int = 30):
    """Get gas station usage statistics"""
    db = SessionLocal()
    try:
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get transactions that used gas station
        gas_station_transactions = db.query(Transaction).filter(
            Transaction.gas_station_used == "true",
            Transaction.created_at >= cutoff_date
        ).all()
        
        stats = {
            "total_sponsored_transactions": len(gas_station_transactions),
            "blockchain_breakdown": {},
            "gas_fee_totals": {},
            "daily_usage": {}
        }
        
        total_gas_fees = 0
        
        for tx in gas_station_transactions:
            # Blockchain breakdown
            blockchain = tx.blockchain or "unknown"
            if blockchain not in stats["blockchain_breakdown"]:
                stats["blockchain_breakdown"][blockchain] = 0
            stats["blockchain_breakdown"][blockchain] += 1
            
            # Gas fee totals
            if blockchain not in stats["gas_fee_totals"]:
                stats["gas_fee_totals"][blockchain] = 0
            
            try:
                gas_fee = float(tx.gas_fee or 0)
                stats["gas_fee_totals"][blockchain] += gas_fee
                total_gas_fees += gas_fee
            except (ValueError, TypeError):
                logger.warning(f"Invalid gas fee: {tx.gas_fee}")
            
            # Daily usage
            date_str = tx.created_at.strftime("%Y-%m-%d")
            if date_str not in stats["daily_usage"]:
                stats["daily_usage"][date_str] = 0
            stats["daily_usage"][date_str] += 1
        
        stats["total_gas_fees"] = total_gas_fees
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting gas station usage statistics: {str(e)}")
        return {}
    finally:
        db.close()

async def monitor_gas_station_health():
    """Monitor gas station health across all supported blockchains"""
    try:
        blockchain_config = get_blockchain_config()
        gas_station_support = blockchain_config.get("gas_station_support", {})
        
        health_status = {}
        
        for blockchain, supported in gas_station_support.items():
            if supported:
                try:
                    # Test gas estimation
                    estimate_result = await estimate_gas_fees(blockchain, "transfer", "MEDIUM")
                    
                    health_status[blockchain] = {
                        "status": "healthy" if estimate_result.get("supported") else "unhealthy",
                        "gas_estimation_working": estimate_result.get("supported", False),
                        "last_check": datetime.utcnow().isoformat(),
                        "error": estimate_result.get("error") if not estimate_result.get("supported") else None
                    }
                    
                    # Add delay to avoid rate limiting
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    health_status[blockchain] = {
                        "status": "error",
                        "gas_estimation_working": False,
                        "last_check": datetime.utcnow().isoformat(),
                        "error": str(e)
                    }
            else:
                health_status[blockchain] = {
                    "status": "not_supported",
                    "gas_estimation_working": False,
                    "last_check": datetime.utcnow().isoformat()
                }
        
        # Overall health status
        healthy_count = sum(1 for status in health_status.values() if status["status"] == "healthy")
        total_supported = sum(1 for supported in gas_station_support.values() if supported)
        
        overall_health = {
            "overall_status": "healthy" if healthy_count == total_supported else "degraded",
            "healthy_blockchains": healthy_count,
            "total_supported": total_supported,
            "health_percentage": (healthy_count / total_supported * 100) if total_supported > 0 else 0,
            "blockchain_status": health_status,
            "last_check": datetime.utcnow().isoformat()
        }
        
        log_audit("gas_station_health_check", overall_health)
        
        return overall_health
        
    except Exception as e:
        logger.error(f"Error monitoring gas station health: {str(e)}")
        return {"error": str(e)}

async def optimize_gas_fees(blockchain: str, transaction_type: str = "transfer"):
    """Get optimal gas fee recommendations"""
    try:
        # Get estimates for all gas levels
        gas_levels = ["LOW", "MEDIUM", "HIGH"]
        estimates = {}
        
        for level in gas_levels:
            estimate = await estimate_gas_fees(blockchain, transaction_type, level)
            if estimate.get("supported"):
                estimates[level] = estimate.get("estimated_fee", "0")
        
        if not estimates:
            return {
                "optimization_available": False,
                "message": "No gas estimates available"
            }
        
        # Find optimal recommendation
        try:
            low_fee = float(estimates.get("LOW", "0"))
            medium_fee = float(estimates.get("MEDIUM", "0"))
            high_fee = float(estimates.get("HIGH", "0"))
            
            # Simple optimization logic
            if low_fee > 0 and medium_fee > 0:
                if medium_fee <= low_fee * 1.2:  # Medium is only 20% more expensive
                    recommendation = "MEDIUM"
                    reason = "Medium priority offers good balance of speed and cost"
                else:
                    recommendation = "LOW"
                    reason = "Low priority offers significant cost savings"
            else:
                recommendation = "MEDIUM"
                reason = "Default recommendation"
            
            return {
                "optimization_available": True,
                "blockchain": blockchain,
                "transaction_type": transaction_type,
                "estimates": estimates,
                "recommendation": recommendation,
                "reason": reason,
                "cost_savings": {
                    "low_vs_medium": f"{((medium_fee - low_fee) / medium_fee * 100):.1f}%" if medium_fee > 0 else "N/A",
                    "low_vs_high": f"{((high_fee - low_fee) / high_fee * 100):.1f}%" if high_fee > 0 else "N/A"
                }
            }
            
        except (ValueError, TypeError):
            return {
                "optimization_available": False,
                "message": "Unable to calculate optimization due to invalid fee data",
                "estimates": estimates
            }
            
    except Exception as e:
        logger.error(f"Error optimizing gas fees: {str(e)}")
        return {"error": str(e)} 