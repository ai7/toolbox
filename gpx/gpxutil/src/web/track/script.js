var COLORS = {
    magenta: '#e6005c',
    red: '#e41a1c',
    green: '#4daf4a',
    green_bright: '#2ecc40',
    orange: '#ff7f00',
    purple: '#984ea3',
    cyan: '#42d4f4',
    pink: '#f781bf',
    brown: '#a65628',
    blue: '#377eb8'
};
var TRACK_COLORS = [COLORS.green_bright, COLORS.red, COLORS.magenta, COLORS.orange, COLORS.purple, COLORS.cyan, COLORS.pink, COLORS.brown];

var START_ICON = L.icon({
    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
    iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41]
});

var END_ICON = L.icon({
    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
    iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41]
});

function haversine(p1, p2) {
    var R = 6371000;
    var dLat = (p2[0] - p1[0]) * Math.PI / 180;
    var dLon = (p2[1] - p1[1]) * Math.PI / 180;
    var a = Math.sin(dLat/2) * Math.sin(dLat/2)
          + Math.cos(p1[0] * Math.PI / 180) * Math.cos(p2[0] * Math.PI / 180)
          * Math.sin(dLon/2) * Math.sin(dLon/2);
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
}

function computeDistances(points) {
    var distances = [0];
    for (var i = 1; i < points.length; i++) {
        distances.push(distances[i-1] + haversine(points[i-1], points[i]));
    }
    return distances;
}

function getDistanceInterval(visibleMeters) {
    var steps = [100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000];
    for (var i = 0; i < steps.length; i++) {
        if (visibleMeters / steps[i] <= 12) return steps[i];
    }
    return steps[steps.length - 1];
}

function formatDistLabel(meters) {
    var km = meters / 1000;
    if (km >= 1) return km % 1 === 0 ? km.toFixed(0) : km.toFixed(1);
    return (meters).toFixed(0) + 'm';
}

var distanceMarkers = [];

// Estimate track distance within the viewport
function getVisibleDistance(points, distances, bounds) {
    var visible = 0;
    for (var i = 1; i < points.length; i++) {
        if (bounds.contains(L.latLng(points[i][0], points[i][1]))) {
            visible += distances[i] - distances[i-1];
        }
    }
    return visible || distances[distances.length - 1];
}

// Find the lat/lon at a given cumulative distance along the track
function interpolatePointAtDistance(points, distances, targetDist) {
    for (var i = 1; i < distances.length; i++) {
        if (distances[i] >= targetDist) {
            var ratio = (targetDist - distances[i-1]) / (distances[i] - distances[i-1]);
            return [
                points[i-1][0] + ratio * (points[i][0] - points[i-1][0]),
                points[i-1][1] + ratio * (points[i][1] - points[i-1][1])
            ];
        }
    }
    return null;
}

// Build the Leaflet divIcon for a distance label
function createDistanceIcon(label) {
    return L.divIcon({
        html: '<div class="distance-marker">' + label + '</div>',
        className: '',
        iconSize: null,
        iconAnchor: [12, 8]
    });
}

// Place distance markers along tracks, adapting density to visible area
function createDistanceMarkers(map, tracks) {
    distanceMarkers.forEach(function(m) { map.removeLayer(m); });
    distanceMarkers = [];

    var bounds = map.getBounds();

    tracks.forEach(function(track) {
        // Compute distances per segment, accumulating across segments
        var allPoints = [];
        var allDistances = [];
        var cumulative = 0;
        track.segments.forEach(function(seg) {
            var points = seg.points.map(function(p) { return [p[0], p[1]]; });
            var segDist = computeDistances(points);
            for (var i = 0; i < points.length; i++) {
                allPoints.push(points[i]);
                allDistances.push(cumulative + segDist[i]);
            }
            cumulative += segDist[segDist.length - 1];
        });

        var totalDist = cumulative;
        var interval = getDistanceInterval(getVisibleDistance(allPoints, allDistances, bounds));

        for (var d = interval; d < totalDist; d += interval) {
            var pt = interpolatePointAtDistance(allPoints, allDistances, d);
            if (pt && bounds.contains(L.latLng(pt[0], pt[1]))) {
                var marker = L.marker(pt, {icon: createDistanceIcon(formatDistLabel(d)), interactive: false}).addTo(map);
                distanceMarkers.push(marker);
            }
        }
    });
}

