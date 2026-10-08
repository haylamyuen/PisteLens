const diffs = ["novice", "easy", "intermediate", "advanced", "expert", "extreme"];
const run_id = new URLSearchParams(location.search).get("id");
const offsets = {};

function difff(grade) {
    const span = document.createElement("span");
    span.className = "diff " + grade;
    span.textContent = grade;
    return span;
}

function show_grade(value_id, category_id, rating) {
    x = Math.round(rating)
    if (x < 0) {
        x = 0;
    } else if (x > 5) {
        x = 5;
    }
    const grade = diffs[x]
    
    document.getElementById(value_id).textContent = rating.toFixed(2);
    document.getElementById(category_id).className = "";
    document.getElementById(category_id).replaceChildren(difff(grade));
}

function notfound(text) {
    document.getElementById("whoopsnotfound").textContent = text;
    document.getElementById("notfound").hidden = false;
}

function draw_map(run) {
    if (!window.L) { //check leaflet loaded
        document.getElementById("mapnote").textContent = "The map library could not be loaded."; 
        return;
    }

    const map = L.map("map").setView([run.lat, run.lon], 15);
    
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(map);

    fetch("https://api.openstreetmap.org/api/0.6/way/" + run.id + "/full.json")
    .then(function(r) {
        return r.json();
    })
    .then(function(data) {
        const nodes = {};
        
        for (let i = 0; i < data.elements.length; i++) {
            const e = data.elements[i];
            if (e.type === "node") {
                nodes[e.id] = [e.lat, e.lon];
            } 
        }
        
        const way = data.elements.find(function(e) {
            return e.type === "way";
        });
        
        const line = L.polyline(way.nodes.map(function(n) {
            return nodes[n];
        }), {color: "#2f7fd1", weight: 5}).addTo(map); 
        
        map.fitBounds(line.getBounds(), { padding: [30, 30] });
    })
    .catch(function() {
        document.getElementById("mapnote").textContent = "The piste outline could not be loaded.";
    });
}


function calibrate() {
    const ref = document.getElementById("ref").value;

    if (!ref) {
        document.getElementById("calval").textContent = "-";
        document.getElementById("calcat").className = "muted";
        document.getElementById("calcat").textContent = "Pick a resort below.";
        return;
    } 

    fetch("/run/" + run_id + "?ref=" + encodeURIComponent(ref))
        .then(function(r) {
            return r.json();
        })
        .then(function(run) {
            if (run.error) {
                document.getElementById("calnote").textContent = run.error;
                return;
            }
            
            show_grade("calval", "calcat", run.calibrated);
        })

        .catch(function() {
            document.getElementById("calnote").textContent = "Could not reach the server :(";
        });
}



if (!run_id) {
    notfound("No piste was selected.");
} else {
    fetch("/run/" + encodeURIComponent(run_id))
        .then(function(r) {
            return r.json();
        })
        .then(function(run) {
            if (run.error) {
                notfound(run.error);
            } else {
                const name = run.name || "Unnamed piste";
                document.getElementById("name").textContent = name;
                show_grade("globalval", "globalcat", run.global_rating);
                document.getElementById("piste").hidden = false; 
                draw_map(run);
            }
        })

        .catch(function() {
            notfound("Could not reach the server :(");
        });

    fetch("/resortlist")
        .then(function(r) {
            return r.json();
        }) 
        .then(function(data) {
            for (let i = 0; i < data.resorts.length; i++) {
                const item = data.resorts[i];
                offsets[item.resort] = item.offset;
                
                const opt = document.createElement("option");
                opt.value = item.resort;
                opt.textContent = String(item.resort).replace(/-/g, " ");
                document.getElementById("ref").appendChild(opt);
            }
            document.getElementById("ref").value = localStorage.getItem("ref") || ""; // default from settings
            calibrate();
        })
        .catch(function() {});

    document.getElementById("ref").addEventListener("change", calibrate);
}
