/**
 * Feature Flags Service for ResHub Chatbot
 * 
 * Manages feature flags to toggle new UI components.
 * Provides fallback mechanism if API calls fail.
 */

import { getFeatureFlags as fetchFeatureFlags } from './apiService.js';

class FeatureFlagsService {
  constructor() {
    this.flags = {
      USE_NEW_CHATBOT_UI: true,
      new_chatbot_frontend: true,  // Alias for frontend check
      ENABLE_ADVANCED_SEARCH: false,
      ENABLE_EXPORT_CHAT: false,
      ENABLE_SESSION_MANAGEMENT: true,
      ENABLE_CHAT_HISTORY: true,
      ENABLE_FEEDBACK: true
    };
    this.loaded = false;
    this.loading = false;
  }

  /**
   * Initialize feature flags by fetching from backend
   * @returns {Promise<Object>} Feature flags object
   */
  async initialize() {
    if (this.loading) {
      // Wait for existing request to complete
      while (this.loading) {
        await new Promise(resolve => setTimeout(resolve, 100));
      }
      return this.flags;
    }

    if (this.loaded) {
      return this.flags;
    }

    this.loading = true;

    try {
      console.log('Fetching feature flags from backend...');
      const backendFlags = await fetchFeatureFlags();
      
      // Merge backend flags with defaults
      this.flags = {
        ...this.flags,
        ...backendFlags
      };
      
      this.loaded = true;
      console.log('Feature flags loaded:', this.flags);
      
    } catch (error) {
      console.warn('Failed to load feature flags from backend, using defaults:', error);
      // Keep default flags
    } finally {
      this.loading = false;
    }

    return this.flags;
  }

  /**
   * Check if a feature is enabled
   * @param {string} flagName - Name of the feature flag
   * @returns {boolean} True if feature is enabled
   */
  isEnabled(flagName) {
    if (!this.loaded) {
      console.warn(`Feature flag '${flagName}' checked before initialization. Using default value.`);
    }
    
    return Boolean(this.flags[flagName]);
  }

  /**
   * Get all feature flags
   * @returns {Object} All feature flags
   */
  getAll() {
    return { ...this.flags };
  }

  /**
   * Set a feature flag (for testing/development)
   * @param {string} flagName - Name of the feature flag
   * @param {boolean} value - Flag value
   */
  setFlag(flagName, value) {
    this.flags[flagName] = Boolean(value);
    console.log(`Feature flag '${flagName}' set to:`, value);
  }

  /**
   * Reset flags to defaults (for testing)
   */
  reset() {
    this.flags = {
      USE_NEW_CHATBOT_UI: true,
      new_chatbot_frontend: true,  // Alias for frontend check
      ENABLE_ADVANCED_SEARCH: false,
      ENABLE_EXPORT_CHAT: false,
      ENABLE_SESSION_MANAGEMENT: true,
      ENABLE_CHAT_HISTORY: true,
      ENABLE_FEEDBACK: true
    };
    this.loaded = false;
    this.loading = false;
  }

  /**
   * Check if new chatbot UI should be used
   * @returns {boolean} True if new UI is enabled
   */
  useNewUI() {
    return this.isEnabled('USE_NEW_CHATBOT_UI');
  }

  /**
   * Check if advanced search is enabled
   * @returns {boolean} True if advanced search is enabled
   */
  hasAdvancedSearch() {
    return this.isEnabled('ENABLE_ADVANCED_SEARCH');
  }

  /**
   * Check if chat export is enabled
   * @returns {boolean} True if chat export is enabled
   */
  hasExportChat() {
    return this.isEnabled('ENABLE_EXPORT_CHAT');
  }

  /**
   * Check if session management is enabled
   * @returns {boolean} True if session management is enabled
   */
  hasSessionManagement() {
    return this.isEnabled('ENABLE_SESSION_MANAGEMENT');
  }

  /**
   * Check if chat history is enabled
   * @returns {boolean} True if chat history is enabled
   */
  hasChatHistory() {
    return this.isEnabled('ENABLE_CHAT_HISTORY');
  }

  /**
   * Check if feedback is enabled
   * @returns {boolean} True if feedback is enabled
   */
  hasFeedback() {
    return this.isEnabled('ENABLE_FEEDBACK');
  }
}

// Create singleton instance
export const FeatureFlags = new FeatureFlagsService();

// Export class for testing
export { FeatureFlagsService };

export default FeatureFlags;
