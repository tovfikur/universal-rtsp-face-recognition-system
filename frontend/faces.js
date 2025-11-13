console.log("[Faces] Script loading...");

// UI Elements
const ui = {
    faceGallery: document.getElementById("faceGallery"),
    searchInput: document.getElementById("searchInput"),
    totalCount: document.getElementById("totalCount"),
    refreshBtn: document.getElementById("refreshFacesBtn"),
    clearAllBtn: document.getElementById("clearAllBtn"),
    alertContainer: document.getElementById("alertContainer"),
};

// State
const state = {
    faces: [],
    filteredFaces: [],
};

// Utility Functions
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

// Fetch registered faces from backend
const fetchFaces = async () => {
    try {
        const response = await fetch("/api/faces");
        if (!response.ok) throw new Error("Failed to fetch faces");

        const data = await response.json();
        state.faces = data.faces || [];
        state.filteredFaces = state.faces;

        renderFaces();
        updateCount();
    } catch (error) {
        console.error("Error fetching faces:", error);
        showAlert("Failed to load registered faces", "error");
    }
};

// Update face count
const updateCount = () => {
    if (ui.totalCount) {
        ui.totalCount.textContent = state.filteredFaces.length;
    }
};

// Render faces in grid
const renderFaces = () => {
    if (!ui.faceGallery) return;

    // Clear existing content
    ui.faceGallery.innerHTML = "";

    if (state.filteredFaces.length === 0) {
        ui.faceGallery.innerHTML = `
            <div class="gallery-empty">
                <i class="fas fa-user-slash"></i>
                <span>${state.faces.length === 0 ? 'No faces registered yet.' : 'No matching faces found.'}</span>
                ${state.faces.length === 0 ? '<p class="text-muted mt-2">Go to Live Monitor to register new persons.</p>' : ''}
            </div>
        `;
        return;
    }

    // Create face cards
    state.filteredFaces.forEach((face) => {
        const card = document.createElement("div");
        card.className = "face-card";

        const personId = face.person_id
            ? `<div class="badge bg-primary mb-2">${face.person_id}</div>`
            : '';

        const imageUrl = face.image_url || 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="200"%3E%3Crect width="100%25" height="100%25" fill="%232b2b40"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" fill="%239ea6c9" font-family="Inter" font-size="18"%3ENo Image%3C/text%3E%3C/svg%3E';

        card.innerHTML = `
            <img src="${imageUrl}" alt="${face.name}" loading="lazy">
            ${personId}
            <strong>${face.name}</strong>
            <small class="text-muted">${new Date(face.created_at).toLocaleString()}</small>
        `;

        ui.faceGallery.appendChild(card);
    });
};

// Search functionality
const handleSearch = () => {
    const query = ui.searchInput.value.toLowerCase().trim();

    if (!query) {
        state.filteredFaces = state.faces;
    } else {
        state.filteredFaces = state.faces.filter(face =>
            face.name.toLowerCase().includes(query) ||
            (face.person_id && face.person_id.toLowerCase().includes(query))
        );
    }

    renderFaces();
    updateCount();
};

// Clear all faces
const clearAllFaces = async () => {
    if (!confirm("Are you sure you want to delete ALL registered faces? This action cannot be undone.")) {
        return;
    }

    try {
        const response = await fetch("/api/clear", { method: "DELETE" });
        if (!response.ok) throw new Error("Failed to clear faces");

        showAlert("All registered faces have been deleted", "success");
        await fetchFaces();
    } catch (error) {
        console.error("Error clearing faces:", error);
        showAlert("Failed to clear faces", "error");
    }
};

// Event Listeners
if (ui.refreshBtn) {
    ui.refreshBtn.addEventListener("click", fetchFaces);
}

if (ui.clearAllBtn) {
    ui.clearAllBtn.addEventListener("click", clearAllFaces);
}

if (ui.searchInput) {
    ui.searchInput.addEventListener("input", handleSearch);
}

// Initialize tooltips
document.addEventListener("DOMContentLoaded", () => {
    const tooltipTriggerList = [].slice.call(
        document.querySelectorAll('[data-bs-toggle="tooltip"]')
    );
    tooltipTriggerList.map((el) => new bootstrap.Tooltip(el));

    // Initial load
    fetchFaces();
});

console.log("[Faces] Script loaded successfully");
