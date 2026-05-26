/**
 * GPX Map Viewer - JavaScript functions for displaying coordinates on OpenStreetMap
 * Uses Leaflet.js library for map rendering
 */

// Configuration constants
var LABEL_ZOOM_THRESHOLD = 13; // Show labels when zoom >= this level

// Mutable application state
var mapState = {
    markers: [],          // current Leaflet marker objects
    data: [],             // coordinates data from Python
    map: null,            // Leaflet map instance
    pulseMarker: null,    // pulsing ring overlay for selected waypoint
    filteredIndices: null, // null = show all, Set = show only these indices
    sortMode: 0,          // current sort mode index
    selectedIndex: -1     // currently selected waypoint index
};

function initializeMap(coordinates, centerLat, centerLon, zoomLevel) {
    // Default coordinates if none provided
    coordinates = coordinates || [];
    centerLat = centerLat || 37.7749;
    centerLon = centerLon || -122.4194;
    zoomLevel = zoomLevel || 10;

    // Store coordinates and map globally for zoom event handling
    mapState.data = coordinates;

    // Initialize the map
    var map = L.map('map').setView([centerLat, centerLon], zoomLevel);
    mapState.map = map;

    // Define base layers
    var streetMap = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19
    });

    var topoMap = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, © <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: © <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)',
        maxZoom: 17
    });

    var satelliteMap = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
        maxZoom: 19
    });

    // Add default layer (street map)
    streetMap.addTo(map);

    // Create layer control
    var baseLayers = {
        "Street Map": streetMap,
        "Topographic Map": topoMap,
        "Satellite": satelliteMap,
    };

    L.control.layers(baseLayers).addTo(map);

    // Add scale control
    L.control.scale().addTo(map);

    // Add zoom event listener for dynamic marker switching
    map.on('zoomend', function() {
        var currentZoom = map.getZoom();
        updateMarkersForZoom(currentZoom);
    });

    // Inject copy icon SVG into popup buttons when opened
    map.on('popupopen', function(e) {
        var btns = e.popup.getElement().querySelectorAll('.copy-btn');
        btns.forEach(function(btn) {
            if (!btn.innerHTML) btn.innerHTML = COPY_ICON_SVG;
        });
    });

    // Create initial markers based on current zoom level
    var initialZoom = map.getZoom();
    createMarkersForZoom(initialZoom);

    // If there are multiple points, fit the map to show all markers
    if (coordinates.length > 1) {
        var group = new L.featureGroup(mapState.markers);
        map.fitBounds(group.getBounds().pad(0.1));
    }

    // Create waypoint list panel
    createWaypointPanel();

    console.log('Map initialized with ' + coordinates.length + ' waypoints');
    console.log('Label threshold: zoom >= ' + LABEL_ZOOM_THRESHOLD);
}

// Marker creation functions
function createSimpleMarker(coord) {
    var marker = L.marker([coord.lat, coord.lon])
        .bindTooltip(coord.name)
        .bindPopup(coord.popup, {maxWidth: 500});
    return marker;
}

function createLabeledMarker(coord) {
    // Create the standard marker first (this ensures perfect positioning)
    var marker = L.marker([coord.lat, coord.lon])
        .bindPopup(coord.popup, {maxWidth: 500});

    // Add a custom label above the marker using a separate div
    var labelHtml = '<div class="waypoint-label-overlay">' + coord.name + '</div>';

    var labelIcon = L.divIcon({
        html: labelHtml,
        className: 'waypoint-label-container',
        iconSize: null,
        iconAnchor: [50, 65],
        popupAnchor: [0, -65]
    });

    // Create a separate marker for the label positioned slightly above the main marker
    var labelMarker = L.marker([coord.lat, coord.lon], { icon: labelIcon })
        .bindPopup(coord.popup, {maxWidth: 500});

    // Return a marker group containing both the pin and label
    var markerGroup = L.layerGroup([marker, labelMarker]);
    return markerGroup;
}

function clearAllMarkers() {
    mapState.markers.forEach(function(marker) {
        mapState.map.removeLayer(marker);
    });
    mapState.markers = [];
}

function createMarkersForZoom(zoomLevel) {
    clearAllMarkers();

    var useLabels = zoomLevel >= LABEL_ZOOM_THRESHOLD;

    mapState.data.forEach(function(coord, i) {
        var marker = useLabels ? createLabeledMarker(coord) : createSimpleMarker(coord);
        if (!mapState.filteredIndices || mapState.filteredIndices.has(i)) {
            marker.addTo(mapState.map);
        }
        mapState.markers.push(marker);
    });

    console.log('Created ' + mapState.markers.length + ' markers with labels: ' + useLabels);
}

function updateMarkersForZoom(zoomLevel) {
    var shouldUseLabels = zoomLevel >= LABEL_ZOOM_THRESHOLD;
    var currentlyUsingLabels = mapState.markers.length > 0 &&
                               mapState.markers[0].getLayers &&
                               mapState.markers[0].getLayers().length > 1; // Layer group has both marker and label

    // Only recreate markers if the label state needs to change
    if (shouldUseLabels !== currentlyUsingLabels) {
        createMarkersForZoom(zoomLevel);
    }
}

var COPY_ICON_SVG = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">'
    + '<rect x="9" y="9" width="13" height="13" rx="2"/>'
    + '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>';

function copyToClipboard(text, el) {
    navigator.clipboard.writeText(text);
    el.innerHTML = '✓';
    setTimeout(function() { el.innerHTML = COPY_ICON_SVG; }, 1500);
}

