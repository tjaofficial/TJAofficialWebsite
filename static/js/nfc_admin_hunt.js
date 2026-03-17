document.addEventListener("DOMContentLoaded", function () {
    const addBtn = document.getElementById("addLocationBtn");
    const builder = document.getElementById("locationBuilder");
    const jsonField = document.getElementById("id_locations_json");
    const initialScript = document.getElementById("hunt-locations-initial");

    if (!builder || !jsonField) {
        return;
    }

    let locations = [];

    try {
        if (initialScript && initialScript.textContent.trim()) {
            const parsed = JSON.parse(initialScript.textContent);
            if (Array.isArray(parsed)) {
                locations = parsed;
            }
        } else if (jsonField.value.trim()) {
            const parsed = JSON.parse(jsonField.value);
            if (Array.isArray(parsed)) {
                locations = parsed;
            }
        }
    } catch (err) {
        console.warn("Could not parse initial locations_json", err);
        locations = [];
    }

    if (!locations.length) {
        locations = [
            { key: "merch", path: "merch", label: "Merch Table" },
            { key: "stage", path: "stage", label: "By The Stage" },
            { key: "lounge", path: "lounge", label: "Bar / Lounge" },
            { key: "hidden", path: "hidden", label: "Secret Spot" }
        ];
    }

    function syncJsonField() {
        jsonField.value = JSON.stringify(locations, null, 2);
    }

    function renderRows() {
        builder.innerHTML = "";

        locations.forEach((location, index) => {
            const row = document.createElement("div");
            row.className = "hunt-location-row";

            row.innerHTML = `
                <div class="hunt-location-row-grid">
                    <div class="hunt-location-field">
                        <label>Key</label>
                        <input type="text" value="${escapeHtml(location.key || "")}" data-index="${index}" data-field="key">
                    </div>

                    <div class="hunt-location-field">
                        <label>Path</label>
                        <input type="text" value="${escapeHtml(location.path || "")}" data-index="${index}" data-field="path">
                    </div>

                    <div class="hunt-location-field">
                        <label>Label</label>
                        <input type="text" value="${escapeHtml(location.label || "")}" data-index="${index}" data-field="label">
                    </div>

                    <button type="button" class="btn hunt-location-remove" data-remove-index="${index}">
                        Remove
                    </button>
                </div>
            `;

            builder.appendChild(row);
        });

        bindRowEvents();
        syncJsonField();
    }

    function bindRowEvents() {
        builder.querySelectorAll("input[data-field]").forEach((input) => {
            input.addEventListener("input", function () {
                const index = Number(this.dataset.index);
                const field = this.dataset.field;
                locations[index][field] = this.value;
                syncJsonField();
            });
        });

        builder.querySelectorAll("[data-remove-index]").forEach((btn) => {
            btn.addEventListener("click", function () {
                const index = Number(this.dataset.removeIndex);
                locations.splice(index, 1);
                renderRows();
            });
        });
    }

    function escapeHtml(value) {
        return String(value)
            .replaceAll("&", "&amp;")
            .replaceAll('"', "&quot;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;");
    }

    if (addBtn) {
        addBtn.addEventListener("click", function () {
            locations.push({
                key: "",
                path: "",
                label: ""
            });
            renderRows();
        });
    }

    renderRows();
});