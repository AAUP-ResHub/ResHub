# ResHub Chatbot Frontend Manual Test Guide

## Overview
This document provides a structured approach to diagnose chatbot frontend issues where the UI shows no answer after submitting research questions, despite API calls working directly.

## Pre-requisites
- Docker environment with ResHub containers running
- Browser with Developer Tools (Chrome/Firefox/Edge)
- Access to the project codebase

## Test Matrix

| Test Category | Description | Expected Result | Observed Result |
|---------------|-------------|-----------------|-----------------|
| **Template Structure** | Check template inheritance | Scripts loaded in correct order | |
| **Static Files** | JS/CSS file loading | All assets load with 200 response | |
| **Form Elements** | Chatbot form exists | `#chatForm` exists in DOM | |
| **Event Handlers** | Form submit handlers | Events trigger & log to console | |
| **API Communication** | XHR requests & responses | Successful API calls with responses | |
| **Authentication** | Login status & redirection | Proper auth handling | |
| **Docker Cache** | Updated file serving | Latest file versions served | |

## Step-by-Step Diagnostics

### 1. Browser Environment Tests

#### 1.1. Hard Refresh Test
1. Open `http://localhost:5000/chatbot/public` in a private/incognito window
2. Perform a hard refresh (Ctrl+Shift+R or Command+Shift+R)
3. Open Developer Tools (F12) and go to the Console tab
4. **Expected:** Console should show `Chatbot.js loaded successfully!` message
5. **Observed:** ____________________

#### 1.2. DOM Structure Verification
1. In Developer Tools, run this command in Console:
```javascript
document.getElementById('chatForm') ? 
  console.log('✓ chatForm found') : 
  console.log('✗ chatForm NOT found');
```
2. **Expected:** `✓ chatForm found` message
3. **Observed:** ____________________

#### 1.3. Script Loading Check
1. In Network tab, filter by "JS"
2. Check if `chatbot.js` is loaded (Status 200)
3. Run this command in Console:
```javascript
Array.from(document.scripts).map(s => s.src).filter(s => s.includes('chatbot')).length ?
  console.log('✓ chatbot.js script tag found') :
  console.log('✗ chatbot.js script tag NOT found');
```
4. **Expected:** `✓ chatbot.js script tag found` message
5. **Observed:** ____________________

#### 1.4. Event Handler Registration
1. Run this command in Console:
```javascript
const form = document.getElementById('chatForm');
form.onsubmit ? 
  console.log('✓ onsubmit handler registered') : 
  console.log('✗ NO onsubmit handler');

form._events && form._events.submit ? 
  console.log('✓ addEventListener submit registered') : 
  console.log('⚠️ No addEventListener handlers visible');
```
2. **Expected:** Both handlers should be registered
3. **Observed:** ____________________

### 2. API Communication Tests

#### 2.1. Manual Fetch Request
1. Run this command in Console:
```javascript
fetch('/chatbot/api/chat/test', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ prompt: 'What is machine learning?' })
})
.then(res => res.json())
.then(data => console.log('API Response:', data))
.catch(err => console.error('API Error:', err));
```
2. **Expected:** Response object with answer field in console
3. **Observed:** ____________________

#### 2.2. Network Request Analysis
1. Enter a question in the chatbot form and submit
2. In Network tab, look for POST request to `/chatbot/api/chat/test`
3. Check:
   - Request payload (should have `prompt` field)
   - Response status (should be 200)
   - Response body (should have `answer` field)
4. **Expected:** Complete request cycle with valid JSON response
5. **Observed:** ____________________

### 3. Template Structure Tests

#### 3.1. Block Structure Verification
1. View page source (right-click > View Page Source)
2. Search for `{% block scripts_extra %}` and `{% endblock %}`
3. Check if `chatbot.js` script tag is inside this block
4. **Expected:** `<script src="/static/js/chatbot.js"></script>` inside the scripts_extra block
5. **Observed:** ____________________

### 4. Docker Cache Tests

