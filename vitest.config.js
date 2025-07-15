import { defineConfig } from 'vitest/config';
import { resolve } from 'path';

export default defineConfig({
  test: {
    // Use jsdom as the test environment
    environment: 'jsdom',
    
    // Set up global configuration
    globals: true,
    
    // Set up aliases for easier imports in tests
    alias: {
      '@components': resolve(__dirname, 'app/static/js/components'),
      '@services': resolve(__dirname, 'app/static/js/components/services'),
      '@store': resolve(__dirname, 'app/static/js/components/store'),
      '@ui': resolve(__dirname, 'app/static/js/components/ui')
    },
    
    // Configure coverage collection
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['app/static/js/components/**/*.js'],
      exclude: ['app/static/js/components/**/*.test.js']
    },
    
    // Configure retry behavior for flaky tests
    retry: 2,
    
    // Include all files matching the patterns
    include: ['app/static/js/components/**/*.test.js'],
    
    // Setup files to run before each test file
    setupFiles: ['./test/setup.js']
  },
});
