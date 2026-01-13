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

  function setStatus(msg) {
    $("statusChip").textContent = `Estado: ${msg}`;
  }

  function setMeta(total, tiempos) {
    $("totalChip").textContent = `Total: ${total ?? 0}`;
    $("bstChip").textContent = `BST: ${tiempos?.bst ?? "—"}`;
    $("avlChip").textContent = `AVL: ${tiempos?.avl ?? "—"}`;
  }

  function clearTable() {
    $("tbodyHistorial").innerHTML = "";
  }

  function num(v) {
    if (v === null || v === undefined || v === "") return "";
    const n = Number(v);
    if (Number.isNaN(n)) return v;
    return n.toLocaleString("es-EC", { maximumFractionDigits: 3 });
  }

  function renderRows(rows) {
    const tbody = $("tbodyHistorial");
    tbody.innerHTML = "";

    rows.forEach((r) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${r.fecha ?? ""}</td>
        <td>${r.diseno_mezcla ?? ""}</td>
        <td>${r.zona ?? ""}</td>
        <td>${r.wbs ?? ""}</td>
        <td>${r.turno ?? ""}</td>
        <td>${num(r.volumen_m3)}</td>

        <td>${num(r.est_arena_kg)}</td>
        <td>${num(r.est_grava_kg)}</td>
        <td>${num(r.est_cemento_he_kg)}</td>
        <td>${num(r.est_cemento_ip_kg)}</td>
        <td>${num(r.est_agua_kg)}</td>

        <td>${num(r.est_aditivo_rheo_sika115)}</td>
        <td>${num(r.est_aditivo_basf_sika200)}</td>
        <td>${num(r.est_aditivo_delvo)}</td>
        <td>${num(r.est_aditivo_glenium_7950)}</td>
        <td>${num(r.est_aditivo_glenium_7970)}</td>
        <td>${num(r.est_aditivo_fibras)}</td>

        <td>${num(r.arena_humedad_pct)}</td>
        <td>${num(r.asentamiento_final_cm)}</td>
        <td>${num(r.temperatura_c)}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  async function cargarDisenos() {
    const sel = $("diseno");
    const keepFirst = sel.querySelector("option[value='']");
    sel.innerHTML = "";
    sel.appendChild(keepFirst);

    const res = await fetch("/api/recetas");
    const data = await res.json();

    if (!res.ok || !data.ok) {
      setStatus("No se pudieron cargar diseños");
      return;
    }

    (data.disenos || []).forEach((d) => {
      const opt = document.createElement("option");
      opt.value = d;
      opt.textContent = d;
      sel.appendChild(opt);
    });
  }

  function renderSummary(resumen, totalRegistros) {
    const box = $("summaryBox");
    const grid = $("summaryGrid");
    const hint = $("summaryHint");

    grid.innerHTML = "";
    hint.textContent = "";

    if (!resumen) {
      box.style.display = "none";
      return;
    }

    const items = [
      ["Arena (kg)", resumen.arena_kg],
      ["Grava (kg)", resumen.grava_kg],
      ["Cem HE (kg)", resumen.cemento_he_kg],
      ["Cem IP (kg)", resumen.cemento_ip_kg],
      ["Agua (kg)", resumen.agua_kg],
      ["Rheo+Sika115", resumen.aditivo_rheo_sika115],
      ["BASF+Sika200", resumen.aditivo_basf_sika200],
      ["Delvo", resumen.aditivo_delvo],
      ["Glenium 7950", resumen.aditivo_glenium_7950],
      ["Glenium 7970", resumen.aditivo_glenium_7970],
      ["Fibras", resumen.aditivo_fibras],
    ];

    items.forEach(([k, v]) => {
      const div = document.createElement("div");
      div.className = "sum-card";
      div.innerHTML = `<div class="k">${k}</div><div class="v">${num(v)}</div>`;
      grid.appendChild(div);
    });

    if (resumen._errores && resumen._errores > 0) {
      hint.textContent = `Nota: ${resumen._errores} registro(s) no pudieron calcular consumo (diseño sin receta).`;
    } else {
      hint.textContent = `Registros considerados: ${totalRegistros ?? 0}`;
    }

    box.style.display = "block";
  }

  function renderAlertas(payload) {
    const box = $("alertsBox");
    const tbody = $("tbodyAlertas");
    const hint = $("alertsHint");

    tbody.innerHTML = "";
    hint.textContent = "";

    if (!payload || !payload.ok) {
      box.style.display = "none";
      return;
    }

    const filas = payload.filas || [];
    filas.forEach((f) => {
      const deficit = Number(f.deficit_sugerido || 0);
      const bajoMin = Boolean(f.bajo_minimo);

      let tag = `<span class="tag good">OK</span>`;
      if (deficit > 0) tag = `<span class="tag bad">Déficit</span>`;
      else if (bajoMin) tag = `<span class="tag warn">Bajo mínimo</span>`;

      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${f.material ?? ""}</td>
        <td>${f.unidad ?? ""}</td>
        <td>${num(f.stock_actual)}</td>
        <td>${num(f.minimo)}</td>
        <td>${num(f.consumo_estimado)}</td>
        <td>${num(f.deficit_sugerido)}</td>
        <td>${tag}</td>
      `;
      tbody.appendChild(tr);
    });

    const noMap = payload.no_mapeados || [];
    const noFound = payload.no_encontrados || [];

    const parts = [];
    if (noMap.length > 0) parts.push(`${noMap.length} campo(s) de consumo no están mapeados a materiales`);
    if (noFound.length > 0) parts.push(`${noFound.length} material(es) mapeados no existen en tabla materiales`);
    if (parts.length > 0) hint.textContent = "Aviso: " + parts.join(" | ");

    box.style.display = "block";
  }

  async function buscarConConsumoYAlertas(e) {
    e.preventDefault();
    setStatus("Buscando...");
    $("hint").textContent = "";

    const inicio = $("inicio").value;
    const fin = $("fin").value;
    const diseno = $("diseno").value;
    const zona = $("zona").value.trim();
    const turno = $("turno").value;
    const wbs = $("wbs").value.trim();

    if (!inicio || !fin) {
      setStatus("Faltan fechas");
      return;
    }

    const params = new URLSearchParams();
    params.set("inicio", inicio);
    params.set("fin", fin);
    if (diseno) params.set("diseno", diseno);
    if (zona) params.set("zona", zona);
    if (turno) params.set("turno", turno);
    if (wbs) params.set("wbs", wbs);

    const urlRows = `/api/historial_consumo?${params.toString()}`;
    const urlSum = `/api/resumen_consumo?${params.toString()}`;
    const urlAlert = `/api/alertas_consumo?${params.toString()}`;

    // filas
    const resRows = await fetch(urlRows);
    const dataRows = await resRows.json().catch(() => ({}));

    if (!resRows.ok) {
      clearTable();
      setMeta(0, null);
      setStatus("Error");
      $("hint").textContent = dataRows.error ? String(dataRows.error) : `HTTP ${resRows.status}`;
      $("summaryBox").style.display = "none";
      $("alertsBox").style.display = "none";
      return;
    }

    renderRows(dataRows.datos || []);
    setMeta(dataRows.total || 0, dataRows.tiempos || null);

    // resumen
    const resSum = await fetch(urlSum);
    const dataSum = await resSum.json().catch(() => ({}));
    if (resSum.ok && dataSum.ok) renderSummary(dataSum.resumen, dataSum.total_registros);
    else renderSummary(null, 0);

    // alertas
    const resAlert = await fetch(urlAlert);
    const dataAlert = await resAlert.json().catch(() => ({}));
    if (resAlert.ok && dataAlert.ok) renderAlertas(dataAlert);
    else renderAlertas(null);

    if (!dataRows.datos || dataRows.datos.length === 0) {
      setStatus("OK (sin resultados)");
      $("hint").textContent = "No se encontraron registros con esos filtros.";
      renderSummary(null, 0);
      renderAlertas(null);
      return;
    }

    setStatus("OK");
  }

  document.addEventListener("DOMContentLoaded", async () => {
    $("fin").value = todayISO();
    $("inicio").value = daysAgoISO(7);

    await cargarDisenos();

    const form = $("historialForm");
    form.addEventListener("submit", buscarConConsumoYAlertas);

    form.dispatchEvent(new Event("submit"));
  });
})();
