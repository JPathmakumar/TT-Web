const BASE_URL = "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show?id=waste-wizard-lookup-table";

const GREEN_BIN_MARKERS = ["green bin", "organics", "compost"];

let allItems = [];

async function loadData() {
  try {
    const pkgRes = await fetch(BASE_URL);
    const pkgData = await pkgRes.json();

    const resources = pkgData.result.resources;
    const jsonResource = resources.find(r => r.format === "JSON");

    const metaRes = await fetch(
      "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/resource_show?id=" + jsonResource.id
    );
    const metaData = await metaRes.json();

    const dataRes = await fetch(metaData.result.url);
    const raw = await dataRes.json();

    const records = Array.isArray(raw) ? raw : (raw.data || raw.items || []);

    allItems = records
      .map(r => {
        const values = Object.values(r).join(" ").toLowerCase();
        const name = Object.values(r)[0];
        const bin = values;
        return { name, bin };
      })
      .filter(x => GREEN_BIN_MARKERS.some(m => x.bin.includes(m)))
      .map(x => x.name)
      .sort();

    document.getElementById("status").innerText = `Loaded ${allItems.length} items`;
    render(allItems);

  } catch (err) {
    console.error(err);
    document.getElementById("status").innerText =
      "Failed to load Green Bin data (check console)";
  }
}

function render(items) {
  const list = document.getElementById("list");
  list.innerHTML = "";

  items.forEach(item => {
    const li = document.createElement("li");
    li.textContent = item;
    list.appendChild(li);
  });
}

document.getElementById("search").addEventListener("input", (e) => {
  const q = e.target.value.toLowerCase();
  render(allItems.filter(x => x.toLowerCase().includes(q)));
});

loadData();
