// ─── Global State ───────────────────────────────────────────────────────────
var map = null;
var userMarker = null;
var resourceMarkers = [];

var currentCategory = null;
var currentLat = null;
var currentLon = null;

// ─── Category Config ─────────────────────────────────────────────────────────
const categoryTitles = {
    shelter:         'Emergency Shelters',
    food:            'Food Banks & Kitchens',
    medical:         'ERs & Medical Centers',
    rehab:           'Rehabilitation Centers',
    food_events:     'Food Events & Pop-Ups',
    shelter_events:  'Emergency Shelter Events',
    medical_events:  'Medical Events & Pop-Ups',
    rehab_events:    'Rehab & Recovery Events',
};

const categoryLoadingMsg = {
    shelter:         'Finding emergency shelters near you…',
    food:            'Finding food banks and kitchens near you…',
    medical:         'Finding hospitals, clinics and pharmacies near you…',
    rehab:           'Finding rehabilitation centers near you…',
    food_events:     'Finding food events and pop-ups near you…',
    shelter_events:  'Finding emergency shelter events near you…',
    medical_events:  'Finding medical events and pop-ups near you…',
    rehab_events:    'Finding rehab and recovery events near you…',
};

// Event-only categories: map category ID → dedicated API endpoint
const eventEndpoints = {
    food_events:    '/api/food/events/',
    shelter_events: '/api/shelter/events/',
    medical_events: '/api/medical/events/',
    rehab_events:   '/api/rehab/events/',
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
    user:     _makeIcon('violet'),
    medical:  _makeIcon('red'),
    event:    _makeIcon('orange'),
    verified: _makeIcon('green'),
    default:  _makeIcon('blue'),
};

function _iconForElement(element) {
    if (element.type === 'event') return icons.event;
    if ((element.tags || {}).source_label === '211 NC') return icons.verified;
    if (currentCategory === 'medical') return icons.medical;
    return icons.default;
}

// ─── Distance Helpers ─────────────────────────────────────────────────────────
// Haversine formula — returns distance in miles between two lat/lon points.
function _haversineMiles(lat1, lon1, lat2, lon2) {
    var R = 3958.8; // Earth radius in miles
    var dLat = (lat2 - lat1) * Math.PI / 180;
    var dLon = (lon2 - lon1) * Math.PI / 180;
    var a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);
    var c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
}

function _formatDistance(miles) {
    if (miles < 0.1) return Math.round(miles * 5280) + ' ft away';
    if (miles < 10)  return miles.toFixed(1) + ' mi away';
    return Math.round(miles) + ' mi away';
}

// ─── Opening Hours Parser ─────────────────────────────────────────────────────
// Parses the most common OSM opening_hours format: "Mo-Fr 09:00-17:00"
// Returns "open" | "closed" | null (null = unable to parse reliably)
function _parseOpenStatus(ohStr) {
    if (!ohStr) return null;
    // Handle "24/7"
    if (ohStr.trim() === '24/7') return 'open';

    var dayMap = { Mo: 1, Tu: 2, We: 3, Th: 4, Fr: 5, Sa: 6, Su: 0 };
    var now = new Date();
    var todayDow = now.getDay();   // 0=Sun, 1=Mon ... 6=Sat
    var nowMins  = now.getHours() * 60 + now.getMinutes();

    // Support multiple semicolon-separated rules; try each
    var rules = ohStr.split(';');
    for (var ri = 0; ri < rules.length; ri++) {
        var rule = rules[ri].trim();
        // Match pattern: "Mo-Fr 09:00-17:00" or "Mo 09:00-17:00"
        var m = rule.match(/^([A-Z][a-z])(?:-([A-Z][a-z]))?\s+(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})$/);
        if (!m) continue;

        var startDay = dayMap[m[1]];
        var endDay   = m[2] ? dayMap[m[2]] : startDay;
        if (startDay === undefined || endDay === undefined) continue;

        // Check if today falls in day range (handles Mo-Fr = 1-5, not wrap-around)
        var inDay = false;
        if (startDay <= endDay) {
            inDay = (todayDow >= startDay && todayDow <= endDay);
        } else {
            // wrap-around like Fr-Mo
            inDay = (todayDow >= startDay || todayDow <= endDay);
        }
        if (!inDay) continue;

        var openMins  = parseInt(m[3], 10) * 60 + parseInt(m[4], 10);
        var closeMins = parseInt(m[5], 10) * 60 + parseInt(m[6], 10);
        if (nowMins >= openMins && nowMins < closeMins) return 'open';
        return 'closed';
    }
    return null;   // format too complex or no rule matched today
}

