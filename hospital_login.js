// Global variables
console.log('Hospital Login JS Loaded v2 - File Upload Logic Active');
let map;
let userMarker;
let hospitalMarkers = [];
let userLocation = null;
let selectedHospitalCoords = null; // Store selected hospital coordinates

// Initialize map when page loads
document.addEventListener('DOMContentLoaded', function () {
    const mapElement = document.getElementById('map');
    if (mapElement) {
        initializeMap();
    }
});

// Initialize Leaflet Map
function initializeMap() {
    // Default center (India)
    map = L.map('map').setView([20.5937, 78.9629], 5);

    // Add OpenStreetMap tiles with dark theme
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 20
    }).addTo(map);
}

// Search for nearby hospitals
const searchHospitalsBtn = document.getElementById('searchHospitalsBtn');
const hospitalSuggestions = document.getElementById('hospitalSuggestions');
const hospitalNameInput = document.getElementById('hospitalName');

if (searchHospitalsBtn) {
    searchHospitalsBtn.addEventListener('click', function () {
        if (!navigator.geolocation) {
            alert('Geolocation is not supported by your browser');
            return;
        }

        // Show loading state
        const originalHTML = this.innerHTML;
        this.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="animation: spin 1s linear infinite; width: 18px; height: 18px;">
            <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" opacity="0.25"/>
            <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        Searching...
    `;
        this.disabled = true;

        navigator.geolocation.getCurrentPosition(
            function (position) {
                userLocation = {
                    lat: position.coords.latitude,
                    lon: position.coords.longitude
                };

                // Center map on user location
                map.setView([userLocation.lat, userLocation.lon], 13);

                // Add user marker
                if (userMarker) {
                    map.removeLayer(userMarker);
                }

                const userIcon = L.divIcon({
                    className: 'custom-user-marker',
                    html: `<div style="background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 15px rgba(59, 130, 246, 0.6); border: 3px solid white;">
                    <svg viewBox="0 0 24 24" fill="white" style="width: 20px; height: 20px;">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                        <circle cx="12" cy="7" r="4"/>
                    </svg>
                </div>`,
                    iconSize: [40, 40],
                    iconAnchor: [20, 20]
                });

                userMarker = L.marker([userLocation.lat, userLocation.lon], { icon: userIcon })
                    .addTo(map)
                    .bindPopup('<b>Your Location</b>')
                    .openPopup();

                // Search for hospitals using Overpass API
                searchNearbyHospitals(userLocation.lat, userLocation.lon);

                // Reset button
                searchHospitalsBtn.innerHTML = originalHTML;
                searchHospitalsBtn.disabled = false;
            },
            function (error) {
                alert('Unable to retrieve your location: ' + error.message);
                searchHospitalsBtn.innerHTML = originalHTML;
                searchHospitalsBtn.disabled = false;
            }
        );
    });
}

// Search nearby hospitals using Overpass API (OpenStreetMap)
function searchNearbyHospitals(lat, lon) {
    // Clear existing hospital markers
    hospitalMarkers.forEach(marker => map.removeLayer(marker));
    hospitalMarkers = [];

    // Overpass API query for hospitals within 5km radius
    const radius = 5000; // 5km in meters
    const query = `
        [out:json][timeout:25];
        (
            node["amenity"="hospital"](around:${radius},${lat},${lon});
            way["amenity"="hospital"](around:${radius},${lat},${lon});
            relation["amenity"="hospital"](around:${radius},${lat},${lon});
        );
        out center;
    `;

    const overpassUrl = 'https://overpass-api.de/api/interpreter';

    fetch(overpassUrl, {
        method: 'POST',
        body: query
    })
        .then(response => response.json())
        .then(data => {
            const hospitals = data.elements.map(element => {
                const hospitalLat = element.lat || element.center.lat;
                const hospitalLon = element.lon || element.center.lon;
                const distance = calculateDistance(lat, lon, hospitalLat, hospitalLon);

                return {
                    name: element.tags.name || 'Unnamed Hospital',
                    lat: hospitalLat,
                    lon: hospitalLon,
                    address: null, // Will be fetched via reverse geocoding
                    distance: distance,
                    tags: element.tags
                };
            });

            // Sort by distance
            hospitals.sort((a, b) => a.distance - b.distance);

            // Fetch full addresses for all hospitals using reverse geocoding
            Promise.all(hospitals.map(hospital => fetchFullAddress(hospital.lat, hospital.lon)))
                .then(addresses => {
                    hospitals.forEach((hospital, index) => {
                        hospital.address = addresses[index];
                    });

                    // Display hospitals on map
                    displayHospitalsOnMap(hospitals);

                    // Show suggestions
                    displaySuggestions(hospitals);
                })
                .catch(error => {
                    console.error('Error fetching addresses:', error);
                    // Still display hospitals even if address fetch fails
                    hospitals.forEach(hospital => {
                        hospital.address = formatAddress(hospital.tags);
                    });
                    displayHospitalsOnMap(hospitals);
                    displaySuggestions(hospitals);
                });
        })
        .catch(error => {
            console.error('Error fetching hospitals:', error);
            alert('Unable to fetch nearby hospitals. Please try again.');
        });
}

// Display hospitals on map
function displayHospitalsOnMap(hospitals) {
    hospitals.forEach(hospital => {
        const hospitalIcon = L.divIcon({
            className: 'custom-hospital-marker',
            html: `<div style="background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%); width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 15px rgba(220, 38, 38, 0.6); border: 2px solid white; cursor: pointer;">
                <span style="font-size: 18px;">🏥</span>
            </div>`,
            iconSize: [36, 36],
            iconAnchor: [18, 18]
        });

        const marker = L.marker([hospital.lat, hospital.lon], { icon: hospitalIcon })
            .addTo(map)
            .bindPopup(createPopupContent(hospital));

        hospitalMarkers.push(marker);
    });
}

// Create popup content for hospital marker
function createPopupContent(hospital) {
    return `
        <div style="min-width: 200px;">
            <div class="popup-hospital-name">${hospital.name}</div>
            <div class="popup-hospital-address">${hospital.address}</div>
            <div class="suggestion-distance">${hospital.distance.toFixed(2)} km away</div>
            <button class="popup-select-btn" onclick="selectHospital('${escapeHtml(hospital.name)}', '${escapeHtml(hospital.address)}', ${hospital.lat}, ${hospital.lon})">
                Select This Hospital
            </button>
        </div>
    `;
}

// Display suggestions dropdown
function displaySuggestions(hospitals) {
    hospitalSuggestions.innerHTML = '';

    if (hospitals.length === 0) {
        hospitalSuggestions.innerHTML = '<div style="padding: 16px; text-align: center; color: var(--text-muted);">No hospitals found nearby</div>';
        hospitalSuggestions.classList.add('active');
        return;
    }

    // Show top 10 hospitals
    hospitals.slice(0, 10).forEach(hospital => {
        const suggestionItem = document.createElement('div');
        suggestionItem.className = 'suggestion-item';
        suggestionItem.innerHTML = `
            <div class="suggestion-icon">🏥</div>
            <div class="suggestion-content">
                <div class="suggestion-name">${hospital.name}</div>
                <div class="suggestion-address">${hospital.address}</div>
                <div class="suggestion-distance">${hospital.distance.toFixed(2)} km away</div>
            </div>
        `;

        suggestionItem.addEventListener('click', function () {
            selectHospital(hospital.name, hospital.address, hospital.lat, hospital.lon);
        });

        hospitalSuggestions.appendChild(suggestionItem);
    });

    hospitalSuggestions.classList.add('active');
}

// Select a hospital
function selectHospital(name, address, lat, lon) {
    hospitalNameInput.value = name;
    document.getElementById('location').value = address;

    // Store coordinates for map link
    selectedHospitalCoords = { lat, lon };

    // Update map link
    updateMapLink(lat, lon, name);

    // Close suggestions
    hospitalSuggestions.classList.remove('active');

    // Center map on selected hospital
    map.setView([lat, lon], 15);

    // Highlight selected marker
    hospitalMarkers.forEach(marker => {
        const markerLatLng = marker.getLatLng();
        if (markerLatLng.lat === lat && markerLatLng.lng === lon) {
            marker.openPopup();
        }
    });

    // Scroll to contact field
    document.getElementById('contact').scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// Fetch full address using Nominatim reverse geocoding
function fetchFullAddress(lat, lon) {
    const nominatimUrl = `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&addressdetails=1`;

    return fetch(nominatimUrl, {
        headers: {
            'Accept-Language': 'en'
        }
    })
        .then(response => response.json())
        .then(data => {
            if (data.display_name) {
                return data.display_name;
            }
            return 'Address not available';
        })
        .catch(error => {
            console.error('Error fetching address:', error);
            return 'Address not available';
        });
}

// Format address from OSM tags (fallback)
function formatAddress(tags) {
    const parts = [];

    if (tags['addr:street']) parts.push(tags['addr:street']);
    if (tags['addr:city']) parts.push(tags['addr:city']);
    if (tags['addr:state']) parts.push(tags['addr:state']);
    if (tags['addr:postcode']) parts.push(tags['addr:postcode']);

    if (parts.length === 0) {
        // Fallback to other available info
        if (tags.address) return tags.address;
        return 'Fetching address...';
    }

    return parts.join(', ');
}

// Update map link
function updateMapLink(lat, lon, name) {
    const mapLinkContainer = document.getElementById('mapLinkContainer');
    if (!mapLinkContainer) return;

    const encodedName = encodeURIComponent(name);
    const googleMapsUrl = `https://www.google.com/maps/search/?api=1&query=${lat},${lon}`;

    mapLinkContainer.innerHTML = `
        <a href="${googleMapsUrl}" target="_blank" class="map-link" rel="noopener noreferrer">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <circle cx="12" cy="10" r="3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            View on Google Maps
        </a>
    `;
    mapLinkContainer.style.display = 'block';
}

// Calculate distance between two coordinates (Haversine formula)
function calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371; // Earth's radius in km
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);

    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
        Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
        Math.sin(dLon / 2) * Math.sin(dLon / 2);

    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
}

