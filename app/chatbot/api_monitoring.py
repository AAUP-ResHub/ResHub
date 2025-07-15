"""
API Monitoring Module

This module provides functions for monitoring external API usage,
tracking quotas, and logging rate limit information.
"""

import logging
import time
from datetime import datetime
from flask import current_app
from functools import wraps

def track_api_usage(api_name):
    """
    Decorator to track API usage and log rate limit information.
    
    Args:
        api_name: Name of the API being used
        
    Returns:
        Decorator function that wraps API calls
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get start time
            start_time = time.time()
            
            # Call the original function
            result = func(*args, **kwargs)
            
            # Get end time and calculate duration
            end_time = time.time()
            duration_ms = int((end_time - start_time) * 1000)
            
            # For methods in the CoreFetcher class, check for rate limit info
            if hasattr(args[0], 'last_response_headers') and args[0].last_response_headers:
                # Extract method name
                method_name = func.__name__
                
                # Log API call with rate limit info
                rate_limit_remaining = args[0].last_response_headers.get('X-Rate-Limit-Remaining')
                if rate_limit_remaining is not None:
                    current_app.logger.info(
                        f"{api_name} API call to {method_name} completed in {duration_ms}ms. "
                        f"Remaining quota: {rate_limit_remaining}"
                    )
                else:
                    current_app.logger.info(
                        f"{api_name} API call to {method_name} completed in {duration_ms}ms. "
                        f"No rate limit information available."
                    )
                
                # Check if we're getting low on quota
                if rate_limit_remaining is not None and int(rate_limit_remaining) < 50:
                    current_app.logger.warning(
                        f"{api_name} API quota running low! Only {rate_limit_remaining} requests remaining."
                    )
            else:
                # Basic logging for other API calls
                current_app.logger.info(
                    f"{api_name} API call completed in {duration_ms}ms"
                )
            
            return result
        return wrapper
    return decorator

def log_daily_usage(api_name, usage_stats):
    """
    Log daily API usage statistics.
    
    Args:
        api_name: Name of the API
        usage_stats: Dictionary containing usage statistics
    """
    current_app.logger.info(
        f"Daily {api_name} API usage stats: "
        f"Total requests: {usage_stats.get('total_requests', 0)}, "
        f"Successful requests: {usage_stats.get('successful_requests', 0)}, "
        f"Failed requests: {usage_stats.get('failed_requests', 0)}, "
        f"Average response time: {usage_stats.get('avg_response_time', 0):.2f}ms"
    )

class QuotaManager:
    """Manager class for API quota monitoring and throttling."""
    
    def __init__(self, api_name, daily_limit=None):
        """
        Initialize quota manager.
        
        Args:
            api_name: Name of the API
            daily_limit: Daily request limit (if applicable)
        """
        self.api_name = api_name
        self.daily_limit = daily_limit
        self.daily_usage = 0
        self.last_reset = datetime.now().date()
    
    def get_quota_info(self):
        """
        Get information about current quota usage and limits.
        
        Returns:
            Dictionary with quota information
        """
        # Reset counter if it's a new day
        today = datetime.now().date()
        if today > self.last_reset:
            self.daily_usage = 0
            self.last_reset = today
        
        return {
            "api_name": self.api_name,
            "daily_limit": self.daily_limit if self.daily_limit else 0,
            "usage": self.daily_usage,
            "remaining": (self.daily_limit - self.daily_usage) if self.daily_limit else 0,
            "reset_date": self.last_reset.isoformat()
        }
    
    def check_quota(self):
        """
        Check if there's sufficient quota remaining.
        
        Returns:
            Boolean indicating if there's quota available
        """
        # Reset counter if it's a new day
        today = datetime.now().date()
        if today > self.last_reset:
            self.daily_usage = 0
            self.last_reset = today
            current_app.logger.info(f"{self.api_name} API quota counter reset for new day")
        
        # Check if we're over the daily limit
        if self.daily_limit and self.daily_usage >= self.daily_limit:
            current_app.logger.warning(
                f"{self.api_name} API daily quota exceeded: {self.daily_usage}/{self.daily_limit}"
            )
            return False
        
        return True
    
    def increment_usage(self):
        """Increment the usage counter."""
        self.daily_usage += 1
        
        # Log when hitting certain thresholds
        if self.daily_limit:
            usage_percentage = (self.daily_usage / self.daily_limit) * 100
            if usage_percentage >= 80 and usage_percentage < 90:
                current_app.logger.warning(
                    f"{self.api_name} API usage at 80% of daily quota: {self.daily_usage}/{self.daily_limit}"
                )
            elif usage_percentage >= 90:
                current_app.logger.warning(
                    f"{self.api_name} API usage at 90% of daily quota: {self.daily_usage}/{self.daily_limit}"
                )
        
        return self.daily_usage

# Create quota manager for CORE API
core_quota_manager = QuotaManager(api_name="CORE", daily_limit=10000)  # Set appropriate limit based on your plan
