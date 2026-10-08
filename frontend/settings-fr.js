const ref = document.getElementById("ref");

fetch("/resortlist")
    .then(function(r) {
        return r.json();
    })
    .then(function(data) {
        for (const item of data.resorts) {
            ref.add(new Option(item.resort.replace(/-/g, " "), item.resort));
        }
        ref.value = localStorage.getItem("ref") || "";
    })
    .catch(function() {});

ref.addEventListener("change", function() {
    localStorage.setItem("ref", ref.value);
    document.getElementById("msg").textContent = "Enregistré.";
});

