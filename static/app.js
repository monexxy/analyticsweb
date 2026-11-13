const $ = (id) => document.getElementById(id);
const fmt = (v, digits=2) => v == null ? "—" : `${Number(v).toFixed(digits)}%`;
let current = null;

function showNotice(message, bad=false) {
  const box = $("notice");
  box.textContent = message;
  box.classList.toggle("bad", bad);
}
async function api(url, options={}) {
  const response = await fetch(url, {headers:{"Content-Type":"application/json"}, ...options});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Не удалось выполнить запрос.");
  return data;
}
function paint(data) {
  current = data;
  $("overall").textContent = fmt(data.overall);
  $("overall-note").textContent = data.attempts
    ? `Сводная описательная оценка по ${data.attempts} записанным исходам.`
    : "Пока нет записанных исходов. Добавьте уже завершённые результаты.";
  $("empirical").textContent = fmt(data.empirical);
  $("posterior").textContent = fmt(data.posterior);
  $("interval").textContent = data.attempts ? `${fmt(data.low)} – ${fmt(data.high)}` : "—";
  $("above").textContent = data.attempts ? fmt(data.above) : "—";
  $("total").textContent = data.attempts;
  $("win-total").textContent = data.wins;
  $("loss-total").textContent = data.losses;
}
function values() {
  return {
    chance: $("chance").value || 30,
    wins: $("wins").value || 0,
    losses: $("losses").value || 0,
    streak: $("streak").value || 0
  };
}
async function calculate(event) {
  if (event) event.preventDefault();
  try {
    const data = await api("/api/calculate", {method:"POST", body:JSON.stringify(values())});
    paint(data);
    showNotice("Расчёт сохранён в истории.", false);
    refreshHistory();
  } catch (err) { showNotice(err.message, true); }
}
async function addOutcome(outcome) {
  try {
    const data = await api("/api/observations", {
      method:"POST", body:JSON.stringify({chance:$("chance").value || 30, outcome})
    });
    const analysis = data.analysis;
    $("wins").value = analysis.wins;
    $("losses").value = analysis.losses;
    $("streak").value = Math.min(Number($("streak").value || 0), analysis.losses);
    paint(analysis);
    showNotice(outcome === "win" ? "Победа записана в историю." : "Поражение записано в историю.", false);
    refreshHistory();
    refreshStats();
  } catch (err) { showNotice(err.message, true); }
}
async function loadSummary() {
  try {
    const data = await api(`/api/summary?chance=${encodeURIComponent($("chance").value || 30)}`);
    $("wins").value = data.wins;
    $("losses").value = data.losses;
    $("streak").max = data.losses;
    if (Number($("streak").value) > data.losses) $("streak").value = data.losses;
    // Summary is a history view, not a newly persisted calculation.
    $("overall").textContent = fmt(data.attempts ? data.overall : null);
    $("overall-note").textContent = data.attempts
      ? `Сводная оценка по ${data.attempts} результатам с таким же указанным шансом.`
      : "Нужны прошлые результаты для расчёта.";
    $("empirical").textContent = fmt(data.empirical);
    $("posterior").textContent = data.attempts ? fmt(data.posterior) : "—";
    $("interval").textContent = data.attempts ? `${fmt(data.low)} – ${fmt(data.high)}` : "—";
    $("above").textContent = data.attempts ? fmt(data.above) : "—";
    $("total").textContent = data.attempts;
    $("win-total").textContent = data.wins;
    $("loss-total").textContent = data.losses;
  } catch (err) { showNotice(err.message, true); }
}
async function refreshHistory() {
  try {
    const items = await api("/api/history");
    const body = $("history-body");
    if (!items.length) { body.innerHTML = '<tr><td colspan="4" class="empty">История пока пуста.</td></tr>'; return; }
    body.innerHTML = items.map(item => {
      const date = new Date(item.date.replace(" ","T")+"Z").toLocaleString("ru-RU");
      if (item.type === "result") {
        const label = item.outcome === "win" ? "Победа" : "Поражение";
        return `<tr><td><span class="badge ${item.outcome}">ИСХОД</span></td><td>${date}</td><td>${Number(item.chance).toFixed(2)}%</td><td>${label}</td></tr>`;
      }
      return `<tr><td><span class="badge calc">РАСЧЁТ</span></td><td>${date}</td><td>${Number(item.chance).toFixed(2)}%</td><td>${item.wins} побед · ${item.losses} поражений · итог ${item.overall == null ? "—" : Number(item.overall).toFixed(2)+"%"}</td></tr>`;
    }).join("");
  } catch (err) { $("history-body").innerHTML = `<tr><td colspan="4" class="empty">${err.message}</td></tr>`; }
}
async function refreshStats() {
  try {
    const data = await api("/api/stats");
    $("stat-total").textContent = data.total;
    $("stat-wins").textContent = data.wins;
    $("stat-losses").textContent = data.losses;
    $("stat-rate").textContent = fmt(data.rate);
    const chart = $("chart");
    if (!data.recent.length) { chart.innerHTML = '<div class="empty">Пока нет записей для графика.</div>'; return; }
    chart.innerHTML = data.recent.map((item, index) =>
      `<div class="bar-group" title="${item.outcome === "win" ? "Победа" : "Поражение"} · ${item.chance}%"><div class="bar ${item.outcome}" style="height:${item.outcome === "win" ? 100 : 48}%"></div><span class="bar-label">${index+1}</span></div>`
    ).join("");
  } catch (err) { $("chart").textContent = err.message; }
}
function switchPage(name) {
  document.querySelectorAll(".page").forEach(page => page.classList.toggle("active", page.id === `page-${name}`));
  document.querySelectorAll(".nav-btn").forEach(btn => btn.classList.toggle("active", btn.dataset.page === name));
  if (name === "history") refreshHistory();
  if (name === "stats") refreshStats();
}
document.querySelectorAll(".nav-btn").forEach(btn => btn.addEventListener("click", () => switchPage(btn.dataset.page)));
document.querySelectorAll("[data-chance]").forEach(btn => btn.addEventListener("click", () => {
  $("chance").value = btn.dataset.chance;
  document.querySelectorAll("[data-chance]").forEach(b => b.classList.toggle("selected", b === btn));
  loadSummary();
}));
$("analysis-form").addEventListener("submit", calculate);
$("add-win").addEventListener("click", () => addOutcome("win"));
$("add-loss").addEventListener("click", () => addOutcome("loss"));
$("chance").addEventListener("change", loadSummary);
$("refresh-history").addEventListener("click", refreshHistory);
loadSummary();
refreshHistory();
refreshStats();
