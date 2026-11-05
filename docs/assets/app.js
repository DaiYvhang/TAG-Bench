"use strict";

(() => {
  const data = window.TAGBENCH_DATA;
  if (!data) {
    document.getElementById("table-status").textContent = "Page data could not load. Keep the assets folder beside index.html.";
    return;
  }
  const $ = (id) => document.getElementById(id);
  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const pct = (value) => value === null ? "—" : (value * 100).toFixed(1);
  const fixed = (value, digits = 1) => value === null ? "—" : Number(value).toFixed(digits);
  const clock = (seconds) => `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
  const seconds = (value) => Number(value).toFixed(2);
  const waveSVG = (values, color) => {
    const ns = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", "0 0 960 90");
    svg.setAttribute("preserveAspectRatio", "none");
    values.forEach((peak, i) => {
      const line = document.createElementNS(ns, "line");
      const x = (i + 0.5) * 960 / values.length;
      const extent = Math.max(1.2, Math.pow(peak, 0.75) * 40);
      line.setAttribute("x1", x);
      line.setAttribute("x2", x);
      line.setAttribute("y1", 45 - extent);
      line.setAttribute("y2", 45 + extent);
      line.setAttribute("stroke", color);
      line.setAttribute("stroke-width", Math.max(1.5, 960 / values.length * 0.42));
      line.setAttribute("stroke-linecap", "round");
      svg.append(line);
    });
    return svg;
  };

  if (data.paper.repository_url) {
    $("code-link").href = data.paper.repository_url;
    $("code-link").target = "_blank";
    $("code-link").rel = "noopener";
  }

  // A real example, on a 0–30 second view of its full 60-second recording.
  const heroDemo = data.demos[0];
  $("hero-wave").append(waveSVG(heroDemo.waveform.slice(0, Math.ceil(heroDemo.waveform.length * 30 / heroDemo.duration)), "#73b8aa"));
  [
    ["Human annotation", heroDemo.ground_truth, false],
    ["FireRedAudio", heroDemo.predictions[0].intervals, true],
    ["MOSS-Audio-8B-Thinking", heroDemo.predictions[1].intervals, true],
  ].forEach(([label, intervals, prediction]) => {
    const track = el("div", "hero-track" + (prediction ? " pred" : ""));
    const title = el("div", "hero-track-label");
    title.append(el("span", "", label), el("span", "", `${intervals.length} intervals`));
    const lane = el("div", "hero-track-lane");
    intervals.forEach(([start, end]) => {
      const bar = el("span", "hero-segment");
      bar.style.left = `${Math.max(0, start) / 30 * 100}%`;
      bar.style.width = `${(Math.min(end, 30) - Math.max(start, 0)) / 30 * 100}%`;
      lane.append(bar);
    });
    track.append(title, lane);
    $("hero-tracks").append(track);
  });

  data.subsets.forEach((subset, i) => {
    const item = el("div", "subset-item");
    const copy = el("div");
    copy.append(el("h4", "", subset.name), el("p", "", subset.description));
    item.append(el("span", "subset-number", String(i + 1).padStart(2, "0")), copy, el("span", "subset-count", subset.n));
    $("subset-grid").append(item);
  });

  const column = (key, label, getter, format = pct, ascending = false) => ({key, label, getter, format, ascending});
  const overall = (key) => (model) => model.overall[key];
  const multi = (key) => (model) => model.count[key];
  const views = {
    overall: [
      column("miou", "mIoU ↑", overall("miou")), column("r03", "R@0.3 ↑", overall("r03")),
      column("r05", "R@0.5 ↑", overall("r05")), column("r07", "R@0.7 ↑", overall("r07")),
      column("single", "One-to-one ↑", overall("single")), column("multi", "One-to-many ↑", overall("multi")),
      column("fail", "Fail ↓", overall("fail"), pct, true), column("giou", "gIoU ↑", overall("giou")),
      column("mae", "MAE (s) ↓", overall("mae"), fixed, true), column("cvg", "Cvg ↑", overall("cvg")),
      column("n", "N", overall("n"), String),
    ],
    subsets: data.subsets.map((s) => column(s.tag, s.name + " ↑", (model) => model.subsets[s.tag])),
    count: [
      column("accuracy", "Count accuracy ↑", multi("accuracy")), column("under", "Under ↓", multi("under"), pct, true),
      column("over", "Over ↓", multi("over"), pct, true), column("predictions", "Avg. predicted", multi("predictions"), (v) => fixed(v, 2)),
      column("targets", "Avg. target", multi("targets"), (v) => fixed(v, 2)), column("miou", "mIoU ↑", multi("miou")),
      column("n", "N", multi("n"), String),
    ],
  };
  const notes = {
    overall: "IoU, Recall, gIoU and count metrics include every evaluated response. Midpoint MAE uses parseable responses only; read it alongside Cvg (coverage). Click a column header to sort.",
    subsets: "Each cell is the subset mIoU. Short and long subsets differ in source composition, so these comparisons are descriptive. Click a subset heading to rank models on that task.",
    count: "One-to-many queries only. Count accuracy + under-reporting + over-reporting = 100%. Count accuracy checks the number of merged intervals, independently of their positions.",
  };
  let activeView = "overall";
  let sortKey = "miou";
  let sortAscending = false;
  let visibleModels = [];

  function renderResults() {
    const query = $("model-search").value.trim().toLowerCase();
    const group = $("model-group").value;
    const columns = views[activeView];
    const selected = columns.find((c) => c.key === sortKey);
    visibleModels = data.models.filter((model) => model.name.toLowerCase().includes(query) && (group === "all" || model.group === group));
    visibleModels.sort((a, b) => {
      if (sortKey === "name") return (sortAscending ? 1 : -1) * a.name.localeCompare(b.name);
      const av = selected ? selected.getter(a) : a.overall.miou;
      const bv = selected ? selected.getter(b) : b.overall.miou;
      if (av === null) return 1;
      if (bv === null) return -1;
      return (sortAscending ? 1 : -1) * (av - bv) || a.name.localeCompare(b.name);
    });
    const heading = el("tr");
    [{key: "name", label: "Model", ascending: true}, ...columns].forEach((c) => {
      const th = el("th");
      th.scope = "col";
      const current = c.key === sortKey;
      th.setAttribute("aria-sort", current ? (sortAscending ? "ascending" : "descending") : "none");
      const button = el("button", "", c.label + (current ? (sortAscending ? " ▴" : " ▾") : ""));
      button.type = "button";
      button.addEventListener("click", () => {
        sortAscending = current ? !sortAscending : c.ascending;
        sortKey = c.key;
        renderResults();
        [...$("results-head").querySelectorAll("button")].find((b) => b.textContent.startsWith(c.label))?.focus({preventScroll: true});
      });
      th.append(button);
      heading.append(th);
    });
    $("results-head").replaceChildren(heading);
    $("results-body").replaceChildren();
    visibleModels.forEach((model) => {
      const tr = el("tr");
      const name = el("td", "model-cell", model.name);
      name.append(el("small", "", model.id === "gemini-3.1-pro" ? "API" : ""));
      tr.append(name);
      columns.forEach((c) => tr.append(el("td", "", c.format(c.getter(model)))));
      $("results-body").append(tr);
    });
    if (!visibleModels.length) {
      const tr = el("tr");
      const td = el("td", "", "No models match these filters.");
      td.colSpan = columns.length + 1;
      tr.append(td);
      $("results-body").append(tr);
    }
    $("table-status").textContent = `${visibleModels.length} of ${data.models.length} systems · arXiv v2`;
    $("result-note").textContent = notes[activeView];
    renderChart(visibleModels);
  }

  function renderChart(models) {
    const isCount = activeView === "count";
    const selected = activeView === "subsets" ? views.subsets.find((c) => c.key === sortKey) : null;
    const value = isCount ? multi("accuracy") : selected ? selected.getter : overall("miou");
    const title = isCount ? "One-to-many count accuracy" : selected ? `${selected.label.replace(" ↑", "")} mIoU` : "Overall mIoU";
    const leaders = [...models].sort((a, b) => value(b) - value(a)).slice(0, 5);
    $("chart-title").textContent = `${title} · leading systems`;
    $("ranking-chart").replaceChildren();
    const ceiling = Math.max(...leaders.map(value), 0.01);
    leaders.forEach((model) => {
      const row = el("div", "rank-bar-row");
      const track = el("div", "rank-track");
      const fill = el("div", "rank-fill");
      fill.style.width = `${value(model) / ceiling * 100}%`;
      track.append(fill);
      row.append(el("span", "rank-name", model.name), track, el("span", "rank-value", pct(value(model))));
      $("ranking-chart").append(row);
    });
    $("ranking-chart").setAttribute("aria-label", title + ": " + (leaders.map((m) => `${m.name}, ${pct(value(m))}`).join("; ") || "No matching models"));
  }

  document.querySelectorAll("[data-view]").forEach((button) => button.addEventListener("click", () => {
    activeView = button.dataset.view;
    sortKey = activeView === "count" ? "accuracy" : activeView === "subsets" ? data.subsets[0].tag : "miou";
    sortAscending = false;
    document.querySelectorAll("[data-view]").forEach((item) => item.setAttribute("aria-pressed", item === button ? "true" : "false"));
    renderResults();
  }));
  $("model-search").addEventListener("input", renderResults);
  $("model-group").addEventListener("change", renderResults);
  $("download-csv").addEventListener("click", () => {
    const columns = views[activeView];
    const quote = (value) => '"' + String(value).replaceAll('"', '""') + '"';
    const rows = [["Model", ...columns.map((c) => c.label)], ...visibleModels.map((model) => [model.name, ...columns.map((c) => c.format(c.getter(model)))])];
    const content = rows.map((row) => row.map(quote).join(",")).join("\r\n");
    const url = URL.createObjectURL(new Blob([content], {type: "text/csv;charset=utf-8"}));
    const link = el("a");
    link.href = url;
    link.download = `tagbench-paper-v2-${activeView}.csv`;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });

  const audio = $("demo-audio");
  let activeDemo = data.demos[0];
  let stopAt = null;
  let intervalButtons = [];
  function updatePlayback() {
    const time = audio.currentTime || 0;
    $("playback-time").textContent = `${clock(time)} / ${clock(activeDemo.duration)}`;
    $("audio-seek").value = time;
    $("audio-seek").setAttribute("aria-valuetext", `${seconds(time)} of ${seconds(activeDemo.duration)} seconds`);
    $("playhead").style.left = `${Math.min(100, time / activeDemo.duration * 100)}%`;
    intervalButtons.forEach(({button, start, end}) => button.classList.toggle("active", !audio.paused && time >= start && time <= end));
    if (stopAt !== null && time >= stopAt) {
      audio.pause();
      stopAt = null;
    }
  }

  async function playInterval(start, end, label) {
    stopAt = Math.min(end > start ? end : start + 0.35, activeDemo.duration);
    audio.currentTime = Math.min(start, activeDemo.duration);
    try {
      await audio.play();
      $("demo-feedback").textContent = `${label}: playing ${seconds(start)}–${seconds(end)} seconds. Audio stops at the end of the selected interval.`;
    } catch (error) {
      stopAt = null;
      $("demo-feedback").textContent = "Playback could not start. Use the audio player's play button, or check that the audio assets are present.";
    }
  }

  function addTrack(name, intervals, truth = false) {
    const track = el("div", "demo-track" + (truth ? " ground-truth" : ""));
    const title = el("div", "track-title", name);
    title.append(el("small", "", `${intervals.length} interval${intervals.length === 1 ? "" : "s"}`));
    const body = el("div");
    const lane = el("div", "track-lane");
    intervals.forEach(([start, end]) => {
      if (start >= activeDemo.duration) return;
      const button = el("button", "interval");
      button.type = "button";
      button.style.left = `${start / activeDemo.duration * 100}%`;
      button.style.width = `${Math.max(0, Math.min(end, activeDemo.duration) - start) / activeDemo.duration * 100}%`;
      const label = `${name}, ${seconds(start)} to ${seconds(end)} seconds`;
      button.title = label;
      button.setAttribute("aria-label", `Play ${label}`);
      button.addEventListener("click", () => playInterval(start, end, name));
      lane.append(button);
      intervalButtons.push({button, start, end});
    });
    const labels = intervals.map(([s, e]) => `${seconds(s)}–${seconds(e)}s${e > activeDemo.duration ? " (extends beyond audio)" : ""}`).join(" · ") || "No recoverable timestamp";
    body.append(lane, el("div", "interval-labels", labels));
    track.append(title, body);
    $("demo-tracks").append(track);
  }

  function selectDemo(index) {
    audio.pause();
    stopAt = null;
    activeDemo = data.demos[index];
    intervalButtons = [];
    $("demo-tag").textContent = `${activeDemo.task_tag} · ${activeDemo.ground_truth.length > 1 ? "One-to-many" : "One-to-one"} · ${clock(activeDemo.duration)}`;
    $("demo-query").textContent = activeDemo.short_query;
    $("demo-description").textContent = activeDemo.description;
    $("demo-full-query").textContent = activeDemo.question;
    audio.src = activeDemo.audio;
    audio.load();
    $("audio-seek").max = activeDemo.duration;
    $("demo-waveform").replaceChildren(waveSVG(activeDemo.waveform, "#7cad99"));
    $("demo-axis").replaceChildren();
    for (let i = 0; i <= 5; i++) $("demo-axis").append(el("span", "", `${fixed(activeDemo.duration * i / 5, activeDemo.duration < 10 ? 1 : 0)}s`));
    $("demo-tracks").replaceChildren();
    addTrack("Human annotation", activeDemo.ground_truth, true);
    activeDemo.predictions.forEach((p) => addTrack(p.name, p.intervals));
    $("demo-metrics").replaceChildren();
    activeDemo.predictions.forEach((prediction) => {
      const row = el("tr");
      [prediction.name, pct(prediction.iou), `${prediction.n_hyp} / ${prediction.n_gt} target`, prediction.mae_mid === null ? "—" : `${fixed(prediction.mae_mid, 2)} s`].forEach((v) => row.append(el("td", "", v)));
      $("demo-metrics").append(row);
    });
    $("demo-feedback").textContent = "Full recording, original timestamps. These are archived outputs, not live inference. Example scores are illustrative, not aggregate rankings.";
    [...$("demo-tabs").children].forEach((button, i) => button.setAttribute("aria-pressed", i === index ? "true" : "false"));
    updatePlayback();
  }
  data.demos.forEach((demo, index) => {
    const button = el("button", "demo-tab");
    button.type = "button";
    button.setAttribute("aria-pressed", "false");
    button.append(el("span", "", String(index + 1).padStart(2, "0")), document.createTextNode(demo.title));
    button.addEventListener("click", () => selectDemo(index));
    $("demo-tabs").append(button);
  });
  ["timeupdate", "pause", "play", "loadedmetadata", "ended"].forEach((event) => audio.addEventListener(event, updatePlayback));
  audio.addEventListener("error", () => {$("demo-feedback").textContent = "Audio could not load. Keep assets/audio beside the HTML page, or serve the docs folder with a local HTTP server.";});
  $("audio-seek").addEventListener("input", (event) => {
    stopAt = null;
    audio.currentTime = Number(event.target.value);
    updatePlayback();
  });

  let toastTimer;
  function showToast(message) {
    $("copy-status").textContent = message;
    $("copy-status").classList.add("visible");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => $("copy-status").classList.remove("visible"), 2600);
  }
  document.querySelectorAll("[data-copy]").forEach((button) => button.addEventListener("click", async () => {
    const target = $(button.dataset.copy);
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(target.textContent);
      } else {
        const textArea = el("textarea");
        textArea.value = target.textContent;
        textArea.style.position = "fixed";
        textArea.style.opacity = "0";
        document.body.append(textArea);
        textArea.select();
        const copied = document.execCommand("copy");
        textArea.remove();
        button.focus({preventScroll: true});
        if (!copied) throw new Error("Clipboard unavailable");
      }
      showToast("Copied to clipboard");
    } catch (error) {
      const range = document.createRange();
      range.selectNodeContents(target);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      showToast("Text selected. Press Ctrl+C or ⌘C to copy.");
    }
  }));

  renderResults();
  selectDemo(0);
})();