function toRad(degrees) {
    return degrees * (Math.PI / 180);
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML.replace(/'/g, "\\'");
}

// Close suggestions when clicking outside
document.addEventListener('click', function (e) {
    if (!e.target.closest('.search-container')) {
        hospitalSuggestions.classList.remove('active');
    }
});

// Add spin animation
const style = document.createElement('style');
style.textContent = `
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
`;
document.head.appendChild(style);

// Ensure DOM is loaded before attaching file upload listeners
// Ensure DOM is loaded before attaching file upload listeners
document.addEventListener('DOMContentLoaded', function () {
    // ID Upload Functionality - Matched with Donor Form
    const idUploadArea = document.getElementById('idUploadArea');
    const idFileInput = document.getElementById('staffIdUpload');
    const idUploadContent = document.getElementById('idUploadContent');
    const idPreviewArea = document.getElementById('idPreviewArea');
    const idPreviewImage = document.getElementById('idPreviewImage');
    const idChangeBtn = document.getElementById('idChangeBtn');
    let selectedIdFile = null;

    if (idUploadArea && idFileInput) {
        idUploadArea.addEventListener('click', (e) => {
            if (e.target !== idChangeBtn && !idChangeBtn.contains(e.target)) {
                idFileInput.click();
            }
        });

        idChangeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            idFileInput.click();
        });

        idFileInput.addEventListener('change', (e) => {
            handleIdFile(e.target.files[0]);
        });

        idUploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            idUploadArea.classList.add('drag-over');
        });

        idUploadArea.addEventListener('dragleave', () => {
            idUploadArea.classList.remove('drag-over');
        });

        idUploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            idUploadArea.classList.remove('drag-over');
            const file = e.dataTransfer.files[0];
            idFileInput.files = e.dataTransfer.files; // Sync file input
            handleIdFile(file);
        });
    }

    function handleIdFile(file) {
        if (!file) return;

        if (!file.type.startsWith('image/')) {
            alert('Please select an image file');
            return;
        }

        if (file.size > 5 * 1024 * 1024) {
            alert('File size must be less than 5MB');
            return;
        }

        selectedIdFile = file;

        const reader = new FileReader();
        reader.onload = (e) => {
            idPreviewImage.src = e.target.result;
            idUploadContent.style.display = 'none';
            idPreviewArea.style.display = 'block';

            // Success feedback
            idUploadArea.style.borderColor = 'var(--accent-green)';
            idUploadArea.style.backgroundColor = 'rgba(22, 163, 74, 0.05)';

            // Add success text if not already present
            let successText = document.getElementById('uploadSuccessText');
            if (!successText) {
                successText = document.createElement('p');
                successText.id = 'uploadSuccessText';
                successText.style.color = 'var(--accent-green)';
                successText.style.fontWeight = '600';
                successText.style.fontSize = '14px';
                successText.style.marginTop = '10px';
                successText.textContent = '✓ ID Uploaded Successfully';
                idPreviewArea.appendChild(successText);
            }
        };
        reader.readAsDataURL(file);

        const idError = document.getElementById('idError');
        if (idError) idError.style.display = 'none';
    }
});

// Form Submission is handled in hospital_login.html inline script

// Input validation feedback
const inputs = document.querySelectorAll('.form-input');
inputs.forEach(input => {
    if (input.id === 'location') return; // Skip readonly location field

    input.addEventListener('blur', function () {
        if (this.value && !this.checkValidity()) {
            this.style.borderColor = 'var(--primary-red)';
        } else if (this.value) {
            this.style.borderColor = 'var(--accent-green)';
        }
    });

    input.addEventListener('focus', function () {
        this.style.borderColor = 'var(--accent-blue)';
    });
});
