(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);

  function todayISO() {
    const d = new Date();
    const off = d.getTimezoneOffset();
    const local = new Date(d.getTime() - off * 60 * 1000);
    return local.toISOString().slice(0, 10);
  }

  function daysAgoISO(n) {
    const d = new Date();
    d.setDate(d.getDate() - n);
    const off = d.getTimezoneOffset();
    const local = new Date(d.getTime() - off * 60 * 1000);
    return local.toISOString().slice(0, 10);
  }

  function getParam(name) {
    const url = new URL(window.location.href);
    return url.searchParams.get(name) || "";
  }

  function setIfEmpty(id, value) {
    const el = $(id);
    if (el && !el.value && value) el.value = value;
  }

  function setEstado(msg) {
    const el = $("estado");
    if (el) el.textContent = msg;
  }

  function setChip(id, text) {
    const el = $(id);
    if (el) el.textContent = text;
  }

  function num(v, maxFrac = 3) {
    if (v === null || v === undefined || v === "") return "—";
    const n = Number(v);
    if (Number.isNaN(n)) return String(v);
    return n.toLocaleString("es-EC", { maximumFractionDigits: maxFrac });
  }

  function clearCharts() {
    const grid = $("chartsGrid");
    if (!grid) return;
    // Deja el primer card de estado (si existe) y limpia lo demás
    const keep = [];
    [...grid.children].forEach((child) => {
      const isStatusCard = child.querySelector && child.querySelector("#estado");
      if (isStatusCard) keep.push(child);
    });
    grid.innerHTML = "";
    keep.forEach((k) => grid.appendChild(k));
  }

  function createCard({ title, spanClass = "span-12" }) {
    const grid = $("chartsGrid");
    if (!grid) return null;

    const section = document.createElement("section");
    section.className = `card ${spanClass}`;

    if (title) {
      const h = document.createElement("h3");
      h.className = "chart-title";
      h.textContent = title;
      section.appendChild(h);
    }

    return section;
  }

  function createPlotContainer(height = 420) {
    const wrap = document.createElement("div");
    wrap.className = "plot-wrap";
    const div = document.createElement("div");
    div.style.height = `${height}px`;
    wrap.appendChild(div);
    return { wrap, div };
  }

  function plotInto(div, fig, config = {}) {
    if (!div) return;

    if (!fig) {
      div.innerHTML = "<div class='muted'>Sin datos</div>";
      return;
    }

    try {
      const data = fig.data || [];
      const layout = fig.layout || {};
      const cfg = Object.assign({ responsive: true, displaylogo: false }, config);
      Plotly.newPlot(div, data, layout, cfg);
    } catch (e) {
      div.innerHTML = "<div class='muted'>Error renderizando gráfica</div>";
      // eslint-disable-next-line no-console
      console.error(e);
    }
  }

  // ---------- Renderers según schema "estadisticas_dinamicas.py" ----------
  function renderSummaryChart(chart) {
    const data = chart?.data || {};
    const card = createCard({ title: "Resumen", spanClass: "span-12" });
    if (!card) return;

    const box = document.createElement("div");
    box.className = "plot-wrap";

    const rows = [];
    rows.push(["Registros", num(data.num_registros, 0)]);
    if (data.disenos_unicos !== null && data.disenos_unicos !== undefined)
      rows.push(["Diseños únicos", num(data.disenos_unicos, 0)]);
    if (data.zonas_unicas !== null && data.zonas_unicas !== undefined)
      rows.push(["Zonas únicas", num(data.zonas_unicas, 0)]);
    if (data.turnos_unicos !== null && data.turnos_unicos !== undefined)
      rows.push(["Turnos únicos", num(data.turnos_unicos, 0)]);

    const vol = data.volumen_stats;
    if (vol) {
      rows.push(["Volumen min", num(vol.min)]);
      rows.push(["Volumen p25", num(vol.p25)]);
      rows.push(["Volumen mediana", num(vol.median)]);
      rows.push(["Volumen media", num(vol.mean)]);
      rows.push(["Volumen p75", num(vol.p75)]);
      rows.push(["Volumen max", num(vol.max)]);
      rows.push(["Volumen std", num(vol.std)]);
    }

    const table = document.createElement("table");
    table.style.width = "100%";
    table.style.borderCollapse = "collapse";
    table.innerHTML = `
      <thead>
        <tr>
          <th style="text-align:left;padding:10px 12px;border-bottom:1px solid rgba(255,255,255,.08);color:var(--muted);font-size:12px;">Métrica</th>
          <th style="text-align:left;padding:10px 12px;border-bottom:1px solid rgba(255,255,255,.08);color:var(--muted);font-size:12px;">Valor</th>
        </tr>
      </thead>
      <tbody>
        ${rows
          .map(
            ([k, v]) => `
          <tr>
            <td style="padding:10px 12px;border-bottom:1px solid rgba(255,255,255,.06);font-size:13px;">${k}</td>
            <td style="padding:10px 12px;border-bottom:1px solid rgba(255,255,255,.06);font-size:13px;font-family:var(--mono);">${v}</td>
          </tr>
        `
          )
          .join("")}
      </tbody>
    `;

    box.appendChild(table);
    card.appendChild(box);
    $("chartsGrid").appendChild(card);
  }

  function renderBarChart(chart, titleFallback) {
    const x = chart?.x || [];
    const y = chart?.y || [];
    const title = chart?.title || titleFallback || "Gráfica";

    const card = createCard({ title, spanClass: "span-12" });
    if (!card) return;

    const { wrap, div } = createPlotContainer(420);
    card.appendChild(wrap);
    $("chartsGrid").appendChild(card);

    const fig = {
      data: [
        {
          type: "bar",
          x,
          y,
        },
      ],
      layout: {
        margin: { l: 50, r: 20, t: 20, b: 80 },
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        font: { color: "rgba(255,255,255,.9)" },
        xaxis: { tickangle: -25, gridcolor: "rgba(255,255,255,.06)" },
        yaxis: { gridcolor: "rgba(255,255,255,.06)" },
      },
    };

    plotInto(div, fig);
  }

  function renderHistChart(chart, titleFallback) {
    // chart trae labels/values
    const labels = chart?.labels || [];
    const values = chart?.values || [];
    const title = chart?.title || titleFallback || "Histograma";

    const card = createCard({ title, spanClass: "span-12" });
    if (!card) return;

    const { wrap, div } = createPlotContainer(420);
    card.appendChild(wrap);
    $("chartsGrid").appendChild(card);

    const fig = {
      data: [
        {
          type: "bar",
          x: labels,
          y: values,
        },
      ],
      layout: {
        margin: { l: 50, r: 20, t: 20, b: 120 },
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        font: { color: "rgba(255,255,255,.9)" },
        xaxis: { tickangle: -35, gridcolor: "rgba(255,255,255,.06)" },
        yaxis: { gridcolor: "rgba(255,255,255,.06)" },
      },
    };

    plotInto(div, fig);
  }

  function renderBoxplotChart(chart, titleFallback) {
    const title = chart?.title || titleFallback || "Boxplot";
    const stats = chart?.stats;

    const card = createCard({ title, spanClass: "span-12" });
    if (!card) return;

    const { wrap, div } = createPlotContainer(380);
    card.appendChild(wrap);
    $("chartsGrid").appendChild(card);

    if (!stats) {
      div.innerHTML = "<div class='muted'>Sin datos</div>";
      return;
    }

    // Plotly soporta box con q1/median/q3/lowerfence/upperfence
    const fig = {
      data: [
        {
          type: "box",
          name: "Volumen",
          q1: [stats.p25],
          median: [stats.median],
          q3: [stats.p75],
          lowerfence: [stats.min],
          upperfence: [stats.max],
          boxpoints: false,
          whiskerwidth: 0.6,
        },
      ],
      layout: {
        margin: { l: 50, r: 20, t: 20, b: 50 },
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        font: { color: "rgba(255,255,255,.9)" },
        yaxis: { gridcolor: "rgba(255,255,255,.06)" },
      },
    };

    plotInto(div, fig);
  }

  function renderCorrChart(chart, titleFallback) {
    const title = chart?.title || titleFallback || "Correlación";
    const data = chart?.data;

    const card = createCard({ title, spanClass: "span-12" });
    if (!card) return;

    const { wrap, div } = createPlotContainer(520);
    card.appendChild(wrap);
    $("chartsGrid").appendChild(card);

    if (!data || !data.labels || !data.matrix) {
      div.innerHTML = "<div class='muted'>Sin datos</div>";
      return;
    }

    const labels = data.labels;
    const z = data.matrix;

    const fig = {
      data: [
        {
          type: "heatmap",
          x: labels,
          y: labels,
          z,
          zmin: -1,
          zmax: 1,
        },
      ],
      layout: {
        margin: { l: 90, r: 20, t: 20, b: 120 },
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        font: { color: "rgba(255,255,255,.9)" },
        xaxis: { tickangle: -35 },
        yaxis: { autorange: "reversed" },
      },
    };

    plotInto(div, fig);
  }

  function renderGraficasFromPackage(pkg) {
    // pkg esperado:
    // { num_registros, graficas: {k:{type,...}}, graficas_disponibles:[...] }
    const n = pkg?.num_registros ?? 0;
    const disponibles = pkg?.graficas_disponibles || [];
    const graficas = pkg?.graficas || {};

    setChip("chipReg", `Registros: ${n}`);
    setChip("chipDisp", `Disponibles: ${disponibles.length ? disponibles.join(", ") : "—"}`);

    const keys = Object.keys(graficas);
    if (!keys.length) {
      setEstado("No hay gráficas disponibles para ese rango (o muy pocos datos).");
      return;
    }

    // Render en un orden lógico
    const order = [
      "resumen_basico",
      "frecuencia_diseno",
      "boxplot_volumen",
      "hist_volumen",
      "correlacion",
    ];

    const finalKeys = order.filter((k) => k in graficas).concat(keys.filter((k) => !order.includes(k)));

    finalKeys.forEach((k) => {
      const ch = graficas[k];
      const t = ch?.type;

      if (t === "summary") return renderSummaryChart(ch);
      if (t === "bar") return renderBarChart(ch, k);
      if (t === "hist") return renderHistChart(ch, k);
      if (t === "boxplot") return renderBoxplotChart(ch, k);
      if (t === "corr") return renderCorrChart(ch, k);

      // Fallback: intenta si viene como figura Plotly directa
      if (ch?.data && ch?.layout) {
        const card = createCard({ title: ch?.title || k, spanClass: "span-12" });
        const { wrap, div } = createPlotContainer(420);
        card.appendChild(wrap);
        $("chartsGrid").appendChild(card);
        return plotInto(div, ch);
      }
    });
  }

  // ---------- Cargar diseños (select) ----------
  async function cargarDisenos() {
    const sel = $("diseno");
    if (!sel) return;

    const keepFirst = sel.querySelector("option[value='']");
    sel.innerHTML = "";
    if (keepFirst) sel.appendChild(keepFirst);
    else {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "Todos";
      sel.appendChild(opt);
    }

    try {
      const res = await fetch("/api/recetas");
      const data = await res.json().catch(() => ({}));
      if (!res.ok) return;

      const disenos = data.disenos || [];
      disenos.forEach((d) => {
        const opt = document.createElement("option");
        opt.value = d;
        opt.textContent = d;
        sel.appendChild(opt);
      });

      // Si llegó con ?diseno=..., selecciónalo
      const qDis = getParam("diseno");
      if (qDis) sel.value = qDis;
    } catch (_) {
      // silencio
    }
  }

  // ---------- Generar ----------
  async function generar(e) {
    if (e && typeof e.preventDefault === "function") e.preventDefault();

    const inicio = $("inicio")?.value || "";
    const fin = $("fin")?.value || "";
    const diseno = $("diseno")?.value || "";
    const zona = ($("zona")?.value || "").trim();

    if (!inicio || !fin) {
      setChip("chipEstado", "Estado: Error");
      setEstado("Debes seleccionar inicio y fin.");
      return;
    }

    const qs = new URLSearchParams({ inicio, fin });
    if (diseno) qs.set("diseno", diseno);
    if (zona) qs.set("zona", zona);

    setChip("chipEstado", "Estado: Generando…");
    setEstado("Generando gráficas…");
    clearCharts();

    const res = await fetch(`/api/graficas?${qs.toString()}`);
    const data = await res.json().catch(() => ({}));

    if (!res.ok || !data.ok) {
      setChip("chipEstado", "Estado: Error");
      setEstado(data.error || `Error (HTTP ${res.status})`);
      return;
    }

    // Compat: a veces viene como {figs: {...}} o {figs: package}
    // Tu backend (según lo último) debe devolver { ok:true, figs: <package> }
    const figs = data.figs;

    // Caso 1: figs ya es el package esperado
    if (figs && typeof figs === "object" && ("graficas" in figs || "graficas_disponibles" in figs)) {
      renderGraficasFromPackage(figs);
      setChip("chipEstado", "Estado: OK");
      setEstado("OK");
      return;
    }

    // Caso 2: figs es un dict de figuras plotly (legacy)
    if (figs && typeof figs === "object") {
      setChip("chipReg", "Registros: —");
      setChip("chipDisp", "Disponibles: legacy");
      setChip("chipEstado", "Estado: OK");
      setEstado("OK (modo legacy)");

      Object.keys(figs).forEach((k) => {
        const fig = figs[k];
        const card = createCard({ title: k, spanClass: "span-12" });
        const { wrap, div } = createPlotContainer(420);
        card.appendChild(wrap);
        $("chartsGrid").appendChild(card);
        plotInto(div, fig);
      });
      return;
    }

    setChip("chipEstado", "Estado: OK");
    setEstado("OK (sin gráficas).");
  }

  // ---------- Init ----------
  document.addEventListener("DOMContentLoaded", async () => {
    // Defaults
    if ($("fin") && !$("fin").value) $("fin").value = todayISO();
    if ($("inicio") && !$("inicio").value) $("inicio").value = daysAgoISO(7);

    // Query params from historial
    setIfEmpty("inicio", getParam("inicio"));
    setIfEmpty("fin", getParam("fin"));
    setIfEmpty("zona", getParam("zona"));

    await cargarDisenos();

    const form = $("formGraficas");
    if (form) form.addEventListener("submit", generar);

    // Autogenera si hay inicio/fin
    if (($("inicio")?.value || "") && ($("fin")?.value || "")) {
      form?.dispatchEvent(new Event("submit"));
    }
  });
})();
