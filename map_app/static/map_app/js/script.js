// Global variables state management
var map = null;
var userMarker = null;
var resourceMarkers = []; // Keep track of pins so we can clear them easily on back

// Track the current application state for radius refreshing
var currentCategory = null;
var currentLat = null;
var currentLon = null;

// Helper Map describing frontend strings based on category ID
const categoryTitles = {
    'shelter': 'Emergency Shelters',
    'food': 'Food Banks & Kitchens',
    'medical': 'ERs & Medical Centers',
    'rehab': 'Rehabilitation Centers'
};

/**
 * Triggered when a User clicks any of the 4 category buttons.
 * Hides the home screen, initializes the map, and requests their geolocation.
 */
function openMapCategory(categoryId) {
    // Document application state
    currentCategory = categoryId;

    // 1) Swap UI displays
    document.getElementById('home-view').style.display = 'none';
    document.getElementById('map-view').style.display = 'flex';
    
    // 2) Set dynamic text
    document.getElementById('map-title').innerText = categoryTitles[categoryId] || "Resources";
    
    // 3) Show Loading Banner
    let infoBox = document.getElementById('loading-info');
    infoBox.style.display = 'block';
    infoBox.innerText = "Finding your location...";

    // 4) Initialize Map if it doesn't already exist
    if (!map) {
        map = L.map('map').setView([0, 0], 2);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors'
        }).addTo(map);
    }

    // 5) Prompt browser location api
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (pos) => onLocationSuccess(pos, categoryId),
            onLocationError,
            { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
        );
    } else {
        infoBox.innerText = "Geolocation is not supported by your browser.";
    }
}

/**
 * Triggered when the user hits the Back Button.
 * Shuts down the map view and brings the 4 buttons back to center-screen.
 */
function closeMap() {
    // Hide the actual map screen
    document.getElementById('map-view').style.display = 'none';
    // Show the standard main container
    document.getElementById('home-view').style.display = 'flex';
    
    // Clean up old markers
    if (userMarker) { 
        map.removeLayer(userMarker); 
        userMarker = null; 
    }
    resourceMarkers.forEach(marker => map.removeLayer(marker));
    resourceMarkers = []; // Empty the tracking array completely
}

/**
 * Fired automatically when `navigator.geolocation` succeeds.
 * Parses the coords, centers the map, and queries the respective backend.
 */
function onLocationSuccess(pos, categoryId) {
    currentLat = pos.coords.latitude;
    currentLon = pos.coords.longitude;
    fetchData();
}

/**
 * Triggers the radius update manually when user changes dropdown
 */
function updateRadius() {
    if (currentCategory && currentLat && currentLon) {
        // Clear existing pins cleanly before polling again
        resourceMarkers.forEach(marker => map.removeLayer(marker));
        resourceMarkers = [];
        fetchData();
    }
}

/**
 * Generic data fetcher utilizing state variables
 */
function fetchData() {
    var infoBox = document.getElementById('loading-info');
    var radius = document.getElementById('radius-select').value;
    
    infoBox.style.display = 'block';
    infoBox.innerText = `Location verified. Searching for ${currentCategory} (${radius}m)...`;

    // Adjust view to zoom closely on user's exact coordinate point
    map.setView([currentLat, currentLon], 14);

    // Draw the user pin (Red map marker)
    if (!userMarker) {
        var userIcon = L.icon({
            iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
            shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
            iconSize: [25, 41],
            iconAnchor: [12, 41],
            popupAnchor: [1, -34],
            shadowSize: [41, 41]
        });
        userMarker = L.marker([currentLat, currentLon], {icon: userIcon}).addTo(map)
            .bindPopup("<b>Your Approximate Location</b>")
            .openPopup();
    }

    // Perform our asynchronous Javascript Fetch exactly against our Django REST API url
    fetch(`/api/search_resources/?category=${currentCategory}&lat=${currentLat}&lon=${currentLon}&radius=${radius}`)
        .then(response => response.json())
        .then(data => {
            // First evaluate if our backend explicitly threw an Overpass API timeout or server error
            if (data.error) {
                infoBox.innerText = `API Search Failed: The region might be too heavily populated to search ${radius} meters at once. Try a smaller radius.`;
                return; // halt execution
            }

            // Safety check if the response format contains valid `elements` array from Overpass
            if (data.elements && data.elements.length > 0) {
                infoBox.innerText = `Found ${data.elements.length} match(es) cleanly inside ${radius}m range!`;
                
                // Overpass typically returns standard "nodes" mapping lat/long directly 
                data.elements.forEach(element => {
                    if (element.type === 'node') {
                        // Default fallback naming just in case the node lacks a dedicated "name" tag
                        var name = element.tags && element.tags.name ? element.tags.name : "Unnamed Service Provider";
                        
                        // Draw standardized Blue Pin for the available resource
                        var marker = L.marker([element.lat, element.lon]).addTo(map)
                            .bindPopup(`<b>${name}</b><br>Category: ${categoryTitles[currentCategory]}`);
                        
                        // Index into global array so we can wipe them on `Back` execution
                        resourceMarkers.push(marker);
                    }
                });

                // Automatically hide infoBox gently using setTimeout
                setTimeout(() => { infoBox.style.display = 'none'; }, 4000);
            } else {
                infoBox.innerText = `No resources currently found within a ${radius}m radius.`;
            }
        })
        .catch(err => {
            console.error("Fetch API error:", err);
            infoBox.innerText = "Fatal network error fetching resources. Please try again.";
        });
}

/**
 * Fired manually by javascript if `navigator.geolocation` crashes or user denies permission.
 */
function onLocationError(err) {
    console.warn(`Location Error Code (${err.code}): ${err.message}`);
    document.getElementById('loading-info').innerText = "Location access denied or failed. Please allow standard browser location permission.";
}
