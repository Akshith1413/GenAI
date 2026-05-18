document.addEventListener('DOMContentLoaded', () => {
    // UI Elements
    const form = document.getElementById('generate-form');
    const submitBtn = document.getElementById('submit-btn');
    const btnText = document.querySelector('.btn-text');
    const loader = document.querySelector('.loader');
    const resultsDiv = document.getElementById('results');
    const attemptsContainer = document.getElementById('attempts-container');
    const previewDiv = document.getElementById('final-document');
    const editorTextarea = document.getElementById('markdown-editor');
    
    // Tab Elements
    const tabPreview = document.getElementById('tab-preview');
    const tabEdit = document.getElementById('tab-edit');
    
    // Download Elements
    const downloadPdfBtn = document.getElementById('download-pdf-btn');
    const downloadMdBtn = document.getElementById('download-md-btn');
    const downloadTxtBtn = document.getElementById('download-txt-btn');
    
    // State
    let currentDocumentName = 'Agent_Document';
    
    // Generation Form Handler
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const topic = document.getElementById('topic').value;
        const notes = document.getElementById('notes').value;
        const max_attempts = document.getElementById('max_attempts').value;
        
        // Update document name based on topic
        currentDocumentName = topic.replace(/[^a-z0-9]/gi, '_').toLowerCase() || 'agent_document';
        
        // UI Loading state
        submitBtn.disabled = true;
        btnText.textContent = 'Engineering Output...';
        loader.classList.remove('hidden');
        resultsDiv.classList.add('hidden');
        attemptsContainer.innerHTML = '';
        previewDiv.innerHTML = '';
        editorTextarea.value = '';
        
        try {
            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ topic, notes, max_attempts })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Render attempts
                data.attempts.forEach((attempt, index) => {
                    const reviewText = attempt.review.toLowerCase();
                    const isApproved = reviewText.includes('status: approved');
                    const statusClass = isApproved ? 'status-approved' : 'status-rejected';
                    const statusText = isApproved ? 'Approved' : 'Rejected';
                    
                    // Add slight delay for sequential animation
                    setTimeout(() => {
                        const attemptHTML = `
                            <div class="attempt-card fade-in">
                                <div class="attempt-header">
                                    <h3><i class="fa-solid fa-code-branch"></i> Iteration ${attempt.attempt}</h3>
                                    <span class="status-badge ${statusClass}">${statusText}</span>
                                </div>
                                <div class="review-content">${attempt.review}</div>
                            </div>
                        `;
                        attemptsContainer.insertAdjacentHTML('beforeend', attemptHTML);
                    }, index * 200);
                });
                
                // Set Editor Content
                editorTextarea.value = data.final_document;
                
                // Set Preview Content
                updatePreview();
                
                // Show results
                resultsDiv.classList.remove('hidden');
                
                // Scroll to results smoothly
                setTimeout(() => {
                    resultsDiv.scrollIntoView({ behavior: 'smooth' });
                }, 100);
            } else {
                alert('An error occurred while generating the document.');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Failed to connect to the server.');
        } finally {
            submitBtn.disabled = false;
            btnText.textContent = 'Generate Stunning Document';
            loader.classList.add('hidden');
        }
    });

    // Function to render markdown
    function updatePreview() {
        const rawMarkdown = editorTextarea.value;
        previewDiv.innerHTML = marked.parse(rawMarkdown);
    }
    
    // Sync preview when typing in editor
    editorTextarea.addEventListener('input', updatePreview);

    // Tab Switching Logic
    tabPreview.addEventListener('click', () => {
        tabPreview.classList.add('active');
        tabEdit.classList.remove('active');
        previewDiv.classList.add('active-view');
        editorTextarea.classList.remove('active-view');
    });

    tabEdit.addEventListener('click', () => {
        tabEdit.classList.add('active');
        tabPreview.classList.remove('active');
        editorTextarea.classList.add('active-view');
        previewDiv.classList.remove('active-view');
    });

    // Download Logic Helper
    function downloadFile(content, filename, type) {
        const blob = new Blob([content], { type: type });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    // Download Button Handlers
    downloadPdfBtn.addEventListener('click', () => {
        const rawContent = editorTextarea.value;
        if (!rawContent || rawContent.trim() === '') return alert('Nothing to download yet!');
        
        const htmlContent = marked.parse(rawContent);
        
        const styledHtml = `
            <div id="pdf-exclusive-format" style="font-family: Arial, sans-serif; color: #000; background: #fff; padding: 40px; max-width: 800px; margin: 0 auto;">
                <style>
                    #pdf-exclusive-format h1 { font-size: 24px; border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px; color: #000; page-break-after: avoid; }
                    #pdf-exclusive-format h2 { font-size: 20px; color: #333; margin-top: 20px; margin-bottom: 15px; page-break-after: avoid; }
                    #pdf-exclusive-format h3 { font-size: 16px; color: #444; margin-top: 15px; margin-bottom: 10px; page-break-after: avoid; }
                    #pdf-exclusive-format p { line-height: 1.6; margin-bottom: 15px; font-size: 14px; color: #222; }
                    #pdf-exclusive-format ul, #pdf-exclusive-format ol { margin-bottom: 15px; padding-left: 20px; font-size: 14px; color: #222; }
                    #pdf-exclusive-format li { margin-bottom: 5px; line-height: 1.6; }
                    #pdf-exclusive-format pre { background-color: #f5f5f5; padding: 15px; border-radius: 5px; font-family: monospace; font-size: 12px; white-space: pre-wrap; margin-bottom: 15px; border: 1px solid #ccc; color: #333; page-break-inside: avoid; }
                    #pdf-exclusive-format code { background-color: #f5f5f5; padding: 2px 5px; border-radius: 3px; font-family: monospace; font-size: 12px; border: 1px solid #eee; color: #333; }
                    #pdf-exclusive-format pre code { background-color: transparent; padding: 0; border: none; }
                    #pdf-exclusive-format blockquote { border-left: 4px solid #8b5cf6; margin: 0 0 15px 0; padding: 10px 15px; background-color: #fafafa; color: #555; font-style: italic; page-break-inside: avoid; }
                    #pdf-exclusive-format table { width: 100%; border-collapse: collapse; margin-bottom: 15px; page-break-inside: avoid; }
                    #pdf-exclusive-format th, #pdf-exclusive-format td { border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 14px; }
                    #pdf-exclusive-format th { background-color: #f2f2f2; }
                </style>
                ${htmlContent}
            </div>
        `;
        
        // CRITICAL FIX: html2canvas has a known bug where it crops the height to the viewport height 
        // if the document body or html has overflow set to hidden. We must temporarily remove it.
        const oldBodyOverflow = document.body.style.overflow;
        const oldBodyOverflowX = document.body.style.overflowX;
        const oldHtmlOverflow = document.documentElement.style.overflow;
        document.body.style.overflow = 'visible';
        document.body.style.overflowX = 'visible';
        document.documentElement.style.overflow = 'visible';
        
        const opt = {
            margin:       0.5,
            filename:     `${currentDocumentName}.pdf`,
            image:        { type: 'jpeg', quality: 0.98 },
            html2canvas:  { scale: 2, useCORS: true, scrollY: 0 },
            jsPDF:        { unit: 'in', format: 'letter', orientation: 'portrait' },
            pagebreak:    { mode: ['avoid-all', 'css', 'legacy'] }
        };
        
        html2pdf().set(opt).from(styledHtml).save().then(() => {
            // Restore the original overflow values
            document.body.style.overflow = oldBodyOverflow;
            document.body.style.overflowX = oldBodyOverflowX;
            document.documentElement.style.overflow = oldHtmlOverflow;
        }).catch(err => {
            console.error("PDF generation error:", err);
            document.body.style.overflow = oldBodyOverflow;
            document.body.style.overflowX = oldBodyOverflowX;
            document.documentElement.style.overflow = oldHtmlOverflow;
        });
    });

    downloadMdBtn.addEventListener('click', () => {
        const content = editorTextarea.value;
        if (!content) return alert('Nothing to download yet!');
        downloadFile(content, `${currentDocumentName}.md`, 'text/markdown');
    });

    downloadTxtBtn.addEventListener('click', () => {
        const content = editorTextarea.value;
        if (!content) return alert('Nothing to download yet!');
        downloadFile(content, `${currentDocumentName}.txt`, 'text/plain');
    });
});
