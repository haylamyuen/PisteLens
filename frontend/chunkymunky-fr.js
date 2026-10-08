fetch("/resortlist")
    .then(function(r) {
        return r.json();
    })
    .then(function(data) {
        for (const item of data.resorts) {
            document.getElementById("ref").add(new Option(item.resort.replace(/-/g, " "), item.resort));
        }
        document.getElementById("ref").value = localStorage.getItem("ref") || ""; // default from settings
    })
    .catch(function() {});

function show(url, opts) {
    document.getElementById("msg").textContent = "Évaluation en cours...";
    fetch(url, opts)
        .then(function(r) {
            return r.json();
        })
        .then(function(data) {
            document.getElementById("msg").textContent = data.error || "";
            document.getElementById("globalval").textContent = data.error ? "-" : data.global_rating.toFixed(2);
            document.getElementById("calval").textContent = data.calibrated !== undefined ? data.calibrated.toFixed(2) : "-";
        })
        .catch(function() {
            document.getElementById("msg").textContent = "Impossible de joindre le serveur :(";
        });
}

document.getElementById("gradegpx").addEventListener("click", function() {
    if (!document.getElementById("gpx").files.length) { document.getElementById("msg").textContent = "Choisissez d'abord un fichier GPX."; return; }
    const form = new FormData();
    form.append("file", document.getElementById("gpx").files[0]);
    form.append("grooming", document.getElementById("grooming").value);
    if (document.getElementById("ref").value) form.append("ref", document.getElementById("ref").value);
    show("/grade/gpx", {method: "POST", body: form});
});

document.getElementById("gradefeats").addEventListener("click", function() {
    const body = {grooming: document.getElementById("grooming").value};
    for (const id of ["length", "avg_grade", "avg_abs_grade", "max_abs_grade", "grade_std", "sinuosity"]) {
        if (document.getElementById(id).value === "") { document.getElementById("msg").textContent = "Veuillez renseigner toutes les caractéristiques."; return; }
        body[id] = parseFloat(document.getElementById(id).value);
    }
    if (document.getElementById("ref").value) body.ref = document.getElementById("ref").value;
    show("/grade/feats", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)}); //headers fix by claude
});