#### 4.1. Static File Freshness Check
1. Run this command to get file modification time in container:
```shell
docker-compose exec web ls -la /app/app/static/js/chatbot.js
```
2. **Expected:** File date should match latest modifications
3. **Observed:** ____________________

#### 4.2. Cache Headers Check
1. In Network tab, select the chatbot.js file
2. Examine the Response Headers
3. Check for cache-related headers: `Cache-Control`, `ETag`, etc.
4. **Expected:** No aggressive caching headers that would prevent reload
5. **Observed:** ____________________

### 5. Flask Route Configuration Tests

#### 5.1. Route Registration Check
1. Run this command to view registered routes:
```shell
docker-compose exec web flask routes | grep chat
```
2. **Expected:** Should see `/chatbot/api/chat/test` endpoint registered
3. **Observed:** ____________________

### 6. Authentication Flow Tests

#### 6.1. Authentication Status Check
1. Run this command in Console:
```javascript
fetch('/api/auth/status')
  .then(res => res.json())
  .then(data => console.log('Auth Status:', data))
  .catch(err => console.error('Auth Error:', err));
```
2. **Expected:** Response showing login status
3. **Observed:** ____________________

#### 6.2. Public Route Access Check
1. Open `http://localhost:5000/chatbot/public` in a private/incognito window
2. Check if redirected to login page or chatbot interface loads
3. **Expected:** Chatbot interface loads without login
4. **Observed:** ____________________

## Troubleshooting Matrix

| Symptom | Potential Causes | Validation Steps |
|---------|------------------|-----------------|
| No `Chatbot.js loaded successfully!` in console | Script not loading | Check Network tab for 404 errors |
| | Script loaded but has error | Look for red error messages in console |
| `chatForm` not found in DOM | Template rendering issue | View page source for form HTML |
| | JavaScript DOM manipulation issue | Check for JS errors in console |
| Form submits but no XHR request | Event handler not registered | Verify form has proper event listeners |
| | JavaScript error before fetch | Look for errors at form submit time |
| XHR request fires but no response | Incorrect endpoint URL | Check Network tab for 404 errors |
| | Server error processing request | Check for 500 errors or error response |
| Response received but UI not updated | UI update code error | Check for JS errors after fetch completes |
| | DOM element for answer not found | Verify answer containers exist |
| Authentication redirects | Login required for endpoint | Confirm route decorators match expectations |

## Next Steps After Testing

1. Document all observations in the "Observed Results" column
2. Compare expected vs. observed results to identify discrepancies
3. Reference the Troubleshooting Matrix to determine likely causes
4. Prioritize issues based on their impact on the chatbot functionality

## Session-List Bug Tests

### Issue Description
Regular users experience a "Failed to load sessions" error toast when first accessing the chatbot interface, accompanied by a JavaScript error: `TypeError: Cannot read properties of null (reading 'parentNode')`. After submitting a research question, the sessions list suddenly appears and becomes clickable.

### Test Procedure

#### 1. Authentication Testing

**Steps:**
1. Clear browser cache and cookies
2. Open the chatbot interface in three different scenarios:
   - As a regular user (standard login)
   - As an admin user (admin@reshub.org / Admin123!)
   - In an incognito/private window using regular credentials

**Check Points:**
- Does the error appear in all three scenarios?
- Is the error timing consistent across multiple refreshes?
- Record the Console output in each scenario

**Questions to Answer:**
- Is the issue user-role specific?
- Does the error persist after multiple refreshes with the same user?

#### 2. Console & Error Analysis

**Steps:**
1. Before submitting any questions, open the Console and run these commands:
   ```javascript
   // Check if the sessions container exists
   console.log(document.getElementById('session-list'));
   
   // Check if the chat history elements exist
   console.log(document.querySelectorAll('.chat-history-item'));
   
   // Inspect the JavaScript event binding
   console.log(document.querySelectorAll('.chat-history-item').forEach(item => {
     console.log('Item:', item);
     console.log('Has parent:', item.parentNode !== null);
   }));
   ```

