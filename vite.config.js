import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  // Base public path - this will be prepended to asset URLs
  base: '/static/dist/',
  
  // Configure server for development
  server: {
    host: '0.0.0.0', // This is essential to make the server accessible from outside the container
    port: 5173,
    proxy: {
      // Any request from the frontend starting with '/chatbot/api'
      // will be forwarded to the Flask backend
      '/chatbot/api': {
        target: 'http://web:5000', // 'web' is the service name of your Flask app
        changeOrigin: true,
      },
      // Add proxy for other API routes
      '/api': {
        target: 'http://web:5000',
        changeOrigin: true,
      }
    }
  },
  
  // Configure build output
  build: {
    // Output directory (relative to project root)
    outDir: 'app/static/dist',
    
    // Empty the outDir on build
    emptyOutDir: true,
    
    // Generate manifest for Flask to reference assets with hashes
    manifest: true,
    
    // Configure rollup options
    rollupOptions: {
      input: {
        // Main entry point
        main: resolve(__dirname, 'app/static/js/components/index.js'),
      },
      output: {
        // Configure chunk naming pattern
        entryFileNames: 'js/[name]-[hash].js',
        chunkFileNames: 'js/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]'
      }
    }
  },
  
  // Development server options
  server: {
    // Use localhost by default
    host: 'localhost',
    
    // Use port 3000 by default
    port: 3000,
    
    // Configure proxying for API requests
    proxy: {
      '/chatbot/api': {
        target: 'http://localhost:5000',
        changeOrigin: true
      }
    }
  },
  
  // Resolve aliases for easier imports
  resolve: {
    alias: {
      '@components': resolve(__dirname, 'app/static/js/components'),
      '@services': resolve(__dirname, 'app/static/js/components/services'),
      '@store': resolve(__dirname, 'app/static/js/components/store'),
      '@ui': resolve(__dirname, 'app/static/js/components/ui')
    }
  }
});
