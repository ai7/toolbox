/**
 * Waypoint filtering — date range parsing and search logic.
 * Supports the same syntax as the CLI --date option:
 *
 *   Partial dates:    2025, 2025-04, 2025-04-23
 *   Explicit range:   2025-04..2025-06
 *   Open-ended:       2024.., ..2023
 *   Relative offset:  2025-04-01..7d, 7d..2025-04-15
 *   Suffixes:         d=days, w=weeks, m=months, y=years
 *
 * Search box prefix:  d:RANGE for date filtering, plain text for name.
 * Multiple d: terms are OR'd; name and date are AND'd.
 */

function parseDateRange(expr) {
    function daysInMonth(year, month) {
        return new Date(year, month, 0).getDate();
    }
    function expandPartial(s) {
        if (/^\d{4}$/.test(s)) {
            return { start: s + '-01-01', end: s + '-12-31' };
        } else if (/^\d{4}-\d{2}$/.test(s)) {
            var y = parseInt(s.slice(0, 4)), m = parseInt(s.slice(5, 7));
            var last = daysInMonth(y, m);
            return { start: s + '-01', end: s + '-' + (last < 10 ? '0' : '') + last };
        } else {
            return { start: s, end: s };
        }
    }
    function isRelative(s) { return /^\d+[dwmy]$/.test(s); }
    function addOffset(dateStr, offset) {
        var m = offset.match(/^(\d+)([dwmy])$/);
        var n = parseInt(m[1]), unit = m[2];
        var d = new Date(dateStr + 'T00:00:00');
        if (unit === 'd') d.setDate(d.getDate() + n);
        else if (unit === 'w') d.setDate(d.getDate() + n * 7);
        else if (unit === 'm') d.setMonth(d.getMonth() + n);
        else if (unit === 'y') d.setFullYear(d.getFullYear() + n);
        return d.toISOString().slice(0, 10);
    }
    function subOffset(dateStr, offset) {
        var m = offset.match(/^(\d+)([dwmy])$/);
        var n = parseInt(m[1]), unit = m[2];
        var d = new Date(dateStr + 'T00:00:00');
        if (unit === 'd') d.setDate(d.getDate() - n);
        else if (unit === 'w') d.setDate(d.getDate() - n * 7);
        else if (unit === 'm') d.setMonth(d.getMonth() - n);
        else if (unit === 'y') d.setFullYear(d.getFullYear() - n);
        return d.toISOString().slice(0, 10);
    }

    if (expr.indexOf('..') !== -1) {
        var parts = expr.split('..', 2);
        var left = parts[0], right = parts[1];
        if (!left && !right) return null;
        if (!left) return { start: null, end: expandPartial(right).end };
        if (!right) return { start: expandPartial(left).start, end: null };
        if (!isRelative(left) && !isRelative(right)) {
            return { start: expandPartial(left).start, end: expandPartial(right).end };
        } else if (!isRelative(left) && isRelative(right)) {
            var s = expandPartial(left).start;
            return { start: s, end: addOffset(s, right) };
        } else if (isRelative(left) && !isRelative(right)) {
            var e = expandPartial(right).end;
            return { start: subOffset(e, left), end: e };
        }
        return null;
    } else {
        var p = expandPartial(expr);
        return { start: p.start, end: p.end };
    }
}

function filterWaypoints(query) {
    /**
     * Filter waypoints by search query. Supports prefixes:
     *   d:RANGE   — date filter (same syntax as CLI --date)
     *   l:TERM    — location filter (matches LvL4 code, country code, or city)
     *   plain text — name filter
     *
     * Multiple d: and l: terms are OR'd within their type, AND'd across types.
     */
    var items = document.querySelectorAll('#waypoint-list li');
    var dateRanges = [];
    var locationTerms = [];

    var remaining = query.replace(/d:(\S+)/g, function(_, expr) {
        var range = parseDateRange(expr);
        if (range) dateRanges.push(range);
        return '';
    }).replace(/l:"([^"]+)"/g, function(_, term) {
        locationTerms.push(term.toLowerCase());
        return '';
    }).replace(/l:(\S+)/g, function(_, term) {
        locationTerms.push(term.toLowerCase());
        return '';
    }).trim().toLowerCase();

    var visibleSet = new Set();
    items.forEach(function(item) {
        var name = item.getAttribute('data-name');
        var dateVal = item.getAttribute('data-date');
        var lvl4 = item.getAttribute('data-lvl4');
        var countryCode = item.getAttribute('data-country-code');
        var state = item.getAttribute('data-state');
        var city = item.getAttribute('data-city');
        var index = parseInt(item.getAttribute('data-index'));

        var nameMatch = !remaining || name.indexOf(remaining) !== -1;

        var dateMatch = dateRanges.length === 0 || dateRanges.some(function(r) {
            if (!dateVal) return false;
            return (r.start === null || dateVal >= r.start) &&
                   (r.end === null || dateVal <= r.end);
        });

        var locationMatch = locationTerms.length === 0 || locationTerms.some(function(term) {
            return (lvl4 && lvl4.indexOf(term) !== -1) ||
                   (countryCode && countryCode.indexOf(term) !== -1) ||
                   (state && state.indexOf(term) !== -1) ||
                   (city && city.indexOf(term) !== -1);
        });

        var visible = nameMatch && dateMatch && locationMatch;
        item.style.display = visible ? '' : 'none';
        if (visible) visibleSet.add(index);
    });

    var title = document.getElementById('waypoint-panel-title');
    if (title) {
        if (visibleSet.size < mapState.data.length) {
            title.textContent = 'Waypoints (' + visibleSet.size + '/' + mapState.data.length + ')';
        } else {
            title.textContent = 'Waypoints (' + mapState.data.length + ')';
        }
    }

    updateMapMarkerVisibility(visibleSet);
}

function updateMapMarkerVisibility(visibleSet) {
    if (!mapState.map || !mapState.markers.length) return;

    var isFiltered = visibleSet.size < mapState.data.length;
    mapState.filteredIndices = isFiltered ? visibleSet : null;

    createMarkersForZoom(mapState.map.getZoom());

    if (isFiltered) {
        var bounds = L.latLngBounds();
        visibleSet.forEach(function(i) {
            var coord = mapState.data[i];
            bounds.extend([coord.lat, coord.lon]);
        });
        if (bounds.isValid()) {
            mapState.map.fitBounds(bounds.pad(0.1));
        }
    }
}
