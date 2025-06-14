/**
 * Citation functionality for ResHub
 * Handles citation generation, copying, and related UI interactions
 */

// Global variables to store citation data
let currentCitations = {};
let currentPaperId = null;
let currentCitationStyle = 'APA';

// Initialize event listeners when the document is ready
document.addEventListener('DOMContentLoaded', function() {
    // Citation button click handler
    const citationButton = document.getElementById('citationButton');
    if (citationButton) {
        citationButton.addEventListener('click', function() {
            const paperId = this.getAttribute('data-paper-id');
            loadCitations(paperId);
        });
    }
    
    // Citation style selector change handler
    const styleSelect = document.getElementById('citationStyleSelect');
    if (styleSelect) {
        styleSelect.addEventListener('change', function() {
            currentCitationStyle = this.value;
            updateCitationDisplay();
        });
    }
    
    // Copy button click handler
    const copyButton = document.getElementById('copyButton');
    if (copyButton) {
        copyButton.addEventListener('click', function() {
            copyCitation();
        });
    }
    
    // Download button click handler
    const downloadButton = document.getElementById('downloadBibtexButton');
    if (downloadButton) {
        downloadButton.addEventListener('click', function() {
            const citation = currentCitations.citations[currentCitationStyle];
            if (citation) {
                // Send AJAX request to track download
                fetch(citation.download_url, {
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                })
                .then(response => response.json())
                .then(data => {
                    // Update download count in UI
                    if (data.download_count) {
                        document.getElementById('downloadCount').textContent = data.download_count;
                        document.getElementById('citationMetrics').classList.remove('d-none');
                    }
                    
                    // Now initiate the actual file download
                    window.location.href = citation.download_url;
                })
                .catch(error => {
                    console.error('Error tracking download:', error);
                    // Still download even if tracking fails
                    window.location.href = citation.download_url;
                });
            }
        });
    }
    
    // Permalink button click handler
    const permalinkButton = document.getElementById('permalinkButton');
    if (permalinkButton) {
        permalinkButton.addEventListener('click', function() {
            const citation = currentCitations.citations[currentCitationStyle];
            if (citation) {
                navigator.clipboard.writeText(citation.permalink)
                    .then(() => {
                        // Show feedback
                        const originalText = this.innerHTML;
                        this.innerHTML = '<i class="bi bi-check"></i> Link Copied!';
                        setTimeout(() => {
                            this.innerHTML = originalText;
                        }, 2000);
                    })
                    .catch(err => {
                        console.error('Failed to copy permalink: ', err);
                        alert('Could not copy permalink. URL: ' + citation.permalink);
                    });
            }
        });
    }
});

// Function to load citation modal
function loadCitations(paperId) {
    currentPaperId = paperId;
    
    // Reset the UI
    document.getElementById('citationText').innerHTML = '\
        <div class="placeholder-glow">\n\
            <span class="placeholder col-12"></span>\n\
            <span class="placeholder col-10"></span>\n\
        </div>';
    
    document.getElementById('downloadBibtexButton').disabled = true;
    document.getElementById('permalinkButton').disabled = true;
    document.getElementById('citationMetrics').classList.add('d-none');
    
    // Show the modal
    const citationModal = new bootstrap.Modal(document.getElementById('citationModal'));
    citationModal.show();
    
    // Load citations from API
    fetchCitations(paperId);
}

// Function to fetch citations for a paper from API
function fetchCitations(paperId) {
    fetch(`/api/citation/${paperId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            currentCitations = data;
            
            // Update the UI with the citation information
            updateCitationDisplay();
        })
        .catch(error => {
            console.error('Error fetching citations:', error);
            document.getElementById('citationText').innerHTML = 
                '<div class="alert alert-danger">Error generating citation. Please try again.</div>';
        });
}

// Function to update the UI with the current citation style
function updateCitationDisplay() {
    if (!currentCitations || !currentCitations.citations) {
        return;
    }
    
    const citation = currentCitations.citations[currentCitationStyle];
    if (!citation) {
        document.getElementById('citationText').innerHTML = 
            '<div class="alert alert-warning">Citation style not available.</div>';
        return;
    }
    
    // Update citation text
    document.getElementById('citationText').innerHTML = 
        `<div>${citation.formatted_text}</div>`;
    
    // Enable buttons
    document.getElementById('downloadBibtexButton').disabled = false;
    document.getElementById('permalinkButton').disabled = false;
    
    // Update metrics if available
    if ('copy_count' in citation || 'download_count' in citation) {
        document.getElementById('citationMetrics').classList.remove('d-none');
        if ('copy_count' in citation) {
            document.getElementById('copyCount').textContent = citation.copy_count;
        }
        if ('download_count' in citation) {
            document.getElementById('downloadCount').textContent = citation.download_count;
        }
    }
}

// Function to copy citation to clipboard and update copy count
function copyCitation() {
    if (!currentCitations || !currentCitations.citations) {
        return;
    }
    
    const citation = currentCitations.citations[currentCitationStyle];
    if (!citation) {
        return;
    }
    
    fetch(citation.copy_url)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Copy to clipboard
                navigator.clipboard.writeText(data.formatted_citation)
                    .then(() => {
                        // Show feedback
                        const copyBtn = document.getElementById('copyButton');
                        const originalText = copyBtn.innerHTML;
                        copyBtn.innerHTML = '<i class="bi bi-check"></i> Copied!';
                        
                        // Update copy count
                        if (data.copy_count) {
                            document.getElementById('copyCount').textContent = data.copy_count;
                            document.getElementById('citationMetrics').classList.remove('d-none');
                        }
                        
                        // Reset button after delay
                        setTimeout(() => {
                            copyBtn.innerHTML = originalText;
                        }, 2000);
                    })
                    .catch(err => {
                        console.error('Failed to copy: ', err);
                        alert('Copy to clipboard failed. Please try selecting and copying the text manually.');
                    });
            }
        })
        .catch(error => {
            console.error('Error copying citation:', error);
        });
}
