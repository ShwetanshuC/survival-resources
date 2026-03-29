// ─── Global State ───────────────────────────────────────────────────────────
var map = null;
var userMarker = null;
var resourceMarkers = [];

var currentCategory = null;
var currentLat = null;
var currentLon = null;

// ─── Category Config ─────────────────────────────────────────────────────────
const categoryTitles = {
    shelter:  'Emergency Shelters',
    food:     'Food Banks & Kitchens',
    medical:  'ERs & Medical Centers',
    rehab:    'Rehabilitation Centers',
};

const categoryLoadingMsg = {
    shelter:  'Finding emergency shelters near you…',
    food:     'Finding food banks and kitchens near you…',
    medical:  'Finding hospitals and clinics near you…',
    rehab:    'Finding rehabilitation centers near you…',
};

// ─── Leaflet Icons ────────────────────────────────────────────────────────────
// Base icon template — only iconUrl changes between variants
function _makeIcon(color) {
    return L.icon({
        iconUrl:    `https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-${color}.png`,
        shadowUrl:  'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
        iconSize:   [25, 41],
        iconAnchor: [12, 41],
        popupAnchor:[1, -34],
        shadowSize: [41, 41],
    });
}

const icons = {
    user:    _makeIcon('violet'),
    medical: _makeIcon('red'),
    event:   _makeIcon('orange'),
    default: _makeIcon('blue'),
};

function _iconForElement(element) {
    if (element.type === 'event') return icons.event;
    if (currentCategory === 'medical')  return icons.medical;
    return icons.default;
}

// ─── Popup Builder ────────────────────────────────────────────────────────────
function _buildPopup(element) {
    var tags = element.tags || {};
    var lat  = element.lat;
    var lon  = element.lon;
    var name = tags.name || 'Unnamed Location';
    var lines = [`<b>${name}</b>`];

    // Address — compose from OSM addr:* tags if present
    var addrParts = [tags['addr:housenumber'], tags['addr:street']].filter(Boolean);
    if (addrParts.length) {
        var addrLine = addrParts.join(' ');
        if (tags['addr:city']) addrLine += ', ' + tags['addr:city'];
        lines.push(addrLine);
    } else if (tags.address) {
        lines.push(tags.address);
    }

    // Phone — tap-to-call link
    if (tags.phone) {
        lines.push(`<a href="tel:${tags.phone}">${tags.phone}</a>`);
    }

    // Hours — from OSM opening_hours tag if present
    if (tags.opening_hours) {
        lines.push(`<small>Hours: ${tags.opening_hours}</small>`);
    }

    // Scraped event extras
    if (element.type === 'event') {
        if (tags.source)     lines.push(`<i>Source: ${tags.source}</i>`);
        if (tags.source_url) lines.push(`<a href="${tags.source_url}" target="_blank" rel="noopener">View event</a>`);
    }

    // Navigate button — opens native Maps app with one tap
    if (lat != null && lon != null) {
        lines.push(
            `<a href="geo:${lat},${lon}?q=${lat},${lon}(${encodeURIComponent(name)})" ` +
            `style="display:inline-block;margin-top:6px;padding:5px 14px;` +
            `background:#1a6632;color:white;border-radius:4px;text-decoration:none;` +
            `font-weight:bold;font-size:13px;">&#x1F9ED; Navigate</a>`
        );
    }

    return lines.join('<br>');
}

// ─── Map Lifecycle ────────────────────────────────────────────────────────────
function openMapCategory(categoryId) {
    currentCategory = categoryId;

    document.getElementById('home-view').style.display = 'none';
    document.getElementById('map-view').style.display  = 'flex';
    document.getElementById('map-title').innerText = categoryTitles[categoryId] || 'Resources';

    _setInfoBox(categoryLoadingMsg[categoryId] || 'Finding your location…', 'loading');

    if (!map) {
        map = L.map('map').setView([0, 0], 2);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        }).addTo(map);
    }

    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            _onLocationSuccess,
            _onLocationError,
            { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
        );
    } else {
        _setInfoBox('Geolocation is not supported by your browser.', 'error');
    }
}

function closeMap() {
    document.getElementById('map-view').style.display  = 'none';
    document.getElementById('home-view').style.display = 'flex';

    if (userMarker) { map.removeLayer(userMarker); userMarker = null; }
    resourceMarkers.forEach(m => map.removeLayer(m));
    resourceMarkers = [];
}

