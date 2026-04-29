document.addEventListener("DOMContentLoaded", function () {
    const dataEl = document.getElementById("bestilling-data");
    const treatmentEl = document.getElementById("tjeneste");
    const carEl = document.getElementById("biltype");
    const previewEl = document.getElementById("price_preview");

    if (!dataEl || !treatmentEl || !carEl || !previewEl) {
        return;
    }

    let bestillingData = { modelTypeMap: {}, priceMap: {} };

    try {
        bestillingData = JSON.parse(dataEl.textContent || "{}");
    } catch (error) {
        bestillingData = { modelTypeMap: {}, priceMap: {} };
    }

    function updatePricePreview() {
        const selectedTreatment = treatmentEl.value;
        const selectedCar = carEl.value;
        const carType = bestillingData.modelTypeMap[selectedCar];

        if (!selectedTreatment || !selectedCar) {
            previewEl.textContent = "Pris: Velg behandling og bilmodell";
            return;
        }

        if (!carType) {
            previewEl.textContent = "Pris: Velg en bilmodell fra listen";
            return;
        }

        const treatmentPrices = bestillingData.priceMap[selectedTreatment] || {};
        const price = treatmentPrices[carType];

        if (price === undefined || price === null) {
            previewEl.textContent = "Pris: Ikke tilgjengelig";
            return;
        }

        previewEl.textContent = `Pris: ${price} kr`;
    }

    treatmentEl.addEventListener("change", updatePricePreview);
    carEl.addEventListener("input", updatePricePreview);
    carEl.addEventListener("change", updatePricePreview);

    updatePricePreview();
});
