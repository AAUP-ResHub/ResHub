// app/static/js/document_editor.js

document.addEventListener('DOMContentLoaded', function() {
    const editorContainer = document.getElementById('editor-container');
    // If this element doesn't exist, we're not on the editor page, so do nothing.
    if (!editorContainer) {
        return; 
    }

    try {
        // Define a rich toolbar for a Notion-like experience
        const toolbarOptions = [
            [{ 'header': [1, 2, 3, false] }],
            ['bold', 'italic', 'underline', 'strike'],
            ['blockquote', 'code-block'],
            [{ 'list': 'ordered'}, { 'list': 'bullet' }],
            [{ 'color': [] }, { 'background': [] }],
            [{ 'align': [] }],
            ['link', 'image', 'video'],
            ['clean']
        ];

        const quill = new Quill('#editor-container', {
            modules: { toolbar: toolbarOptions },
            theme: 'snow', // 'snow' is a clean, modern theme
            placeholder: 'This document has no content. Start writing...'
        });

        // Load any existing content from the database into the editor
        const initialContentEl = document.getElementById('initial-content');
        if (initialContentEl) {
            const initialHTML = initialContentEl.innerHTML;
            if (initialHTML && initialHTML.trim() !== '') {
                // Use dangerouslyPasteHTML as we are loading trusted HTML from our own database
                quill.clipboard.dangerouslyPasteHTML(0, initialHTML);
            }
            // We don't need the hidden div anymore
            initialContentEl.remove();
        }
        
        // --- Autosave Functionality ---
        const docId = editorContainer.dataset.docId;
        // Extract workspace ID from the URL path
        const urlPath = window.location.pathname;
        const workspaceIdMatch = urlPath.match(/\/workspaces\/(\d+)\//i);
        const workspaceId = workspaceIdMatch ? workspaceIdMatch[1] : null;
        
        const saveStatusEl = document.getElementById('save-status');
        let saveTimeout;

        // Debounce function limits how often we call the save API
        const debounce = (func, delay) => {
            return (...args) => {
                clearTimeout(saveTimeout);
                saveTimeout = setTimeout(() => func.apply(this, args), delay);
            };
        };

        const saveContent = async () => {
            if (!saveStatusEl) return;
            
            const contentHTML = quill.root.innerHTML;
            saveStatusEl.textContent = 'Saving...';
            saveStatusEl.style.opacity = 1;

            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

            try {
                // Use the existing save_content endpoint
                const saveUrl = workspaceId ? 
                    `/workspaces/${workspaceId}/document/${docId}/save_content` : 
                    `/workspaces/document/${docId}/save`;
                
                const response = await fetch(saveUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({ content: contentHTML })
                });

                if (!response.ok) throw new Error(`Server error: ${response.status}`);
                
                const data = await response.json();
                if (data.status === 'success') {
                    saveStatusEl.textContent = 'Saved';
                    setTimeout(() => { saveStatusEl.style.opacity = 0; }, 2000); // Fade out success message
                } else {
                    throw new Error(data.message || 'Save failed.');
                }
            } catch (error) {
                console.error('Error saving document:', error);
                saveStatusEl.textContent = 'Save Failed!';
                saveStatusEl.style.color = 'red'; // Make error message prominent
            }
        };

        // Create a debounced version of our save function that waits 2 seconds after the last change
        const debouncedSave = debounce(saveContent, 2000);

        // Listen for changes made by the user in the editor
        quill.on('text-change', (delta, oldDelta, source) => {
            if (source === 'user') {
                saveStatusEl.textContent = '...'; // Indicate unsaved changes
                saveStatusEl.style.color = '#6c757d';
                saveStatusEl.style.opacity = 1;
                debouncedSave();
            }
        });

    } catch (error) {
        console.error("Failed to initialize Quill editor:", error);
        if (editorContainer) {
            editorContainer.innerHTML = '<p class="text-danger">Error: The text editor could not be loaded. Please check the browser console for details.</p>';
        }
    }
});
