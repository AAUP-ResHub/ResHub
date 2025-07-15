// Script for the Journal Finder feature

// Function to handle the "Find Best Journal" button on My Papers page
function setupFindJournalButtons() {
    // Find all "Find Best Journal" buttons
    const findJournalBtns = document.querySelectorAll('.find-journal-btn');
    
    // Add click event listeners to each button
    findJournalBtns.forEach(button => {
        button.addEventListener('click', function(e) {
            // Prevent default link behavior
            e.preventDefault();
            
            // Get paper data from data attributes
            const paperData = {
                id: this.getAttribute('data-paper-id'),
                title: this.getAttribute('data-paper-title'),
                abstract: this.getAttribute('data-paper-abstract'),
                pdfPath: this.getAttribute('data-paper-pdf')
            };
            
            // Store paper data in sessionStorage
            sessionStorage.setItem('journalFinderPaperData', JSON.stringify(paperData));
            
            // Navigate to the journal finder page
            window.location.href = this.getAttribute('href');
        });
    });
}

// Function to prefill journal finder form if data exists in sessionStorage
function prefillJournalFinderForm() {
    // Check if we're on the journal finder page
    const titleInput = document.getElementById('title');
    const abstractTextarea = document.getElementById('abstract');
    
    if (titleInput && abstractTextarea) {
        // Get stored paper data from sessionStorage
        const storedDataString = sessionStorage.getItem('journalFinderPaperData');
        
        if (storedDataString) {
            try {
                const paperData = JSON.parse(storedDataString);
                
                // Only prefill if the fields are empty (to avoid overriding user input)
                if (!titleInput.value && paperData.title) {
                    titleInput.value = paperData.title;
                }
                
                if (!abstractTextarea.value && paperData.abstract) {
                    abstractTextarea.value = paperData.abstract;
                }
                
                // Leave the data in sessionStorage for now in case the user resubmits the form
                // The data will be available for re-prefilling if needed
                console.log('Journal finder form prefilled with paper data');
            } catch (e) {
                console.error('Error parsing stored paper data:', e);
            }
        }
    }
}

// Initialize when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    setupFindJournalButtons();
    prefillJournalFinderForm();
});