function initializeTrackMap(tracks) {
    var map = L.map('map');

    var streetMap = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19
    });
    var topoMap = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, &copy; <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)',
        maxZoom: 17
    });
    var satelliteMap = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: '&copy; <a href="https://www.esri.com/">Esri</a>',
        maxZoom: 19
    });

    streetMap.addTo(map);

    L.control.layers({
        "Street Map": streetMap,
        "Topographic Map": topoMap,
        "Satellite": satelliteMap
    }).addTo(map);

    L.control.scale().addTo(map);

    var allBounds = L.latLngBounds();

    tracks.forEach(function(track, i) {
        var color = TRACK_COLORS[i % TRACK_COLORS.length];
        var segments = track.segments;

        // Draw each segment as a separate polyline
        segments.forEach(function(seg) {
            var latlngs = seg.points.map(function(p) { return [p[0], p[1]]; });

            L.polyline(latlngs, {
                color: '#000',
                weight: 5,
                opacity: 0.3,
                lineCap: 'round',
                lineJoin: 'round'
            }).addTo(map);

            var polyline = L.polyline(latlngs, {
                color: color,
                weight: 3,
                opacity: 1,
                lineCap: 'round',
                lineJoin: 'round'
            }).addTo(map);

            polyline.bindTooltip(track.name, {sticky: true});

            L.polylineDecorator(polyline, {
                patterns: [{
                    offset: 50,
                    repeat: 250,
                    symbol: L.Symbol.arrowHead({
                        pixelSize: 14,
                        headAngle: 40,
                        pathOptions: {color: '#fff', fillOpacity: 1, weight: 0}
                    })
                }]
            }).addTo(map);

            allBounds.extend(polyline.getBounds());
        });

        // Gap markers between segments
        for (var s = 0; s < segments.length - 1; s++) {
            var endSeg = segments[s];
            var nextSeg = segments[s + 1];
            var endPts = endSeg.points;
            var nextPts = nextSeg.points;
            var stopPt = [endPts[endPts.length - 1][0], endPts[endPts.length - 1][1]];
            var gapStartPt = [nextPts[0][0], nextPts[0][1]];

            var endPopup = '<b>Segment ' + (s + 1) + ' end</b>';
            if (endSeg.end_time) endPopup += '<br>Time: ' + endSeg.end_time;
            if (endSeg.duration) endPopup += '<br>Duration: ' + endSeg.duration;

            var startPopup = '<b>Segment ' + (s + 2) + ' start</b>';
            if (nextSeg.start_time) startPopup += '<br>Time: ' + nextSeg.start_time;
            if (nextSeg.gap_duration) {
                endPopup += '<br>Gap: ' + nextSeg.gap_duration;
                startPopup += '<br>Gap: ' + nextSeg.gap_duration;
            }

            var shortGap = nextSeg.gap_secs !== undefined && nextSeg.gap_secs < 1800;
            var dotColor = shortGap ? '#f5d000' : COLORS.red;
            var dotColor2 = shortGap ? '#f5d000' : COLORS.green;

            L.circleMarker(stopPt, {
                radius: 5, fillColor: dotColor, color: '#333',
                weight: 1, fillOpacity: 0.9
            }).addTo(map).bindPopup(endPopup);
            L.circleMarker(gapStartPt, {
                radius: 5, fillColor: dotColor2, color: '#333',
                weight: 1, fillOpacity: 0.9
            }).addTo(map).bindPopup(startPopup);
        }

        // Start and end pins use first point of first segment, last point of last segment
        var firstSeg = segments[0];
        var lastSeg = segments[segments.length - 1];
        var firstPts = firstSeg.points;
        var lastPts = lastSeg.points;
        if (firstPts && firstPts.length > 0) {
            var startPt = [firstPts[0][0], firstPts[0][1]];
            var endPt = [lastPts[lastPts.length - 1][0], lastPts[lastPts.length - 1][1]];

            var startLabel = track.start_time || track.name;
            var endLines = [];
            if (track.end_time) endLines.push(track.end_time);
            if (track.duration) endLines.push(track.duration);
            if (track.distance) endLines.push(track.distance);
            var endLabel = endLines.join('<br>') || track.name;

            L.marker(startPt, {icon: START_ICON}).addTo(map);
            L.marker(startPt, {
                icon: L.divIcon({
                    html: '<div class="pin-label">' + startLabel + '</div>',
                    className: 'pin-label-container',
                    iconSize: [0, 0],
                    iconAnchor: [0, 65]
                }),
                interactive: false
            }).addTo(map);

            L.marker(endPt, {icon: END_ICON}).addTo(map);
            L.marker(endPt, {
                icon: L.divIcon({
                    html: '<div class="pin-label">' + endLabel + '</div>',
                    className: 'pin-label-container',
                    iconSize: [0, 0],
                    iconAnchor: [0, 100]
                }),
                interactive: false
            }).addTo(map);
        }
    });

    map.fitBounds(allBounds, {padding: [20, 20]});

    createDistanceMarkers(map, tracks);
    map.on('moveend', function() { createDistanceMarkers(map, tracks); });

    if (tracks.length > 1) {
        var legend = L.control({position: 'bottomright'});
        legend.onAdd = function() {
            var div = L.DomUtil.create('div', 'track-legend');
            tracks.forEach(function(track, i) {
                var color = TRACK_COLORS[i % TRACK_COLORS.length];
                div.innerHTML += '<div class="track-legend-item">'
                    + '<span class="track-legend-line" style="background:' + color + '"></span>'
                    + '<span>' + track.name + '</span></div>';
            });
            return div;
        };
        legend.addTo(map);
    }
}
