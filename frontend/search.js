const filter_panel = document.getElementById("filters");
const results_panel = document.getElementById("resultspanel");
const results = document.getElementById("results");
const count = document.getElementById("count");

const limit = 100;


// fill resort options
fetch("/resortlist")
    .then(function(r) {
        return r.json();
    })
    .then(function(data) {
        for (const item of data.resorts) {
            const opt = document.createElement("option");
            opt.value = item.resort;
            opt.textContent = item.resort.replace(/-/g, " "); // regex just replaces - with space
            document.getElementById("fresort").appendChild(opt);
        }
    })
    .catch(function() {});

function params() {
    const p = new URLSearchParams();

    const stuff = {
        "search": "q",
        "resort": "fresort",
        "grade": "fgrade",
        "grooming": "fgrooming",
        "diffmin": "fratingmin",
        "diffmax": "fratingmax",
        "lenmin": "flenmin",
        "lenmax": "flenmax"
    };

    for (const key in stuff) {
        const id = stuff[key];
        const value = document.getElementById(id).value;

        if (value) {
            p.set(key, value) // set key value w no duplicates
        }
    }
    p.set("limit", limit);

    return p;
}

function row(run) {
    console.log(run)//debug
    const row = results.insertRow();
    const link = document.createElement("a");
    link.href = "piste.html?id=" + run.id;
    link.textContent = run.name || "[unnamed]";
    link.className = "isaac";
    row.insertCell().appendChild(link);
    row.insertCell().textContent = String(run.resort).replace(/-/g, " ");// regex just replaces - with space

    const grade = row.insertCell();
    const diff = document.createElement("span");
    diff.className = "diff " + run.original_grade;
    diff.textContent = run.original_grade;
    grade.appendChild(diff); // puts grade symbol thingo inside the cell (child)


    row.insertCell().textContent = run.global_rating.toFixed(2);

    if (run.length) {
        row.insertCell().textContent = Math.round(run.length).toLocaleString() + " m"; // 1,000 US vs europe is 1.000
    } else {
        row.insertCell().textContent = "-";
    }
}




function message(text) {
    results.innerHTML = "";
    const cell = results.insertRow().insertCell();
    cell.colSpan = 6;
    cell.className = "softenifyes";
    cell.textContent = text;
}

function search() {
    results_panel.hidden = false;
    count.textContent = "Searching...";
    results.innerHTML = "";

    fetch("/runslist?" + params())
        .then(function(r) {
            return r.json();
        })
        .then(function(data) {
            if (data.error) {
                count.textContent = "";
                message(data.error);
                console.log(data)

                return;
            }
            if (!data.count) {
                count.textContent = "";
                message("No runs match that search.");
                return;
            }

            data.runs.forEach(row);
            count.textContent = data.count < data.matches
                ? "Showing " + data.count + " of " + data.matches + " runs"
                : "Showing " + data.count + (data.count === 1 ? " run" : " runs");
        })
        .catch(function() {
            count.textContent = "";
            message("Could not reach the server :(");
        });
}

document.getElementById("filter").addEventListener("click", function() {
    console.log("this is delta team approaching coordinates. waiting for your response... 6 tangos in sight, armed MAMs. prepare for close combat in 3, 2, 1...")
    filter_panel.hidden = !filter_panel.hidden;
    document.getElementById("filter").setAttribute("aria-expanded", String(!filter_panel.hidden));
});

document.getElementById("clearbtn").addEventListener("click", function() {
    console.log("this is alpha team approaching coordinates. waiting for your response... 6 tangos in sight, armed MAMs. prepare for close combat in 3, 2, 1...")
    for (const id of ["fresort", "fgrade", "fgrooming", "fratingmin", "fratingmax", "flenmin", "flenmax"]) {
        document.getElementById(id).value = "";
    }
})

document.getElementById("searchbutton").addEventListener("click", search);

document.getElementById("q").addEventListener("keydown", function(e) {
    if (e.key === "Enter") search();
});


