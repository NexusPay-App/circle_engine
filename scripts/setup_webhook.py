# scripts/setup_webhook.py

import httpx
import asyncio
from app.utils.config import get_circle_api_key

async def setup_circle_webhook():
    """
    Setup webhook subscription with Circle
    """
    api_key = get_circle_api_key()
    webhook_url = "https://your-domain.com/webhook"  # Your public webhook URL
    
    async with httpx.AsyncClient() as client:
        # Create webhook subscription
        response = await client.post(
            "https://api.circle.com/v2/notifications/subscriptions",
            headers={
                "accept": "application/json",
                "authorization": f"Bearer {api_key}",
                "content-type": "application/json"
            },
                 "url": webhook_url,
                "events": [
                    "transactions.inbound",
                    "transactions.outbound", 
                    "challenges.initialize",
                    "webhooks.test"
                ]
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"Webhook subscription created: {data['data']['id']}")
            return data['data']['id']
        else:
            print(f"Failed to create webhook subscription: {response.status_code}")
            print(response.text)
            return None

if __name__ == "__main__":
    asyncio.run(setup_circle_webhook())