/**
 * GPX Map Viewer - JavaScript functions for displaying coordinates on OpenStreetMap
 * Uses Leaflet.js library for map rendering
 */

function initializeMap(coordinates, centerLat, centerLon, zoomLevel) {
    // Default coordinates if none provided
    coordinates = coordinates || [];
    centerLat = centerLat || 37.7749;
    centerLon = centerLon || -122.4194;
    zoomLevel = zoomLevel || 10;
    
    // Initialize the map
    var map = L.map('map').setView([centerLat, centerLon], zoomLevel);
    
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
    
    // Note: Thunderforest Outdoors requires API key, so commented out for now
    // "Outdoors": outdoorsMap
    
    L.control.layers(baseLayers).addTo(map);
    
    // Add scale control
    L.control.scale().addTo(map);
    
    // Add markers for each coordinate
    var markers = [];
    coordinates.forEach(function(coord, index) {
        var marker = L.marker([coord.lat, coord.lon])
            .addTo(map)
            .bindPopup(coord.popup);
        markers.push(marker);
    });
    
    // If there are multiple points, fit the map to show all markers
    if (coordinates.length > 1) {
        var group = new L.featureGroup(markers);
        map.fitBounds(group.getBounds().pad(0.1));
    }
    
    console.log('Map initialized with ' + coordinates.length + ' waypoints');
}

// Additional utility functions for map interaction
function addCustomMarker(map, lat, lon, popupText, iconColor) {
    var marker = L.marker([lat, lon]).addTo(map);
    if (popupText) {
        marker.bindPopup(popupText);
    }
    return marker;
}

function fitMapToCoordinates(map, coordinates) {
    if (coordinates.length > 1) {
        var bounds = L.latLngBounds();
        coordinates.forEach(function(coord) {
            bounds.extend([coord.lat, coord.lon]);
        });
        map.fitBounds(bounds.pad(0.1));
    }
}
