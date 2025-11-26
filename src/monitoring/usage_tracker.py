"""
API Usage Tracker
Tracks Gemini API usage, costs, and rate limits for free and paid users
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class UsageTracker:
    """Track API usage and costs for Gemini API"""

    # Gemini API pricing (as of 2024)
    PRICING = {
        "free": {
            "requests_per_minute": 15,
            "requests_per_day": 1500,
            "tokens_per_minute": 1_000_000,
            "cost_per_request": 0.0,  # Free tier
        },
        "paid": {
            "flash_input_cost_per_1m_tokens": 0.075,    # $0.075 per 1M input tokens
            "flash_output_cost_per_1m_tokens": 0.30,    # $0.30 per 1M output tokens
            "requests_per_minute": 360,
            "requests_per_day": 10000,
        }
    }

    def __init__(self, storage_path: str = "./usage_data"):
        """
        Initialize usage tracker

        Args:
            storage_path: Directory to store usage data
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.usage_file = self.storage_path / "usage_log.json"

        # Load existing usage data
        self.usage_data = self._load_usage_data()

        logger.info(f"UsageTracker initialized with storage at: {storage_path}")

    def _load_usage_data(self) -> Dict:
        """Load usage data from file"""
        if self.usage_file.exists():
            try:
                with open(self.usage_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load usage data: {e}")
                return self._create_default_usage_data()
        return self._create_default_usage_data()

    def _create_default_usage_data(self) -> Dict:
        """Create default usage data structure"""
        return {
            "total_requests": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost_usd": 0.0,
            "tier": "free",  # or "paid"
            "requests_today": 0,
            "last_reset_date": datetime.now().isoformat(),
            "history": []
        }

    def _save_usage_data(self):
        """Save usage data to file"""
        try:
            with open(self.usage_file, 'w') as f:
                json.dump(self.usage_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save usage data: {e}")

    def _reset_daily_counters_if_needed(self):
        """Reset daily counters if it's a new day"""
        last_reset = datetime.fromisoformat(self.usage_data["last_reset_date"])
        now = datetime.now()

        if now.date() > last_reset.date():
            logger.info("Resetting daily usage counters")
            self.usage_data["requests_today"] = 0
            self.usage_data["last_reset_date"] = now.isoformat()
            self._save_usage_data()

    def track_request(
        self,
        input_tokens: int = 0,
        output_tokens: int = 0,
        model: str = "gemini-2.5-flash",
        file_size_mb: float = 0.0
    ) -> Dict:
        """
        Track a single API request

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model used
            file_size_mb: Size of audio file processed

        Returns:
            Dictionary with usage stats and warnings
        """
        self._reset_daily_counters_if_needed()

        # Update counters
        self.usage_data["total_requests"] += 1
        self.usage_data["requests_today"] += 1
        self.usage_data["total_input_tokens"] += input_tokens
        self.usage_data["total_output_tokens"] += output_tokens

        # Calculate cost
        tier = self.usage_data["tier"]
        cost = 0.0

        if tier == "paid":
            input_cost = (input_tokens / 1_000_000) * self.PRICING["paid"]["flash_input_cost_per_1m_tokens"]
            output_cost = (output_tokens / 1_000_000) * self.PRICING["paid"]["flash_output_cost_per_1m_tokens"]
            cost = input_cost + output_cost
            self.usage_data["total_cost_usd"] += cost

        # Add to history
        self.usage_data["history"].append({
            "timestamp": datetime.now().isoformat(),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost,
            "model": model,
            "file_size_mb": file_size_mb
        })

        # Keep only last 1000 records
        if len(self.usage_data["history"]) > 1000:
            self.usage_data["history"] = self.usage_data["history"][-1000:]

        self._save_usage_data()

        # Check limits and return warnings
        return self._check_limits()

    def _check_limits(self) -> Dict:
        """
        Check if usage is approaching or exceeding limits

        Returns:
            Dictionary with usage stats and warnings
        """
        tier = self.usage_data["tier"]
        limits = self.PRICING[tier]

        requests_today = self.usage_data["requests_today"]
        daily_limit = limits["requests_per_day"]

        # Calculate usage percentage
        daily_usage_pct = (requests_today / daily_limit) * 100

        warnings = []
        status = "ok"

        if daily_usage_pct >= 90:
            status = "critical"
            warnings.append(f"⚠️ CRITICAL: You've used {daily_usage_pct:.1f}% of daily limit!")
        elif daily_usage_pct >= 75:
            status = "warning"
            warnings.append(f"⚠️ WARNING: You've used {daily_usage_pct:.1f}% of daily limit")
        elif daily_usage_pct >= 50:
            status = "caution"
            warnings.append(f"ℹ️ You've used {daily_usage_pct:.1f}% of daily limit")

        return {
            "status": status,
            "tier": tier,
            "requests_today": requests_today,
            "daily_limit": daily_limit,
            "daily_usage_pct": daily_usage_pct,
            "requests_remaining": daily_limit - requests_today,
            "total_cost_usd": self.usage_data["total_cost_usd"],
            "warnings": warnings
        }

    def get_usage_stats(self) -> Dict:
        """Get current usage statistics"""
        self._reset_daily_counters_if_needed()

        return {
            "tier": self.usage_data["tier"],
            "total_requests": self.usage_data["total_requests"],
            "requests_today": self.usage_data["requests_today"],
            "total_input_tokens": self.usage_data["total_input_tokens"],
            "total_output_tokens": self.usage_data["total_output_tokens"],
            "total_cost_usd": self.usage_data["total_cost_usd"],
            "limits": self._check_limits(),
            "last_reset": self.usage_data["last_reset_date"]
        }

    def set_tier(self, tier: str):
        """
        Set API tier (free or paid)

        Args:
            tier: 'free' or 'paid'
        """
        if tier not in ["free", "paid"]:
            raise ValueError("Tier must be 'free' or 'paid'")

        self.usage_data["tier"] = tier
        self._save_usage_data()
        logger.info(f"API tier set to: {tier}")

    def get_burn_rate(self) -> Dict:
        """
        Calculate current burn rate (cost per day)

        Returns:
            Dictionary with burn rate statistics
        """
        if self.usage_data["tier"] == "free":
            return {
                "daily_burn_rate_usd": 0.0,
                "monthly_estimate_usd": 0.0,
                "message": "Free tier - no costs"
            }

        # Calculate burn rate from recent history
        recent_history = self.usage_data["history"][-100:]  # Last 100 requests

        if not recent_history:
            return {
                "daily_burn_rate_usd": 0.0,
                "monthly_estimate_usd": 0.0,
                "message": "No recent usage"
            }

        # Sum costs from today
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_cost = sum(
            record["cost_usd"]
            for record in recent_history
            if datetime.fromisoformat(record["timestamp"]) >= today_start
        )

        # Estimate monthly cost
        monthly_estimate = today_cost * 30

        return {
            "daily_burn_rate_usd": today_cost,
            "monthly_estimate_usd": monthly_estimate,
            "cost_today": today_cost,
            "message": f"Estimated monthly cost: ${monthly_estimate:.2f}"
        }

    def reset_stats(self):
        """Reset all usage statistics (use with caution!)"""
        logger.warning("Resetting all usage statistics")
        self.usage_data = self._create_default_usage_data()
        self._save_usage_data()
