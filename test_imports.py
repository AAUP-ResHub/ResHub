# Simple smoke test for imports
from app.chatbot.api_fetchers import CoreFetcher
from app.chatbot.api_monitoring import track_api_usage
print("CoreFetcher OK:", CoreFetcher)
print("Decorator OK:", track_api_usage)