// ─── Popup Builder ────────────────────────────────────────────────────────────
function _buildPopup(element) {
    var tags = element.tags || {};
    var lat  = element.lat;
    var lon  = element.lon;

    // Prefer tags.name; fall back to tags.operator; show operator as subtitle when both exist
    var name = tags.name || tags.operator || 'Unnamed Location';
    var lines = [`<b>${name}</b>`];
    if (tags.name && tags.operator && tags.operator !== tags.name) {
        lines.push(`<small style="color:#666;">${tags.operator}</small>`);
    }

    // Distance from user location — shown only when user position is known
    if (currentLat !== null && currentLon !== null && lat != null && lon != null) {
        var miles = _haversineMiles(currentLat, currentLon, lat, lon);
        lines.push(`<small style="color:#555;">${_formatDistance(miles)}</small>`);
    }

    // Address — compose from OSM addr:* tags if present
    var addrParts = [tags['addr:housenumber'], tags['addr:street']].filter(Boolean);
    var addrStr = '';
    if (addrParts.length) {
        addrStr = addrParts.join(' ');
        if (tags['addr:city']) addrStr += ', ' + tags['addr:city'];
    } else if (tags.address) {
        addrStr = tags.address;
    }
    if (addrStr) {
        // Tap-to-copy button for address
        var safeAddr = addrStr.replace(/'/g, "\\'");
        lines.push(
            addrStr +
            ` <button onclick="navigator.clipboard.writeText('${safeAddr}').catch(()=>{})" ` +
            `title="Copy address" ` +
            `style="background:none;border:1px solid #aaa;border-radius:3px;` +
            `padding:1px 5px;font-size:11px;cursor:pointer;vertical-align:middle;` +
            `margin-left:4px;">Copy</button>`
        );
    }

    // Hours — from OSM opening_hours tag if present
    if (tags.opening_hours) {
        var status = _parseOpenStatus(tags.opening_hours);
        var badge = '';
        if (status === 'open') {
            badge = ' <span style="background:#28a745;color:white;border-radius:3px;' +
                    'padding:1px 6px;font-size:11px;font-weight:bold;">Open Now</span>';
        } else if (status === 'closed') {
            badge = ' <span style="background:#6c757d;color:white;border-radius:3px;' +
                    'padding:1px 6px;font-size:11px;font-weight:bold;">Closed</span>';
        }
        lines.push(`<small>&#x1F551; ${tags.opening_hours}${badge}</small>`);
    }

    // Scraped event extras
    if (element.type === 'event') {
        if (tags.event_date) lines.push(`&#x1F4C5; ${tags.event_date}`);
        if (tags.source)     lines.push(`<i>Source: ${tags.source}</i>`);
        if (tags.source_url) lines.push(`<a href="${tags.source_url}" target="_blank" rel="noopener">View event</a>`);
    }

    // Action buttons row — Call and Navigate side by side when both are available.
    // maps.apple.com is intercepted by Apple Maps on iOS; other platforms redirect
    // to Google Maps / the default navigation app — universally reliable without UA sniffing.
    var actionBtns = [];
    if (tags.phone) {
        actionBtns.push(
            `<a href="tel:${tags.phone}" ` +
            `style="display:inline-block;padding:6px 14px;` +
            `background:#1a529c;color:white;border-radius:4px;text-decoration:none;` +
            `font-weight:bold;font-size:13px;">&#x1F4DE; Call</a>`
        );
    }
    if (lat != null && lon != null) {
        var mapsUrl = `https://maps.apple.com/?q=${encodeURIComponent(name)}&ll=${lat},${lon}&t=m`;
        actionBtns.push(
            `<a href="${mapsUrl}" target="_blank" rel="noopener" ` +
            `style="display:inline-block;padding:6px 14px;` +
            `background:#1a6632;color:white;border-radius:4px;text-decoration:none;` +
            `font-weight:bold;font-size:13px;">&#x1F9ED; Navigate</a>`
        );
    }
    if (actionBtns.length) {
        lines.push(
            `<div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap;">${actionBtns.join('')}</div>`
        );
    }

    // Website link — shown below action buttons if tag is present
    if (tags.website) {
        lines.push(
            `<div style="margin-top:6px;"><a href="${tags.website}" target="_blank" rel="noopener" ` +
            `style="font-size:13px;">Website</a></div>`
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

    // Show share button only on devices/browsers that support Web Share API
    var shareBtn = document.getElementById('share-btn');
    if (shareBtn) shareBtn.style.display = navigator.share ? 'inline-flex' : 'none';

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
    _handleLocationDenied();
}

function _handleLocationDenied() {
    var box = document.getElementById('loading-info');
    box.className = 'info-error';
    box.style.display = 'block';
    box.style.pointerEvents = 'auto';
    box.innerHTML =
        'Location access denied.' +
        '<div style="margin-top:8px;display:flex;gap:6px;align-items:center;flex-wrap:wrap;">' +
        '<input type="text" id="zip-input" placeholder="Enter zip code" maxlength="10" ' +
        'style="padding:5px 8px;border:1px solid #ccc;border-radius:4px;font-size:14px;' +
        'width:130px;box-sizing:border-box;" ' +
        'onkeydown="if(event.key===\'Enter\')_geocodeZip(this.value.trim())">' +
        '<button onclick="_geocodeZip(document.getElementById(\'zip-input\').value.trim())" ' +
        'style="padding:5px 14px;background:#1a529c;color:white;border:none;border-radius:4px;' +
        'font-size:14px;font-weight:bold;cursor:pointer;">Go</button>' +
        '</div>';
}

function _geocodeZip(zip) {
    if (!zip) return;
    var box = document.getElementById('loading-info');
    box.className = 'info-loading';
    box.style.display = 'flex';
    box.style.pointerEvents = 'none';
    box.innerHTML = '<span class="spinner" aria-hidden="true"></span><span>Looking up zip code…</span>';

    fetch('https://nominatim.openstreetmap.org/search?q=' + encodeURIComponent(zip) +
          '&format=json&limit=1&countrycodes=us')
        .then(function(r) { return r.json(); })
        .then(function(results) {
            if (!results || results.length === 0) {
                box.className = 'info-error';
                box.style.display = 'block';
                box.style.pointerEvents = 'auto';
                box.innerHTML =
                    'Zip code not found. Try again.' +
                    '<div style="margin-top:8px;display:flex;gap:6px;align-items:center;flex-wrap:wrap;">' +
                    '<input type="text" id="zip-input" placeholder="Enter zip code" maxlength="10" ' +
                    'style="padding:5px 8px;border:1px solid #ccc;border-radius:4px;font-size:14px;' +
                    'width:130px;box-sizing:border-box;" ' +
                    'onkeydown="if(event.key===\'Enter\')_geocodeZip(this.value.trim())">' +
                    '<button onclick="_geocodeZip(document.getElementById(\'zip-input\').value.trim())" ' +
                    'style="padding:5px 14px;background:#1a529c;color:white;border:none;border-radius:4px;' +
                    'font-size:14px;font-weight:bold;cursor:pointer;">Go</button>' +
                    '</div>';
                return;
            }
            currentLat = parseFloat(results[0].lat);
            currentLon = parseFloat(results[0].lon);
            fetchData();
        })
        .catch(function() {
            _setInfoBox('Could not reach geocoding service. Check your connection and try again.', 'error');
        });
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

    // For event-only categories (food_events, shelter_events): fetch dedicated endpoint, no OSM query.
    // For medical: fire OSM query + scraped events in parallel.
    // For all others: OSM only.
    var eventsOnlyEndpoint = eventEndpoints[currentCategory];

    var osmFetch = eventsOnlyEndpoint
        ? Promise.resolve({ elements: [] })
        : fetch(`/api/${currentCategory}/?lat=${currentLat}&lon=${currentLon}&radius=${radius}`)
            .then(r => r.json());

    var eventFetch = eventsOnlyEndpoint
        ? fetch(eventsOnlyEndpoint).then(r => r.json()).catch(() => ({ elements: [] }))
        : (currentCategory === 'medical')
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

            // Sort by distance (closest first) so nearest pins are rendered on top
            function _byDistance(a, b) {
                if (currentLat === null || currentLon === null) return 0;
                return _haversineMiles(currentLat, currentLon, a.lat, a.lon) -
                       _haversineMiles(currentLat, currentLon, b.lat, b.lon);
            }
            osmElements.sort(_byDistance);
            eventElements.sort(_byDistance);

            osmElements.forEach(el => {
                var marker = L.marker([el.lat, el.lon], { icon: _iconForElement(el) })
                    .addTo(map)
                    .bindPopup(_buildPopup(el));
                marker.on('click', function() { map.panTo([el.lat, el.lon]); });
                resourceMarkers.push(marker);
            });

            eventElements.forEach(el => {
                var marker = L.marker([el.lat, el.lon], { icon: _iconForElement(el) })
                    .addTo(map)
                    .bindPopup(_buildPopup(el));
                marker.on('click', function() { map.panTo([el.lat, el.lon]); });
                resourceMarkers.push(marker);
            });

            // Auto-fit map to show all results
            if (resourceMarkers.length > 0) {
                var group = L.featureGroup(resourceMarkers);
                map.fitBounds(group.getBounds().pad(0.15));
            }

            var total = osmElements.length;
            var evtCount = eventElements.length;

            if (total === 0 && evtCount === 0) {
                var catLabel = categoryTitles[currentCategory] || 'resources';
                _setInfoBox(
                    `No ${catLabel} found nearby. Try a larger radius using the dropdown above.`,
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

// ─── Web Share ────────────────────────────────────────────────────────────────
function shareCurrentView() {
    if (!navigator.share) return;
    var title = categoryTitles[currentCategory] || 'Survival Resources';
    navigator.share({
        title: title + ' near me',
        text: 'Find ' + title.toLowerCase() + ' nearby — no sign-up required.',
        url: window.location.href,
    }).catch(function() {
        // User cancelled or share failed — silent fail is fine
    });
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function _setInfoBox(msg, state) {
    var box = document.getElementById('loading-info');
    box.className = 'info-' + (state || 'loading');
    box.style.display = state === 'loading' ? 'flex' : 'block';
    if (state === 'error') {
        // Show a Retry button so the user doesn't have to go back and reopen
        box.innerHTML =
            msg +
            ' <button onclick="fetchData()" style="margin-left:8px;padding:3px 10px;' +
            'border-radius:4px;border:none;background:#721c24;color:white;' +
            'cursor:pointer;font-size:12px;font-weight:bold;">Retry</button>';
        box.style.pointerEvents = 'auto';
    } else if (state === 'loading') {
        // Spinner + text during Overpass fetch (can take 5-15 s)
        box.innerHTML = '<span class="spinner" aria-hidden="true"></span>' +
            '<span>' + msg + '</span>';
        box.style.pointerEvents = 'none';
    } else {
        box.innerText = msg;
        box.style.pointerEvents = 'auto';
    }
}

function _formatRadius(meters) {
    var m = parseInt(meters, 10);
    if (m >= 1000) return (m / 1609).toFixed(1) + ' mi';
    return m + ' m';
}

// ─── Service Worker Registration ──────────────────────────────────────────────
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('/sw.js', { scope: '/' })
            .catch(function(err) {
                console.warn('[SW] Registration failed:', err);
            });
    });
}
