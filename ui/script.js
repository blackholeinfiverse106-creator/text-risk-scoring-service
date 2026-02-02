async function analyzeText() {
    const text = document.getElementById("inputText").value;

    const response = await fetch("http://127.0.0.1:8000/analyze", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ text })
    });

    const data = await response.json();

    document.getElementById("result").classList.remove("hidden");

    // Risk score
    document.getElementById("riskScore").innerText =
        data.risk_score !== undefined ? data.risk_score : "N/A";

    // Confidence score (Task 3)
    document.getElementById("confidenceScore").innerText =
        data.confidence_score !== undefined ? data.confidence_score : "N/A";

    // Risk badge
    const badge = document.getElementById("riskBadge");
    badge.innerText = data.risk_category || "UNKNOWN";
    badge.className = "badge " + (data.risk_category ? data.risk_category.toLowerCase() : "");

    // Trigger reasons
    const list = document.getElementById("reasonsList");
    list.innerHTML = "";

    if (!data.trigger_reasons || data.trigger_reasons.length === 0) {
        const li = document.createElement("li");
        li.innerText = "No risk indicators detected";
        list.appendChild(li);
    } else {
        data.trigger_reasons.forEach(reason => {
            const li = document.createElement("li");
            li.innerText = reason;
            list.appendChild(li);
        });
    }
}
