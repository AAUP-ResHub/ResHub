"""
API quota management for external services
"""

import os
import json
import time
from datetime import datetime, timedelta
from flask import current_app

class QuotaManager:
    """
    Manages API usage quotas to avoid exceeding rate limits
    
    Tracks API usage and enforces daily limits
    """
    
    def __init__(self, api_name, daily_quota, storage_dir='app/data/quota'):
        """
        Initialize a quota manager for an API
        
        Args:
            api_name: Name of the API (e.g., 'semantic_scholar')
            daily_quota: Maximum number of calls allowed per day
            storage_dir: Directory to store quota usage data
        """
        self.api_name = api_name
        self.daily_quota = daily_quota
        self.storage_dir = storage_dir
        self.usage_file = os.path.join(storage_dir, f'{api_name}_quota.json')
        self.usage_data = self._load_usage_data()
        
        # Create storage directory if it doesn't exist
        os.makedirs(storage_dir, exist_ok=True)
    
    def _load_usage_data(self):
        """Load usage data from file or create default structure"""
        if os.path.exists(self.usage_file):
            try:
                with open(self.usage_file, 'r') as f:
                    data = json.load(f)
                    return data
            except (json.JSONDecodeError, IOError) as e:
                if 'current_app' in globals():
                    current_app.logger.error(f"Error loading quota data: {str(e)}")
                # Fall back to default if file is corrupted
        
        # Default structure with no usage
        today = datetime.now().strftime('%Y-%m-%d')
        return {
            'date': today,
            'usage': 0
        }
    
    def _save_usage_data(self):
        """Save current usage data to file"""
        try:
            with open(self.usage_file, 'w') as f:
                json.dump(self.usage_data, f)
        except IOError as e:
            if 'current_app' in globals():
                current_app.logger.error(f"Error saving quota data: {str(e)}")
            else:
                print(f"Error saving quota data: {str(e)}")
    
    def _reset_if_new_day(self):
        """Reset usage counter if it's a new day"""
        today = datetime.now().strftime('%Y-%m-%d')
        if self.usage_data['date'] != today:
            self.usage_data = {
                'date': today,
                'usage': 0
            }
            self._save_usage_data()
    
    def record_usage(self, count=1):
        """
        Record API usage
        
        Args:
            count: Number of API calls made (default: 1)
        """
        self._reset_if_new_day()
        self.usage_data['usage'] += count
        self._save_usage_data()
        
        # Log if approaching limit
        if self.usage_data['usage'] >= self.daily_quota * 0.8:
            msg = f"{self.api_name} API usage at {self.usage_data['usage']}/{self.daily_quota} ({self.usage_data['usage']/self.daily_quota:.0%})"
            if 'current_app' in globals():
                current_app.logger.warning(msg)
            else:
                print(f"WARNING: {msg}")
    
    def has_quota(self):
        """Check if there's quota remaining for today"""
        self._reset_if_new_day()
        return self.usage_data['usage'] < self.daily_quota
    
    def remaining_quota(self):
        """Get remaining quota for today"""
        self._reset_if_new_day()
        return self.daily_quota - self.usage_data['usage']

# Quota managers will be instantiated in __init__.py
