const DATA_URL = "data/meetings.geojson";
// OpenFreeMap: free, unlimited, no API key, safe for a public production site.
const MAP_STYLE = "https://tiles.openfreemap.org/styles/liberty";

const DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

let allMeetings = []; // [{...properties, lat, lon}]
let userLocation = null; // {lat, lon}
let map;
let resultMarkers = [];
let userMarker = null;

const el = (id) => document.getElementById(id);
const statusLine = el("status-line");
const resultsList = el("results-list");

function setStatus(msg, isError = false) {
  statusLine.textContent = msg;
  statusLine.classList.toggle("error", isError);
}

function haversineMiles(lat1, lon1, lat2, lon2) {
  const R = 3958.8;
  const toRad = (d) => (d * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function timeToMinutes(hhmm) {
  if (!hhmm || !/^\d{1,2}:\d{2}$/.test(hhmm)) return null;
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
}

function minutesUntilNext(meeting, now) {
  const mins = timeToMinutes(meeting.time);
  if (meeting.day === null || meeting.day === undefined || mins === null) return Infinity;
  const nowDay = now.getDay();
  const nowMins = now.getHours() * 60 + now.getMinutes();
  let diffDays = (meeting.day - nowDay + 7) % 7;
  if (diffDays === 0 && mins < nowMins) diffDays = 7;
  return diffDays * 1440 + (mins - nowMins);
}

async function loadMeetings() {
  setStatus("Loading meeting data…");
  const res = await fetch(DATA_URL);
  const geojson = await res.json();
  allMeetings = geojson.features
    .filter((f) => f.geometry)
    .map((f) => ({
      ...f.properties,
      lon: f.geometry.coordinates[0],
      lat: f.geometry.coordinates[1],
    }));
  setStatus(`${allMeetings.length} meetings loaded. Enter your location to search.`);
}

async function geocode(query) {
  const url = `https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&countrycodes=us&q=${encodeURIComponent(query)}`;
  const res = await fetch(url);
  const data = await res.json();
  if (!data.length) throw new Error("Location not found — try a more specific address or ZIP.");
  return { lat: parseFloat(data[0].lat), lon: parseFloat(data[0].lon) };
}

function useMyLocation() {
  if (!navigator.geolocation) {
    setStatus("Geolocation isn't supported by your browser.", true);
    return;
  }
  setStatus("Getting your location…");
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      userLocation = { lat: pos.coords.latitude, lon: pos.coords.longitude };
      el("location-input").value = "Current location";
      runSearch();
    },
    () => setStatus("Couldn't get your location — try entering an address instead.", true)
  );
}

async function runSearch() {
  const query = el("location-input").value.trim();
  if (!userLocation && !query) {
    setStatus("Enter an address/ZIP or use the location button.", true);
    return;
  }
  el("search-btn").disabled = true;
  try {
    if (query && query !== "Current location") {
      setStatus("Looking up location…");
      userLocation = await geocode(query);
    }
    if (!userLocation) throw new Error("No location set.");

    const radius = parseFloat(el("radius-select").value);
    const when = el("when-select").value;
    const now = new Date();

    let results = allMeetings
      .map((m) => ({ ...m, distance: haversineMiles(userLocation.lat, userLocation.lon, m.lat, m.lon) }))
      .filter((m) => m.distance <= radius);

    if (when === "today" || when === "upcoming-today") {
      results = results.filter((m) => m.day === now.getDay());
    }
    if (when === "upcoming-today") {
      const nowMins = now.getHours() * 60 + now.getMinutes();
      results = results.filter((m) => {
        const t = timeToMinutes(m.time);
        return t !== null && t >= nowMins;
      });
    }

    if (when === "week") {
      results.forEach((m) => (m._sortKey = minutesUntilNext(m, now)));
      results.sort((a, b) => a._sortKey - b._sortKey || a.distance - b.distance);
    } else {
      results.sort((a, b) => a.distance - b.distance);
    }

    renderResults(results);
    renderMap(results);
    setStatus(`${results.length} meeting(s) found within ${radius} miles.`);
  } catch (err) {
    setStatus(err.message || "Search failed.", true);
  } finally {
    el("search-btn").disabled = false;
  }
}