function _onLocationSuccess(pos) {
    currentLat = pos.coords.latitude;
    currentLon = pos.coords.longitude;
    fetchData();
}

function _onLocationError(err) {
    console.warn(`Location error (${err.code}): ${err.message}`);
    _setInfoBox('Location access denied. Please allow location permission and try again.', 'error');
}

// ─── Radius Change ────────────────────────────────────────────────────────────
function updateRadius() {
    if (currentCategory && currentLat !== null && currentLon !== null) {
        resourceMarkers.forEach(m => map.removeLayer(m));
        resourceMarkers = [];
        fetchData();
    }
}

// ─── Core Data Fetch ──────────────────────────────────────────────────────────
function fetchData() {
    var radius = document.getElementById('radius-select').value;

    _setInfoBox(categoryLoadingMsg[currentCategory] || 'Searching…', 'loading');

    map.setView([currentLat, currentLon], 14);

    if (!userMarker) {
        userMarker = L.marker([currentLat, currentLon], { icon: icons.user })
            .addTo(map)
            .bindPopup('<b>Your Location</b>')
            .openPopup();
    }

    // For medical: fire OSM query + scraped events in parallel
    var osmFetch = fetch(`/api/${currentCategory}/?lat=${currentLat}&lon=${currentLon}&radius=${radius}`)
        .then(r => r.json());

    var eventFetch = (currentCategory === 'medical')
        ? fetch('/api/medical/events/').then(r => r.json()).catch(() => ({ elements: [] }))
        : Promise.resolve({ elements: [] });

    Promise.all([osmFetch, eventFetch])
        .then(([osmData, eventData]) => {
            if (osmData.error) {
                _setInfoBox(
                    'OSM service temporarily unavailable. Try again in a moment.',
                    'error'
                );
                return;
            }

            var osmElements   = (osmData.elements   || []).filter(el => el.lat != null && el.lon != null);
            var eventElements = (eventData.elements || []).filter(el => el.lat != null && el.lon != null);

            osmElements.forEach(el => {
                var marker = L.marker([el.lat, el.lon], { icon: _iconForElement(el) })
                    .addTo(map)
                    .bindPopup(_buildPopup(el));
                resourceMarkers.push(marker);
            });

            eventElements.forEach(el => {
                var marker = L.marker([el.lat, el.lon], { icon: icons.event })
                    .addTo(map)
                    .bindPopup(_buildPopup(el));
                resourceMarkers.push(marker);
            });

            var total = osmElements.length;
            var evtCount = eventElements.length;

            if (total === 0 && evtCount === 0) {
                _setInfoBox(
                    `No results found within ${_formatRadius(radius)}. Try expanding your search radius.`,
                    'error'
                );
            } else {
                var msg = `Found ${total} location${total !== 1 ? 's' : ''}`;
                if (evtCount > 0) msg += ` + ${evtCount} upcoming event${evtCount !== 1 ? 's' : ''}`;
                msg += ` within ${_formatRadius(radius)}.`;
                _setInfoBox(msg, 'success');
                setTimeout(() => {
                    document.getElementById('loading-info').style.display = 'none';
                }, 5000);
            }
        })
        .catch(() => {
            _setInfoBox('Network error. Please check your connection and try again.', 'error');
        });
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function _setInfoBox(msg, state) {
    var box = document.getElementById('loading-info');
    box.className = 'info-' + (state || 'loading');
    box.style.display = 'block';
    if (state === 'error') {
        // Show a Retry button so the user doesn't have to go back and reopen
        box.innerHTML =
            msg +
            ' <button onclick="fetchData()" style="margin-left:8px;padding:3px 10px;' +
            'border-radius:4px;border:none;background:#721c24;color:white;' +
            'cursor:pointer;font-size:12px;font-weight:bold;">Retry</button>';
        box.style.pointerEvents = 'auto';
    } else {
        box.innerText = msg;
        box.style.pointerEvents = state === 'loading' ? 'none' : 'auto';
    }
}

function _formatRadius(meters) {
    var m = parseInt(meters, 10);
    if (m >= 1000) return (m / 1609).toFixed(1) + ' mi';
    return m + ' m';
}
