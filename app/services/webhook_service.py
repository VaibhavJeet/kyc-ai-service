"""
TrustVault Webhook Delivery Service
Handles webhook event delivery with retry logic
"""

import json
import hmac
import hashlib
import asyncio
import structlog
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
import aiohttp
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.webhook import Webhook, WebhookEvent

logger = structlog.get_logger(__name__)


class WebhookEventType(str, Enum):
    """Available webhook event types"""
    VERIFICATION_STARTED = "verification.started"
    VERIFICATION_COMPLETED = "verification.completed"
    VERIFICATION_FAILED = "verification.failed"
    VERIFICATION_MANUAL_REVIEW = "verification.manual_review"
    TRUST_SCORE_CALCULATED = "trust_score.calculated"
    BUSINESS_VERIFIED = "business.verified"
    BUSINESS_FLAGGED = "business.flagged"
    SCAM_DETECTED = "scam.detected"
    ALERT_TRIGGERED = "alert.triggered"


class WebhookDeliveryStatus(str, Enum):
    """Webhook delivery status"""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


class WebhookService:
    """
    Service for delivering webhook events to subscribers.

    Features:
    - Async delivery with retry logic
    - HMAC signature verification
    - Exponential backoff
    - Dead letter queue
    """

    def __init__(self, db: Session = None):
        self.db = db
        self.settings = get_settings()
        self.max_retries = self.settings.webhook_retry_count
        self.timeout = self.settings.webhook_timeout
        self.retry_delays = [60, 300, 900]  # 1min, 5min, 15min

    def generate_signature(self, payload: str, secret: str) -> str:
        """
        Generate HMAC-SHA256 signature for webhook payload.

        Args:
            payload: JSON payload string
            secret: Webhook secret key

        Returns:
            Hex-encoded signature
        """
        return hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def verify_signature(self, payload: str, signature: str, secret: str) -> bool:
        """
        Verify webhook signature.

        Args:
            payload: JSON payload string
            signature: Provided signature
            secret: Webhook secret key

        Returns:
            True if signature is valid
        """
        expected = self.generate_signature(payload, secret)
        return hmac.compare_digest(expected, signature)

    async def create_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        tenant_id: str,
        verification_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Create a webhook event and queue it for delivery.

        Args:
            event_type: Type of event (e.g., "verification.completed")
            data: Event payload data
            tenant_id: Tenant ID
            verification_id: Associated verification ID (optional)

        Returns:
            Event ID if created, None if no webhooks configured
        """
        if not self.db:
            logger.warning("webhook.no_db", message="Database not available")
            return None

        # Find active webhooks for this tenant and event type
        webhooks = self.db.query(Webhook).filter(
            Webhook.tenant_id == tenant_id,
            Webhook.is_active == True,
        ).all()

        # Filter webhooks that subscribe to this event type
        matching_webhooks = [
            w for w in webhooks
            if event_type in (w.events or []) or "*" in (w.events or [])
        ]

        if not matching_webhooks:
            logger.debug("webhook.no_subscribers", event_type=event_type)
            return None

        # Create event record
        event = WebhookEvent(
            tenant_id=tenant_id,
            event_type=event_type,
            payload=data,
            verification_id=verification_id,
        )
        self.db.add(event)
        self.db.commit()

        # Queue delivery for each webhook
        for webhook in matching_webhooks:
            asyncio.create_task(
                self.deliver_event(event.id, webhook.id)
            )

        logger.info(
            "webhook.event_created",
            event_id=event.id,
            event_type=event_type,
            webhook_count=len(matching_webhooks)
        )

        return event.id

    async def deliver_event(
        self,
        event_id: str,
        webhook_id: str,
        attempt: int = 1,
    ) -> bool:
        """
        Deliver a webhook event to a specific endpoint.

        Args:
            event_id: Event ID
            webhook_id: Webhook configuration ID
            attempt: Current attempt number

        Returns:
            True if delivered successfully
        """
        if not self.db:
            return False

        # Get event and webhook
        event = self.db.query(WebhookEvent).filter(
            WebhookEvent.id == event_id
        ).first()
        webhook = self.db.query(Webhook).filter(
            Webhook.id == webhook_id
        ).first()

        if not event or not webhook:
            logger.error("webhook.not_found", event_id=event_id, webhook_id=webhook_id)
            return False

        # Prepare payload
        payload = {
            "id": event.id,
            "type": event.event_type,
            "created_at": event.created_at.isoformat(),
            "data": event.payload,
        }
        payload_json = json.dumps(payload, default=str)

        # Generate signature
        signature = self.generate_signature(
            payload_json,
            webhook.secret or self.settings.api_key
        )

        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "X-TrustVault-Signature": signature,
            "X-TrustVault-Event": event.event_type,
            "X-TrustVault-Delivery": event.id,
            "X-TrustVault-Attempt": str(attempt),
            "User-Agent": "TrustVault-Webhook/1.0",
        }

        # Deliver
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook.url,
                    data=payload_json,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    status_code = response.status
                    response_body = await response.text()

                    # Update event
                    event.last_attempt_at = datetime.utcnow()
                    event.attempts = attempt
                    event.last_response_code = status_code
                    event.last_response_body = response_body[:1000]  # Truncate

                    if 200 <= status_code < 300:
                        event.status = WebhookDeliveryStatus.DELIVERED.value
                        event.delivered_at = datetime.utcnow()
                        self.db.commit()

                        logger.info(
                            "webhook.delivered",
                            event_id=event_id,
                            webhook_url=webhook.url,
                            status_code=status_code
                        )
                        return True
                    else:
                        raise Exception(f"HTTP {status_code}: {response_body[:200]}")

        except Exception as e:
            logger.warning(
                "webhook.delivery_failed",
                event_id=event_id,
                webhook_url=webhook.url,
                attempt=attempt,
                error=str(e)
            )

            event.last_error = str(e)[:500]
            event.attempts = attempt

            # Retry logic
            if attempt < self.max_retries:
                event.status = WebhookDeliveryStatus.RETRYING.value
                self.db.commit()

                # Schedule retry with exponential backoff
                delay = self.retry_delays[min(attempt - 1, len(self.retry_delays) - 1)]
                await asyncio.sleep(delay)
                return await self.deliver_event(event_id, webhook_id, attempt + 1)
            else:
                event.status = WebhookDeliveryStatus.FAILED.value
                self.db.commit()

                logger.error(
                    "webhook.delivery_exhausted",
                    event_id=event_id,
                    webhook_url=webhook.url,
                    attempts=attempt
                )
                return False

    async def send_test_event(self, webhook_id: str) -> Dict[str, Any]:
        """
        Send a test event to verify webhook configuration.

        Args:
            webhook_id: Webhook ID to test

        Returns:
            Test result with status and response
        """
        if not self.db:
            return {"success": False, "error": "Database not available"}

        webhook = self.db.query(Webhook).filter(
            Webhook.id == webhook_id
        ).first()

        if not webhook:
            return {"success": False, "error": "Webhook not found"}

        # Create test payload
        payload = {
            "id": "test_event",
            "type": "webhook.test",
            "created_at": datetime.utcnow().isoformat(),
            "data": {
                "message": "This is a test event from TrustVault",
                "webhook_id": webhook_id,
            },
        }
        payload_json = json.dumps(payload, default=str)

        signature = self.generate_signature(
            payload_json,
            webhook.secret or self.settings.api_key
        )

        headers = {
            "Content-Type": "application/json",
            "X-TrustVault-Signature": signature,
            "X-TrustVault-Event": "webhook.test",
            "X-TrustVault-Delivery": "test",
            "User-Agent": "TrustVault-Webhook/1.0",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook.url,
                    data=payload_json,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    status_code = response.status
                    response_body = await response.text()

                    return {
                        "success": 200 <= status_code < 300,
                        "status_code": status_code,
                        "response": response_body[:500],
                    }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    async def get_event_status(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a webhook event"""
        if not self.db:
            return None

        event = self.db.query(WebhookEvent).filter(
            WebhookEvent.id == event_id
        ).first()

        if not event:
            return None

        return {
            "id": event.id,
            "type": event.event_type,
            "status": event.status,
            "attempts": event.attempts,
            "created_at": event.created_at.isoformat() if event.created_at else None,
            "delivered_at": event.delivered_at.isoformat() if event.delivered_at else None,
            "last_error": event.last_error,
        }


# Singleton
_webhook_service: Optional[WebhookService] = None


def get_webhook_service(db: Session = None) -> WebhookService:
    """Get webhook service instance"""
    global _webhook_service
    if _webhook_service is None or db is not None:
        _webhook_service = WebhookService(db)
    return _webhook_service