function formatMeetingTime(m) {
  if (m.day === null || m.day === undefined || !m.time) return "Time varies — see notes";
  const [h, min] = m.time.split(":").map(Number);
  const ampm = h >= 12 ? "PM" : "AM";
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${DAY_NAMES[m.day]} · ${h12}:${String(min).padStart(2, "0")} ${ampm}`;
}

function renderResults(results) {
  resultsList.innerHTML = "";
  if (!results.length) {
    resultsList.innerHTML = `<li id="empty-state">No meetings match this search. Try a wider radius or a broader time range.</li>`;
    return;
  }
  results.forEach((m) => {
    const li = document.createElement("li");
    li.className = "result-item";
    li.innerHTML = `
      <div class="r-name">${escapeHtml(m.name)}</div>
      <div class="r-meta">${escapeHtml(m.location_name || m.address || "")}</div>
      <div class="r-meta">${formatMeetingTime(m)}</div>
      <div class="r-dist">${m.distance.toFixed(1)} mi away</div>
      <div class="r-types">${(m.types || []).map((t) => `<span class="type-badge">${escapeHtml(t)}</span>`).join("")}</div>
    `;
    li.addEventListener("click", () => {
      map.flyTo({ center: [m.lon, m.lat], zoom: 14 });
      new maplibregl.Popup().setLngLat([m.lon, m.lat]).setHTML(popupHtml(m)).addTo(map);
    });
    resultsList.appendChild(li);
  });
}

function popupHtml(m) {
  return `<strong>${escapeHtml(m.name)}</strong><br>${escapeHtml(m.location_name || m.address || "")}<br>${formatMeetingTime(m)}`;
}

function escapeHtml(str) {
  const d = document.createElement("div");
  d.textContent = str ?? "";
  return d.innerHTML;
}

// Classic teardrop pushpin, built as an inline SVG so it needs no image
// assets. `fill`/`stroke` pick the color; a CSS drop-shadow gives it some lift.
function createPinElement(fill, stroke) {
  const el = document.createElement("div");
  el.className = "map-pin";
  el.innerHTML = `
    <svg width="26" height="34" viewBox="0 0 26 34" xmlns="http://www.w3.org/2000/svg">
      <path d="M13 0C5.82 0 0 5.82 0 13c0 9.75 13 21 13 21s13-11.25 13-21C26 5.82 20.18 0 13 0z"
            fill="${fill}" stroke="${stroke}" stroke-width="1.5"/>
      <circle cx="13" cy="13" r="5" fill="#fff"/>
    </svg>
  `;
  return el;
}

function addResultMarker(m) {
  const el = createPinElement("#4ade80", "#15803d");
  el.style.cursor = "pointer";
  const marker = new maplibregl.Marker({ element: el, anchor: "bottom" })
    .setLngLat([m.lon, m.lat])
    .setPopup(new maplibregl.Popup({ offset: 28 }).setHTML(popupHtml(m)))
    .addTo(map);
  resultMarkers.push(marker);
  return marker;
}

function clearResultMarkers() {
  resultMarkers.forEach((mk) => mk.remove());
  resultMarkers = [];
}

function setUserMarker(lat, lon) {
  if (userMarker) userMarker.remove();
  const el = createPinElement("#ef4444", "#991b1b");
  userMarker = new maplibregl.Marker({ element: el, anchor: "bottom" })
    .setLngLat([lon, lat])
    .addTo(map);
}

function renderMap(results) {
  clearResultMarkers();
  results.forEach(addResultMarker);
  if (userLocation) {
    setUserMarker(userLocation.lat, userLocation.lon);
    map.flyTo({ center: [userLocation.lon, userLocation.lat], zoom: 11 });
  }
}

function initMap() {
  map = new maplibregl.Map({
    container: "map",
    style: MAP_STYLE,
    center: [-75.5, 42.9], // roughly centered on NY State
    zoom: 6,
  });
  map.addControl(new maplibregl.NavigationControl(), "top-right");
}

el("search-btn").addEventListener("click", runSearch);
el("use-location-btn").addEventListener("click", useMyLocation);
el("location-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter") runSearch();
});

initMap();
loadMeetings();
