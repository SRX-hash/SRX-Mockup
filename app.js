document.addEventListener('DOMContentLoaded', () => {

    // --- DOM Elements ---
    const searchForm = document.getElementById('search-form');
    const fabricInput = document.getElementById('fabric-ref');
    
    // Main results wrapper
    const resultsWrapper = document.getElementById('results-wrapper');

    // Fabric Card Elements
    const fabricCard = document.getElementById('fabric-card');
    const fabricCardImage = document.getElementById('fabric-card-image');
    const fabricCardRef = document.getElementById('fabric-card-ref');
    const fabricCardStyle = document.getElementById('fabric-card-style');
    const fabricCardError = document.getElementById('fabric-card-error');
    const fabricCardButton = document.getElementById('fabric-card-button'); // NEW: The garment button

    // Category Selector
    const categorySelector = document.getElementById('category-selector');
    const categoryButtons = document.querySelectorAll('.category-button');

    // Mockup Viewer
    const mockupViewer = document.getElementById('mockup-viewer');
    const mockupButtonsContainer = document.getElementById('mockup-buttons');
    const mockupViewerContainer = document.getElementById('viewer-container');
    const viewerTitle = document.getElementById('viewer-title');
    const viewerImage = document.getElementById('viewer-image');
    const downloadImageLink = document.getElementById('download-image');
    const downloadPdfLink = document.getElementById('download-pdf');
    const mockupError = document.getElementById('mockup-error-message');
    const mockupLoading = document.getElementById('mockup-loading');

    // --- State Variable ---
    let allMockupsData = {};

    // --- Main Search Event ---
    searchForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const refCode = fabricInput.value.trim();
        if (!refCode) return;

        resetUI();
        resultsWrapper.style.display = 'grid'; // Show the main wrapper
        fabricCard.style.display = 'block'; // Show the card
        fabricCardRef.textContent = refCode;
        fabricCardStyle.textContent = 'Loading...';

        try {
            // 1. --- ONE SINGLE FETCH ---
            const response = await fetch(`./api/get-all-info?ref=${refCode}`);
            if (!response.ok) {
                throw new Error(`Server error: ${response.statusText}`);
            }
            const data = await response.json();

            // 2. Store all mockup data globally
            allMockupsData = data.availableMockups || {};
            
            // 3. Populate Fabric Card
            fabricCardImage.src = data.imageUrl;
            fabricCardRef.textContent = data.refNo;
            fabricCardStyle.textContent = data.style;

            if (data.excelFound) {
                fabricCardError.style.display = 'none';
            } else {
                fabricCardError.textContent = data.style; // Show error (e.g., "File not found")
                fabricCardError.style.display = 'block';
                fabricCardStyle.style.display = 'none';
            }
            
            // 4. NEW: Show the garment button
            fabricCardButton.style.display = 'flex';

        } catch (err) {
            console.error('Error fetching data:', err);
            fabricCardStyle.style.display = 'none';
            fabricCardError.textContent = 'Failed to connect to API server. Is it running?';
            fabricCardError.style.display = 'block';
        }
    });

    // --- UI Click Events ---

    // NEW: Click event for the garment button on the fabric card
    fabricCardButton.addEventListener('click', () => {
        categorySelector.style.display = 'block'; // Show the category selector
        mockupViewer.style.display = 'none'; // Hide the mockup viewer (if visible)
        
        // De-select all category buttons
        categoryButtons.forEach(btn => btn.classList.remove('active'));
    });

    // Handle Category Selection
    categoryButtons.forEach(button => {
        button.addEventListener('click', () => {
            const category = button.dataset.category;
            
            // De-select all buttons
            categoryButtons.forEach(btn => btn.classList.remove('active'));
            // Select the clicked one
            button.classList.add('active');

            // Hide the category selector and show the mockup viewer IN ITS PLACE
            categorySelector.style.display = 'none';
            mockupViewer.style.display = 'grid'; // Use grid, as defined in CSS
            
            mockupLoading.style.display = 'none'; // Hide "Loading..."
            mockupViewerContainer.style.display = 'none'; // Hide main image
            
            // Get the mockups from our *stored* data, not a new fetch
            const mockups = allMockupsData[category] || [];
            displayMockups(mockups, category);
        });
    });

    // --- Helper Functions ---

    function displayMockups(mockups, categoryName) {
        mockupButtonsContainer.innerHTML = ''; // Clear old buttons
        
        if (mockups.length > 0) {
            mockupError.style.display = 'none';
            
            mockups.forEach(item => {
                const button = document.createElement('button');
                button.textContent = item.garmentName;
                button.addEventListener('click', (e) => {
                    showMockup(item);
                    // Set active class on button
                    document.querySelectorAll('#mockup-buttons button').forEach(btn => btn.classList.remove('active'));
                    e.currentTarget.classList.add('active');
                });
                mockupButtonsContainer.appendChild(button);
            });

            // Auto-click the first button
            if (mockupButtonsContainer.firstChild) {
                mockupButtonsContainer.firstChild.click();
            }

        } else {
            // No mockups found for this category
            mockupViewerContainer.style.display = 'none';
            mockupError.textContent = `No ${categoryName} mockups found for this ref code.`;
            mockupError.style.display = 'block';
        }
    }

    function showMockup(item) {
        mockupViewerContainer.style.display = 'block';
        viewerTitle.textContent = item.garmentName;
        viewerImage.src = item.mockupUrl;
        downloadImageLink.href = item.mockupUrl;
        downloadImageLink.download = item.mockupUrl.split('/').pop();

        if (item.techpackUrl) {
            downloadPdfLink.href = item.techpackUrl;
            downloadPdfLink.download = item.techpackUrl.split('/').pop();
            downloadPdfLink.style.display = 'inline-block';
        } else {
            downloadPdfLink.style.display = 'none';
        }
    }

    function resetUI() {
        resultsWrapper.style.display = 'none'; // Hide the whole results area
        fabricCard.style.display = 'none'; // Hide card
        
        // Clear placeholder text
        fabricCardRef.textContent = '';
        fabricCardStyle.textContent = '';
        fabricCardError.textContent = '';
        
        fabricCardStyle.style.display = 'inline';
        fabricCardError.style.display = 'none';
        fabricCardButton.style.display = 'none'; // Hide garment button
        
        categorySelector.style.display = 'none'; // Hide category selector
        mockupViewer.style.display = 'none'; // Hide mockup viewer
        
        categoryButtons.forEach(btn => btn.classList.remove('active'));
        
        allMockupsData = {}; // Clear stored data
    }
});

