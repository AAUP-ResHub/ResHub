/**
 * Test Setup for ResHub Frontend Components
 * 
 * This file runs before each test to set up the testing environment.
 */

// Mock localStorage
const localStorageMock = (() => {
  let store = {};
  
  return {
    getItem: (key) => store[key] || null,
    setItem: (key, value) => {
      store[key] = value.toString();
    },
    removeItem: (key) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    }
  };
})();

// Set up globals used in tests
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
});

// Mock the fetch API for testing
global.fetch = vi.fn();

// Reset mocks before each test
beforeEach(() => {
  vi.resetAllMocks();
  window.localStorage.clear();
});
