/**
 * Main Entry Point for ResHub Chatbot Frontend
 * 
 * Initializes feature flags, checks compatibility, and renders the main App component.
 * This is the single entry point for the new chatbot frontend architecture.
 */

import { App } from './ui/App.js';
import { FeatureFlags } from './services/featureFlags.js';
import { chatStore } from './store/chatStore.js';

// Global app instance
let appInstance = null;

/**
 * Check browser compatibility
 */
function checkCompatibility() {
  const missingFeatures = [];
  
  // Check window features
  const windowFeatures = ['fetch', 'Promise', 'addEventListener', 'JSON'];
  windowFeatures.forEach(feature => {
    if (!(feature in window)) {
      missingFeatures.push(feature);
    }
  });
  
  // Check document features
  if (!document.querySelector) {
    missingFeatures.push('querySelector');
  }
  
  // Check for ES6 module support
  if (typeof Symbol === 'undefined') {
    missingFeatures.push('ES6 Symbol');
  }
  
  if (missingFeatures.length > 0) {
    throw new Error(`Browser missing required features: ${missingFeatures.join(', ')}`);
  }
  
  console.log('Browser compatibility check passed');
}

/**
 * Initialize feature flags
 */
async function initializeFeatureFlags() {
  try {
    await FeatureFlags.initialize();
    
    const flags = FeatureFlags.getAll();
    console.log('Feature flags initialized:', flags);
    
    // Store feature flags in chatStore for components to access
    chatStore.batchUpdate({ featureFlags: flags });
    
    return FeatureFlags;
  } catch (error) {
    console.error('Failed to initialize feature flags:', error);
    // Continue with default flags
    return FeatureFlags;
  }
}

/**
 * Show loading state
 */
function showLoading(container) {
  container.innerHTML = `
    <div class="chatbot-loading text-center py-5">
      <div class="spinner-border text-primary mb-3" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
      <h5>Initializing ResHub AI Assistant...</h5>
      <p class="text-muted">Please wait while we set up your chat environment.</p>
    </div>
  `;
}

/**
 * Show error state
 */
function showError(container, error) {
  container.innerHTML = `
    <div class="chatbot-error text-center py-5">
      <div class="alert alert-danger" role="alert">
        <i class="fas fa-exclamation-triangle fa-2x mb-3"></i>
        <h5>Failed to Load Chat</h5>
        <p class="mb-3">${error.message}</p>
        <button type="button" class="btn btn-primary" onclick="window.location.reload()">
          <i class="fas fa-refresh me-1"></i>Reload Page
        </button>
      </div>
      <details class="mt-3">
        <summary class="text-muted">Technical Details</summary>
        <pre class="text-start mt-2 small">${error.stack || error.message}</pre>
      </details>
    </div>
  `;
}

/**
 * Get configuration from DOM or defaults
 */
function getConfig() {
  const config = {
    showHistory: true,
    layout: 'vertical',
    theme: 'light',
    debug: false
  };
  
  // Try to read config from data attributes or meta tags
  const container = document.getElementById('chatbot-container');
  if (container) {
    config.showHistory = container.dataset.showHistory !== 'false';
    config.layout = container.dataset.layout || config.layout;
    config.theme = container.dataset.theme || config.theme;
    config.debug = container.dataset.debug === 'true';
  }
  
  // Check for debug mode in URL
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('debug') === 'true') {
    config.debug = true;
  }
  
  return config;
}

/**
 * Main initialization function
 */
async function initialize() {
  console.log('Initializing ResHub Chatbot Frontend...');
  
  // Find container element
  const container = document.getElementById('chatbot-container');
  if (!container) {
    console.error('Chatbot container element not found. Please ensure there is an element with id="chatbot-container"');
    return;
  }
  
  try {
    // Show loading state
    showLoading(container);
    
    // Check browser compatibility
    checkCompatibility();
    
    // Get configuration
    const config = getConfig();
    
    if (config.debug) {
      console.log('Debug mode enabled');
      console.log('Configuration:', config);
    }
    
    // Initialize feature flags
    const featureFlags = await initializeFeatureFlags();
    
    // Check if new chatbot is enabled
    const useNewChatbot = featureFlags.isEnabled('new_chatbot_frontend');
    
    if (!useNewChatbot) {
      console.log('New chatbot frontend is disabled by feature flag');
      container.innerHTML = `
        <div class="alert alert-info text-center">
          <i class="fas fa-info-circle me-2"></i>
          The new chatbot interface is currently disabled. 
          Please use the legacy chatbot interface.
        </div>
      `;
      return;
    }
    
    // Initialize user info in store
    chatStore.batchUpdate({
      user: {
        isAuthenticated: true, // Will be validated by first API call
        userId: null // Will be set by API calls
      }
    });
    
    // Create and initialize app
    console.log('Creating App component...');
    appInstance = App(container, config);
    
    console.log('ResHub Chatbot Frontend initialized successfully');
    
    // Global error handler for unhandled promises
    window.addEventListener('unhandledrejection', (event) => {
      console.error('Unhandled promise rejection:', event.reason);
      if (appInstance) {
        appInstance.showError(`Unexpected error: ${event.reason?.message || 'Unknown error'}`);
      }
    });
    
  } catch (error) {
    console.error('Failed to initialize chatbot:', error);
    showError(container, error);
  }
}

/**
 * Cleanup function
 */
function cleanup() {
  console.log('Cleaning up ResHub Chatbot Frontend...');
  
  if (appInstance) {
    appInstance.destroy();
    appInstance = null;
  }
  
  // Clear any intervals or event listeners if needed
  console.log('Chatbot cleanup completed');
}

/**
 * API for external access
 */
window.ResHubChatbot = {
  initialize,
  cleanup,
  getApp: () => appInstance,
  getStore: () => chatStore,
  version: '1.0.0'
};

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initialize);
} else {
  // DOM is already ready
  initialize();
}

// Cleanup on page unload
window.addEventListener('beforeunload', cleanup);

export { initialize, cleanup, appInstance };
