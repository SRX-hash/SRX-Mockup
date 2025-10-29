document.addEventListener('DOMContentLoaded', () => {

    // --- STATE ---
    let allDataStore = [];
    let currentRef = null;

    // --- DOM ELEMENTS ---
    const searchForm = document.getElementById('search-form');
    const fabricInput = document.getElementById('fabric-ref');
    
    // Results Sections (now stacked)
    const fabricResultsSection = document.getElementById('fabric-results-section');
    const fabricListTitle = document.getElementById('fabric-list-title');
    const fabricCardList = document.getElementById('fabric-card-list');
    const fabricCardError = document.getElementById('fabric-card-error');

    const categorySelector = document.getElementById('category-selector');
    const categoryButtons = categorySelector.querySelectorAll('.category-button');
    
    const mockupViewer = document.getElementById('mockup-viewer');
    const mockupListTitle = document.getElementById('mockup-list-title');
    const mockupLoading = document.getElementById('mockup-loading');
    const mockupButtons = document.getElementById('mockup-buttons');
    const mockupError = document.getElementById('mockup-error-message');
    
    const viewerContainer = document.getElementById('viewer-container');
    const viewerTitle = document.getElementById('viewer-title');
    const viewerImage = document.getElementById('viewer-image');
    const downloadPdfLink = document.getElementById('download-pdf');
    const downloadImageLink = document.getElementById('download-image');

    // --- EVENT LISTENERS ---

    // 1. Handle Search
    searchForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const searchTerm = fabricInput.value.trim();
        if (!searchTerm) return;

        resetApp(); // Reset the entire UI
        fabricListTitle.textContent = "Searching...";
        fabricListTitle.style.display = 'block';

        try {
            const response = await fetch(`/api/find-fabrics?search=${searchTerm}`);
            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.error || `Server error: ${response.statusText}`);
            }
            
            allDataStore = await response.json();

            if (allDataStore.length === 0) {
                fabricListTitle.style.display = 'none';
                fabricCardError.textContent = `No fabrics found for "${searchTerm}".`;
                fabricCardError.style.display = 'block';
                return;
            }

            // Render all fabric cards
            fabricListTitle.textContent = `${allDataStore.length} fabric(s) found for "${searchTerm}"`;
            renderFabricCards(allDataStore);

        } catch (err) {
            console.error('Error fetching data:', err);
            fabricListTitle.style.display = 'none';
            fabricCardError.textContent = err.message || 'Failed to connect to API server.';
            fabricCardError.style.display = 'block';
        }
    });

    // 2. Handle Category Selection
    categoryButtons.forEach(button => {
        button.addEventListener('click', () => {
            const category = button.dataset.category;
            
            // De-select all buttons
            categoryButtons.forEach(btn => btn.classList.remove('active'));
            // Select the clicked one
            button.classList.add('active');
            
            // Show the mockup viewer section
            mockupViewer.style.display = 'flex';
            
            // Find the data for the *currently selected ref*
            const fabricData = allDataStore.find(item => item.ref === currentRef);
            if (!fabricData) return;

            // Populate the mockups for this category
            populateMockupList(fabricData.availableMockups, category);
        });
    });

    // --- FUNCTIONS ---

    function resetApp() {
        fabricResultsSection.style.display = 'block';
        fabricListTitle.style.display = 'block';
        fabricCardList.innerHTML = ''; // Clear old fabric cards
        fabricCardError.style.display = 'none';
        
        // Hide bottom sections
        categorySelector.style.display = 'none'; 
        mockupViewer.style.display = 'none';
        viewerContainer.style.display = 'none';
        
        allDataStore = [];
        currentRef = null;
    }

    // Function to create and show all fabric cards
    function renderFabricCards(fabricDataList) {
        fabricCardList.innerHTML = ''; // Clear list
        
        fabricDataList.forEach((fabricData) => {
            const card = document.createElement('div');
            card.className = 'fabric-card';
            
            // Store ref on the card itself for selection highlighting
            card.dataset.ref = fabricData.ref;
            
            card.innerHTML = `
                <div class="fabric-image-container">
                    <img class="fabric-card-image" src="${fabricData.swatchUrl}" alt="Fabric Swatch">
                    <button class="fabric-card-button" data-ref="${fabricData.ref}" title="View Garments">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M20.38 3.46L16 2a4 4 0 0 0-8 0L3.62 3.46a2 2 0 0 0-1.34 2.23l.58 3.47A1 1 0 0 0 4 10h16a1 1 0 0 0 .96-1.84l.58-3.47a2 2 0 0 0-1.34-2.23z"></path>
                            <path d="M4 10v10a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V10"></path>
                            <path d="M12 10v12"></path>
                        </svg>
                    </button>
                </div>
                <div class="fabric-card-details">
                    <p class="fabric-card-style">${fabricData.style}</p>
                </div>
            `;
            
            const garmentButton = card.querySelector('.fabric-card-button');
            
            // Show the garment button
            garmentButton.style.display = 'flex';
            
            // Add click listener to *this* button
            garmentButton.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent card click from firing
                const ref = garmentButton.dataset.ref;
                handleFabricCardClick(ref, card);
            });
            
            // Add click listener to the *whole card* as well
            card.addEventListener('click', () => {
                const ref = card.dataset.ref;
                handleFabricCardClick(ref, card);
            });
            
            fabricCardList.appendChild(card);
        });
    }

    // Function to handle when a garment button/card is clicked
    function handleFabricCardClick(ref, selectedCard) {
        currentRef = ref; // Set the global ref
        
        // Highlight the selected card
        document.querySelectorAll('.fabric-card').forEach(c => c.classList.remove('selected'));
        selectedCard.classList.add('selected');
        
        // Show the category selector
        categorySelector.style.display = 'block';
        
        // Hide the mockup viewer parts
        mockupViewer.style.display = 'none';
        viewerContainer.style.display = 'none';
        
        // Reset category buttons
        categoryButtons.forEach(btn => btn.classList.remove('active'));
        
        // Find the data for this ref
        const fabricData = allDataStore.find(item => item.ref === ref);
        if (!fabricData) {
            console.error("Could not find data for ref:", ref);
            return;
        }

        // Show/Hide category buttons based on availability
        let hasAnyMockups = false;
        for (let category of ['men', 'women', 'kids']) {
            const button = categorySelector.querySelector(`[data-category="${category}"]`);
            if (fabricData.availableMockups[category].length > 0) {
                button.style.display = 'block';
                hasAnyMockups = true;
            } else {
                button.style.display = 'none';
            }
        }
        
        // Show a message if no mockups at all are found
        if (!hasAnyMockups) {
             categorySelector.querySelector('h3').textContent = `No mockups found for this fabric.`;
        } else {
             categorySelector.querySelector('h3').textContent = 'Select a Category';
        }
    }

    // This function populates the horizontal mockup list
    function populateMockupList(availableMockups, category) {
        mockupButtons.innerHTML = ''; // Clear old buttons
        mockupError.style.display = 'none';
        mockupLoading.style.display = 'none';
        viewerContainer.style.display = 'none'; // Hide old image

        const mockups = availableMockups[category];

        if (mockups.length === 0) {
            mockupError.textContent = `No ${category} mockups found for this fabric.`;
            mockupError.style.display = 'block';
            return;
        }

        mockups.forEach(item => {
            const button = document.createElement('button');
            button.textContent = item.garmentName;
            
            button.addEventListener('click', (e) => {
                showMockup(item);
                // Highlight this button
                document.querySelectorAll('#mockup-buttons button').forEach(btn => {
                    btn.classList.remove('active');
                });
                e.currentTarget.classList.add('active');
            });
            
            mockupButtons.appendChild(button);
        });
    }

    // This function shows the final image
    function showMockup(item) {
        viewerContainer.style.display = 'block';
        viewerTitle.textContent = item.garmentName;
        
        // Build the full URLs (now relative)
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
        
        // Scroll to the viewer
        viewerContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

});

