// Script for the My Papers functionality

document.addEventListener('DOMContentLoaded', function() {
    console.log('My Papers JS loaded successfully');
    
    // Set up click handlers for the "Find Best Journal" buttons
    const findJournalButtons = document.querySelectorAll('.find-journal-btn');
    console.log('Found Find Journal buttons:', findJournalButtons.length);
    
    findJournalButtons.forEach(button => {
        // Log button attributes for debugging
        console.log('Button data attributes:', {
            id: button.getAttribute('data-paper-id'),
            title: button.getAttribute('data-paper-title'),
            abstract: button.getAttribute('data-paper-abstract')
        });
        
        button.addEventListener('click', function(e) {
            // Prevent the default link behavior
            e.preventDefault();
            
            // Get paper data from data attributes
            const paperData = {
                id: this.getAttribute('data-paper-id'),
                title: this.getAttribute('data-paper-title'),
                abstract: this.getAttribute('data-paper-abstract'),
                pdfPath: this.getAttribute('data-paper-pdf')
            };
            
            console.log('Paper data collected:', paperData); // Debug output
            
            // Store the paper data in sessionStorage
            sessionStorage.setItem('journalFinderPaperData', JSON.stringify(paperData));
            
            // Navigate to the journal finder page
            window.location.href = this.getAttribute('href');
        });
    });
});
