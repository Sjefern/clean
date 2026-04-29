document.addEventListener("DOMContentLoaded", function () {
	const dataEl = document.getElementById("bestilling-data");
	const treatmentEl = document.getElementById("tjeneste");
	const carEl = document.getElementById("biltype");
	const previewEl = document.getElementById("price_preview");
	const timeEl = document.getElementById("bestillingstid");

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

	// --- Time input helpers ---
	if (!timeEl) {
		return; // nothing else to do if there's no time input
	}

	// reinforce attributes
	timeEl.setAttribute('step', '1800');
	timeEl.setAttribute('min', '10:00');
	timeEl.setAttribute('max', '18:00');

	function pad2(n) { return n.toString().padStart(2, '0'); }

	function showTimeMessage(msg, timeout = 3000) {
		let msgEl = document.getElementById('time_message');
		if (!msgEl) {
			msgEl = document.createElement('div');
			msgEl.id = 'time_message';
			msgEl.style.color = 'crimson';
			msgEl.style.fontSize = '0.9em';
			timeEl.insertAdjacentElement('afterend', msgEl);
		}
		msgEl.textContent = msg;
		if (timeout > 0) {
			setTimeout(() => { if (msgEl) msgEl.textContent = ''; }, timeout);
		}
	}

	function parseTimeString(s) {
		if (!s) return null;
		const parts = s.split(':');
		if (parts.length < 2) return null;
		const h = parseInt(parts[0], 10);
		const m = parseInt(parts[1], 10);
		if (Number.isNaN(h) || Number.isNaN(m)) return null;
		return { h, m };
	}

	function formatHM(h, m) { return `${pad2(h)}:${pad2(m)}`; }

	function clampAndRoundToHalfHour(h, m) {
		let total = h * 60 + m;
		const min = 10 * 60; // 10:00
		const max = 18 * 60; // 18:00

		if (total < min) total = min;
		if (total > max) total = max;

		// round to nearest 30 minutes
		total = Math.round(total / 30) * 30;
		if (total < min) total = min;
		if (total > max) total = max;

		return { h: Math.floor(total / 60), m: total % 60 };
	}

	function validateAndFixTime() {
		const val = timeEl.value;
		if (!val) return;
		const parsed = parseTimeString(val);
		if (!parsed) {
			showTimeMessage('Ugyldig klokkeslettformat');
			timeEl.value = '';
			return;
		}
		const fixed = clampAndRoundToHalfHour(parsed.h, parsed.m);
		const newVal = formatHM(fixed.h, fixed.m);
		if (newVal !== val) {
			timeEl.value = newVal;
			showTimeMessage('Tid ble justert til nærmeste halvtime', 2500);
		}
	}

	// On blur or change, fix the time to allowed values
	timeEl.addEventListener('blur', validateAndFixTime);
	timeEl.addEventListener('change', validateAndFixTime);

	// Optional: when focusing, remove message
	timeEl.addEventListener('focus', () => {
		const msgEl = document.getElementById('time_message');
		if (msgEl) msgEl.textContent = '';
	});
});

