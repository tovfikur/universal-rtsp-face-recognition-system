console.log("[Timeline] Script loading...");

const ui = {
  eventsList: document.getElementById("eventsList"),
  eventCount: document.getElementById("eventCount"),
  searchInput: document.getElementById("searchInput"),
  alertContainer: document.getElementById("alertContainer"),
  refreshTimelineBtn: document.getElementById("refreshTimelineBtn"),
  clearEventsBtn: document.getElementById("clearEventsBtn"),
};

const state = {
  events: [],
  filteredEvents: [],
};

// Show alert notification
const showAlert = (message, type = "success", timeout = 4000) => {
  const alert = document.createElement("div");
  alert.className = `floating-alert ${type === "error" ? "error" : "success"}`;
  alert.textContent = message;
  ui.alertContainer.appendChild(alert);

  setTimeout(() => {
    alert.style.opacity = "0";
    setTimeout(() => alert.remove(), 400);
  }, timeout);
};

// Fetch events from API
const fetchEvents = async (silent = false) => {
  try {
    const response = await fetch("/api/events");
    if (!response.ok) throw new Error("Failed to load events");
    const data = await response.json();

    state.events = data.events || [];
    state.filteredEvents = state.events;
    renderEvents();

    if (!silent) {
      showAlert("Timeline refreshed successfully");
    }
  } catch (error) {
    if (!silent) {
      console.error("Event fetch error:", error);
      showAlert("Failed to load timeline events", "error");
    }
  }
};

// Render events to timeline
const renderEvents = () => {
  const fragment = document.createDocumentFragment();

  if (!state.filteredEvents.length) {
    const li = document.createElement("li");
    li.className = "timeline-empty";
    li.innerHTML = `
      <i class="fas fa-info-circle"></i>
      <span>No events found.</span>
    `;
    fragment.appendChild(li);
  } else {
    state.filteredEvents.forEach((event) => {
      const li = document.createElement("li");
      li.className = "timeline-item";

      const timestamp = new Date(event.timestamp);
      const timeString = timestamp.toLocaleTimeString();
      const dateString = timestamp.toLocaleDateString();

      li.innerHTML = `
        <div class="timeline-item-content">
          <strong>${event.name}</strong>
          <p class="mb-0 text-muted small">
            Confidence: ${(event.confidence * 100).toFixed(0)}% • ${dateString}
          </p>
        </div>
        <span class="timeline-badge">${timeString}</span>
      `;
      fragment.appendChild(li);
    });
  }

  ui.eventsList.innerHTML = "";
  ui.eventsList.appendChild(fragment);

  // Update count
  if (ui.eventCount) {
    ui.eventCount.textContent = state.filteredEvents.length;
  }
};

// Search/filter events
const filterEvents = () => {
  const searchTerm = ui.searchInput.value.toLowerCase().trim();

  if (!searchTerm) {
    state.filteredEvents = state.events;
  } else {
    state.filteredEvents = state.events.filter(event =>
      event.name.toLowerCase().includes(searchTerm)
    );
  }

  renderEvents();
};

// Clear all events
const clearEvents = async () => {
  if (!confirm("Are you sure you want to clear all events?")) return;

  // Clear local state
  state.events = [];
  state.filteredEvents = [];
  renderEvents();
  showAlert("Timeline cleared");
};

// Event listeners
if (ui.refreshTimelineBtn) {
  ui.refreshTimelineBtn.addEventListener("click", () => fetchEvents(false));
}

if (ui.clearEventsBtn) {
  ui.clearEventsBtn.addEventListener("click", clearEvents);
}

if (ui.searchInput) {
  ui.searchInput.addEventListener("input", filterEvents);
}

// Auto-refresh every 3 seconds
setInterval(() => fetchEvents(true), 3000);

// Initial load
fetchEvents(true);

console.log("[Timeline] Script loaded successfully");