2. Record the precise line causing the error (around line 690)
3. Check if the error occurs at page load or during a specific user interaction

**Questions to Answer:**
- Which DOM element is null when it shouldn't be?
- Is the error related to initial rendering or dynamic content updates?
- Does the Console show any errors related to AJAX/fetch requests before the error?

#### 3. Network Request Analysis

**Steps:**
1. Open the Network tab in Developer Tools
2. Filter for XHR/fetch requests
3. Look for calls to `/chatbot/api/chat/history` or similar endpoints
4. Note the following details for each relevant request:
   - Request URL and parameters
   - Response status code
   - Response body content
   - Timing (when it occurs relative to page load)

**Specific Endpoints to Monitor:**
- `/chatbot/api/chat/sessions` (session list endpoint)
- `/api/auth/status` (authentication check)
- `/chatbot/api/chat/history` (chat history for specific session)

**Questions to Answer:**
- Are the sessions API requests succeeding (200 OK) but returning empty data?
- Are there any authentication/authorization errors in API responses?
- Is there a race condition where DOM updates are happening before data is available?

#### 4. Event Sequence Testing

**Steps:**
1. Add these debugging commands to the Console and then reload the page:
   ```javascript
   // Track function calls related to sessions
   const originalFetch = window.fetch;
   window.fetch = function(...args) {
     console.log('Fetch call:', args[0]);
     return originalFetch.apply(this, args)
       .then(response => {
         console.log('Fetch response:', args[0], response.status);
         return response;
       })
       .catch(error => {
         console.error('Fetch error:', args[0], error);
         throw error;
       });
   }
   
   // Monitor DOM updates in the sessions area
   const observer = new MutationObserver(mutations => {
     mutations.forEach(mutation => {
       console.log('DOM changed:', mutation.target, mutation.type);
     });
   });
   
   // Start observing once the container exists
   setTimeout(() => {
     const container = document.getElementById('session-list') || 
                      document.querySelector('.chat-history');
     if (container) {
       observer.observe(container, { 
         childList: true, 
         subtree: true 
       });
       console.log('Observer attached to:', container);
     } else {
       console.error('Session container not found for observer');
     }
   }, 1000);
   ```

2. Track the sequence of events from page load to error appearance
3. Submit a question and observe how the error state changes

**Questions to Answer:**
- What is the exact sequence of events leading to the error?
- Which DOM manipulation is happening when the error occurs?
- What changes after submitting a question that makes the sessions appear?

#### 5. Template Rendering Check

**Steps:**
1. View the HTML source of the page when the error occurs
2. Check if the template is rendering correctly with this Console command:
   ```javascript
   console.log(document.querySelector('.chat-history').innerHTML);
   ```
3. Compare the HTML structure between:
   - The state with the error
   - After submitting a question when sessions appear
   - The admin view (if different)

**Questions to Answer:**
- Is the template rendering empty containers that should be populated later?
- Are there conditional Jinja2 blocks in the template that might be skipped?
- Does the DOM structure match what the JavaScript code expects?

#### 6. Data Flow Diagnosis

**Steps:**
1. Place breakpoints in the JavaScript code at:
   - The session loading function
   - Event handlers for chat history items
   - Any code referencing parentNode around line 690
2. Reload the page and let the debugger pause execution
3. Inspect variable values at each breakpoint

**Questions to Answer:**
- What is the state of session data when the error occurs?
- Is the code attempting to access elements before they exist?
- Are event handlers being attached to non-existent elements?

#### 7. Regression Testing After Fix

**Steps:**
1. After implementing a fix, verify that:
   - The "Failed to load sessions" error no longer appears
   - No JavaScript console errors related to null elements
   - The session list appears immediately on page load
   - All session items are clickable
2. Test with multiple browser refreshes and different user roles
3. Test with an empty session history and with multiple existing sessions

**Questions to Answer:**
- Does the fix resolve the issue consistently across different scenarios?
- Are there any new errors or warnings introduced by the fix?
- Is there any performance impact from the fix?