function buildListItemHtml(coord, i) {
    var time = coord.time ? '<div class="waypoint-list-time">' + coord.time + '</div>' : '';
    var locText = [coord.city, coord.state, coord.country].filter(Boolean).join(', ');
    if (locText && coord.lvl4) locText += ' (' + coord.lvl4 + ')';
    var loc = locText ? '<div class="waypoint-list-location">' + locText + '</div>' : '';

    var attrs = {
        'data-index': i,
        'data-name': coord.name.toLowerCase(),
        'data-date': coord.date || '',
        'data-lvl4': (coord.lvl4 || '').toLowerCase(),
        'data-country-code': (coord.country_code || '').toLowerCase(),
        'data-state': (coord.state || '').toLowerCase(),
        'data-city': (coord.city || '').toLowerCase()
    };
    var attrStr = Object.keys(attrs).map(function(k) {
        return k + '="' + attrs[k] + '"';
    }).join(' ');

    return '<li ' + attrStr + ' onclick="flyToWaypoint(' + i + ')">'
        + '<div class="waypoint-list-name">' + coord.name + '</div>'
        + loc + time + '</li>';
}

function createWaypointPanel() {
    var panel = document.createElement('div');
    panel.className = 'waypoint-panel';
    panel.id = 'waypoint-panel';

    var header = [
        '<div class="waypoint-panel-header">',
        '  <h3 id="waypoint-panel-title">Waypoints (' + mapState.data.length + ')</h3>',
        '  <button class="waypoint-panel-close" onclick="toggleWaypointPanel()">✕</button>',
        '</div>',
        '<div class="waypoint-panel-search">',
        '  <input type="text" id="waypoint-search"',
        '    placeholder="Search (name, d:2025-04, l:ca-bc) ⏎"',
        '    onkeydown="if(event.key===\'Enter\')filterWaypoints(this.value)">',
        '  <button id="sort-btn" class="waypoint-sort-btn" onclick="cycleSortMode()">Sort: Original</button>',
        '</div>'
    ].join('');

    var list = '<ul class="waypoint-list" id="waypoint-list">';
    mapState.data.forEach(function(coord, i) {
        list += buildListItemHtml(coord, i);
    });
    list += '</ul>';

    panel.innerHTML = header + list;
    document.body.appendChild(panel);

    // Add list button to map
    var ListControl = L.Control.extend({
        options: { position: 'topright' },
        onAdd: function() {
            var btn = L.DomUtil.create('div', 'leaflet-control-list-btn');
            btn.innerHTML = '☰';
            btn.title = 'Waypoint list';
            L.DomEvent.disableClickPropagation(btn);
            btn.onclick = toggleWaypointPanel;
            return btn;
        }
    });
    mapState.map.addControl(new ListControl());
}

function toggleWaypointPanel() {
    var panel = document.getElementById('waypoint-panel');
    var mapContainer = document.getElementById('map');
    panel.classList.toggle('open');
    if (panel.classList.contains('open')) {
        mapContainer.style.width = 'calc(100% - 350px)';
    } else {
        mapContainer.style.width = '100%';
    }
    mapState.map.invalidateSize();
}

var sortModes = ['Original', 'Name', 'Time'];

function cycleSortMode() {
    mapState.sortMode = (mapState.sortMode + 1) % sortModes.length;
    document.getElementById('sort-btn').textContent = 'Sort: ' + sortModes[mapState.sortMode];
    renderWaypointList();
}

function getSortedIndices() {
    var indices = mapState.data.map(function(_, i) { return i; });
    if (sortModes[mapState.sortMode] === 'Name') {
        indices.sort(function(a, b) {
            return mapState.data[a].name.localeCompare(mapState.data[b].name);
        });
    } else if (sortModes[mapState.sortMode] === 'Time') {
        indices.sort(function(a, b) {
            var timeA = mapState.data[a].time || '';
            var timeB = mapState.data[b].time || '';
            return timeA.localeCompare(timeB);
        });
    }
    return indices;
}

function renderWaypointList() {
    var list = document.getElementById('waypoint-list');
    var indices = getSortedIndices();
    var html = '';
    indices.forEach(function(i) {
        html += buildListItemHtml(mapState.data[i], i);
    });
    list.innerHTML = html;
    // Re-apply selection highlight
    if (mapState.selectedIndex >= 0) {
        var selected = document.querySelector('#waypoint-list li[data-index="' + mapState.selectedIndex + '"]');
        if (selected) selected.classList.add('selected');
    }
    // Re-apply search filter if active
    var query = document.getElementById('waypoint-search').value;
    if (query) {
        filterWaypoints(query);
    }
}


function flyToWaypoint(index) {
    // Highlight selected item in list
    mapState.selectedIndex = index;
    var items = document.querySelectorAll('#waypoint-list li');
    items.forEach(function(item) { item.classList.remove('selected'); });
    var selected = document.querySelector('#waypoint-list li[data-index="' + index + '"]');
    if (selected) selected.classList.add('selected');

    var coord = mapState.data[index];

    // Remove previous pulse ring, add new one at selected waypoint
    if (mapState.pulseMarker) {
        mapState.map.removeLayer(mapState.pulseMarker);
    }
    var pulseIcon = L.divIcon({
        className: '',
        html: '<div class="marker-pulse"></div>',
        iconSize: [20, 20],
        iconAnchor: [10, 10]
    });
    mapState.pulseMarker = L.marker([coord.lat, coord.lon], { icon: pulseIcon, interactive: false });
    mapState.pulseMarker.addTo(mapState.map);

    mapState.map.flyTo([coord.lat, coord.lon], 15);
}

