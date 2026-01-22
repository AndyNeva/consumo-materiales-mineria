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
    grid.innerHTML = "";
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

  /**
   * Asegura que los arrays y tengan valores numéricos válidos.
   * NO convierte fechas - preserva strings que parecen fechas.
   */
  function ensureNumericData(trace) {
    if (!trace) return trace;
    
    // Función para verificar si es una fecha ISO (YYYY-MM-DD)
    const looksLikeDate = (val) => {
      if (!val || typeof val !== 'string') return false;
      // Buscar patrón YYYY-MM-DD (4 dígitos, guion, 2 dígitos, guion, 2 dígitos)
      return /^\d{4}-\d{2}-\d{2}/.test(val);
    };
    
    // Para X: solo procesar si NO contiene fechas
    if (Array.isArray(trace.x) && trace.x.length > 0) {
      const firstVal = trace.x[0];
      
      // Si el primer valor parece una fecha, NO tocar el array completo
      if (looksLikeDate(firstVal)) {
        console.log(`✓ Detectada fecha en X: "${firstVal}" - NO se procesará`);
        // Dejar trace.x completamente intacto
      } else {
        // Solo convertir a números si NO son fechas
        console.log(`Procesando X (no es fecha): "${firstVal}"`);
        trace.x = trace.x.map(val => {
          if (val === null || val === undefined) return val;
          if (typeof val === 'number') return val;
          if (typeof val === 'string') {
            // Verificar si esta entrada individual es fecha
            if (looksLikeDate(val)) return val;
            const parsed = parseFloat(val);
            return isNaN(parsed) ? val : parsed;
          }
          return val;
        });
      }
    }
    
    // Para Y: siempre intentar convertir a número
    if (Array.isArray(trace.y)) {
      trace.y = trace.y.map(val => {
        if (val === null || val === undefined) return val;
        if (typeof val === 'number') return val;
        if (typeof val === 'string') {
          const parsed = parseFloat(val);
          return isNaN(parsed) ? val : parsed;
        }
        return val;
      });
    }
    
    return trace;
  }

  function plotInto(div, fig, config = {}) {
    if (!div) return;
    if (!fig) {
      div.innerHTML = "<div class='muted'>Sin datos</div>";
      return;
    }

    try {
      console.group("🧪 DEBUG PLOT");
      console.log("FIG completo:", fig);
      console.log("fig.data:", fig.data);
      console.log("fig.layout:", fig.layout);

      // Procesar cada trace para asegurar datos numéricos
      if (Array.isArray(fig.data)) {
        fig.data = fig.data.map((trace, i) => {
          console.group(`TRACE ${i} (antes de procesamiento)`);
          console.log("type:", trace.type);
          console.log("name:", trace.name);
          console.log("x (raw) - primeros 5:", Array.isArray(trace.x) ? trace.x.slice(0, 5) : trace.x);
          console.log("y (raw) - primeros 5:", Array.isArray(trace.y) ? trace.y.slice(0, 5) : trace.y);
          console.log("x.length:", Array.isArray(trace.x) ? trace.x.length : 'N/A');
          console.log("y.length:", Array.isArray(trace.y) ? trace.y.length : 'N/A');
          
          if (Array.isArray(trace.x) && trace.x.length > 0) {
            console.log("x[0]:", trace.x[0]);
            console.log("typeof x[0]:", typeof trace.x[0]);
            console.log("¿Es fecha? (YYYY-MM-DD):", /^\d{4}-\d{2}-\d{2}/.test(String(trace.x[0])));
          }
          
          if (Array.isArray(trace.y) && trace.y.length > 0) {
            console.log("y[0]:", trace.y[0]);
            console.log("typeof y[0]:", typeof trace.y[0]);
          }
          console.groupEnd();
          
          // Asegurar que los datos sean numéricos (pero preservar fechas)
          const processedTrace = ensureNumericData(trace);
          
          console.group(`TRACE ${i} (después de procesamiento)`);
          console.log("x - primeros 5:", Array.isArray(processedTrace.x) ? processedTrace.x.slice(0, 5) : processedTrace.x);
          console.log("y - primeros 5:", Array.isArray(processedTrace.y) ? processedTrace.y.slice(0, 5) : processedTrace.y);
          if (Array.isArray(processedTrace.x) && processedTrace.x.length > 0) {
            console.log("x[0]:", processedTrace.x[0]);
            console.log("typeof x[0]:", typeof processedTrace.x[0]);
          }
          
          if (Array.isArray(processedTrace.y) && processedTrace.y.length > 0) {
            console.log("y[0]:", processedTrace.y[0]);
            console.log("typeof y[0]:", typeof processedTrace.y[0]);
          }
          console.groupEnd();
          
          return processedTrace;
        });
      }

      console.groupEnd();

      Plotly.newPlot(div, fig.data || [], fig.layout || {}, {
        responsive: true,
        displaylogo: false,
        ...config
      });

    } catch (e) {
      console.error("❌ Error en plotInto", e);
      div.innerHTML = "<div class='muted'>Error renderizando gráfica</div>";
    }
  }

  // Renderiza todas las figuras Plotly recibidas de la API
  function renderGraficasFinales(graficas) {
    // Ahora 'graficas' es una lista ordenada de objetos {nombre, figura}
    if (!graficas || !Array.isArray(graficas) || graficas.length === 0) {
      setEstado("No hay gráficas disponibles para ese rango (o muy pocos datos).");
      return;
    }
    
    console.log(`📊 Renderizando ${graficas.length} gráficas en orden:`);
    
    graficas.forEach((item, index) => {
      const { nombre, figura } = item;
      console.log(`  ${index + 1}. ${nombre}`);
      
      // Determinar altura según el tipo de gráfico
      let height = 420; // altura por defecto
      if (nombre.includes('corr_aditivos')) {
        height = 900; // heatmap de aditivos
      } else if (nombre.includes('corr_materiales')) {
        height = 800; // heatmap de materiales
      } else if (nombre.includes('hist_aditivos')) {
        height = 550; // histograma de aditivos
      } else if (nombre.includes('hist_')) {
        height = 500; // otros histogramas
      }
      
      const card = createCard({ title: nombre, spanClass: "span-12" });
      const { wrap, div } = createPlotContainer(height);
      card.appendChild(wrap);
      $("chartsGrid").appendChild(card);
      plotInto(div, figura);
    });
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
    setChip("chipEstado", "Estado: OK");
    setEstado("OK");
    renderGraficasFinales(data.graficas);
  }

  // ---------- Init ----------
  document.addEventListener("DOMContentLoaded", async () => {
    if ($("fin") && !$("fin").value) $("fin").value = todayISO();
    if ($("inicio") && !$("inicio").value) $("inicio").value = daysAgoISO(7);
    setIfEmpty("inicio", getParam("inicio"));
    setIfEmpty("fin", getParam("fin"));
    setIfEmpty("zona", getParam("zona"));
    const form = $("formGraficas");
    if (form) form.addEventListener("submit", generar);
    if (($("inicio")?.value || "") && ($("fin")?.value || "")) {
      form?.dispatchEvent(new Event("submit"));
    }
  });
})();