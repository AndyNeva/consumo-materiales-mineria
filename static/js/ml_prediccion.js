(() => {
  "use strict";

  function $(id){ return document.getElementById(id); }

  function setStatus(el, msg, kind){
    if(!el) return;
    el.textContent = msg || "";
    el.classList.remove("ok","err","muted");
    if(kind === "ok") el.classList.add("ok");
    else if(kind === "err") el.classList.add("err");
    else el.classList.add("muted");
  }

  function fmtNum(x){
    const n = Number(x);
    if (Number.isFinite(n)) return n.toLocaleString("es-EC", { maximumFractionDigits: 2 });
    return String(x ?? "");
  }

  function renderMetricas(metricas){
    const tb = $("tbodyMetricas");
    if(!tb) return;
    tb.innerHTML = "";

    if(!metricas || typeof metricas !== "object"){
      tb.innerHTML = `<tr><td colspan="2" class="muted">Sin métricas</td></tr>`;
      return;
    }

    const keys = Object.keys(metricas);
    if(!keys.length){
      tb.innerHTML = `<tr><td colspan="2" class="muted">Sin métricas</td></tr>`;
      return;
    }

    keys.forEach(k => {
      const v = metricas[k];
      tb.innerHTML += `<tr><td>${k}</td><td>${fmtNum(v)}</td></tr>`;
    });
  }

  function renderDisenos(disenos){
    const box = $("disenosBox");
    if(!box) return;

    if(!Array.isArray(disenos) || !disenos.length){
      box.innerHTML = `<div class="muted">Sin diseños disponibles</div>`;
      return;
    }

    // Chips
    box.innerHTML = disenos
      .slice(0, 200)
      .map(d => `<span class="pill">${String(d)}</span>`)
      .join("");

    if(disenos.length > 200){
      box.innerHTML += `<div class="muted" style="margin-top:10px;">Mostrando 200 de ${disenos.length}</div>`;
    }
  }

  function fillDisenoSelect(disenos){
    const sel = $("diseno");
    if(!sel) return;

    const keep = sel.value || "OTROS";
    const base = `<option value="OTROS">OTROS</option>`;

    if(!Array.isArray(disenos) || !disenos.length){
      sel.innerHTML = base;
      sel.value = keep;
      return;
    }

    
    const unique = Array.from(new Set(disenos.filter(Boolean).map(String)));
    const opts = unique.map(d => `<option value="${d}">${d}</option>`).join("");

    sel.innerHTML = base + opts;

    
    const exists = Array.from(sel.options).some(o => o.value === keep);
    sel.value = exists ? keep : "OTROS";
  }

  async function cargarInfo(){
    setStatus($("infoStatus"), "Cargando información del modelo...", "muted");
    $("infoEstado").textContent = "Cargando…";

    try{
      const res = await fetch("/api/ml/info");
      const data = await res.json().catch(() => ({}));

      if(!res.ok){
        const msg = data?.error || `Error HTTP ${res.status}`;
        $("infoEstado").textContent = "Error";
        setStatus($("infoStatus"), msg, "err");
        return;
      }

      
      $("infoModelo").value = data.modelo ?? "—";
      $("infoTargets").value = Array.isArray(data.targets) ? data.targets.join(", ") : (data.targets ?? "—");
      $("infoFeatures").value = Array.isArray(data.features) ? data.features.join(", ") : (data.features ?? "—");

      const fmin = data.fecha_min_entrenamiento ?? "—";
      const fmax = data.fecha_max_entrenamiento ?? "—";
      $("infoRango").value = `${fmin} → ${fmax}`;

      renderMetricas(data.metricas);
      renderDisenos(data.disenos_disponibles);
      fillDisenoSelect(data.disenos_disponibles);

      $("infoEstado").textContent = "OK";
      setStatus($("infoStatus"), "Modelo cargado correctamente.", "ok");
    } catch(err){
      console.error(err);
      $("infoEstado").textContent = "Error";
      setStatus($("infoStatus"), "No se pudo conectar con /api/ml/info", "err");
    }
  }

  function renderResultado(obj){
    const box = $("resultadoBox");
    if(!box) return;

    if(!obj || typeof obj !== "object"){
      box.innerHTML = `<div class="muted">Sin datos</div>`;
      return;
    }

    const pred = obj.prediccion || {};
    const desglose = obj.desglose || null;

    const head = `
      <div class="pill">Fecha: <b>${obj.fecha ?? "—"}</b></div>
      <div class="pill">Turno: <b>${obj.turno ?? "—"}</b></div>
      <div class="pill">Diseño: <b>${obj.diseno ?? "—"}</b></div>
      <div class="pill">Volumen (m³): <b>${fmtNum(obj.volumen_m3 ?? obj.volumen ?? "—")}</b></div>
    `;

    const rowsMain = Object.keys(pred).map(k => `
      <tr><td>${k}</td><td>${fmtNum(pred[k])}</td></tr>
    `).join("");

    let desgloseHtml = "";
    if(desglose && typeof desglose === "object"){
      const dia = desglose.dia || null;
      const noche = desglose.noche || null;

      const rows = (label, o) => {
        if(!o || typeof o !== "object") return `<tr><td colspan="2" class="muted">Sin datos</td></tr>`;
        return Object.keys(o).map(k => `<tr><td>${k}</td><td>${fmtNum(o[k])}</td></tr>`).join("");
      };

      desgloseHtml = `
        <details style="margin-top:12px;">
          <summary>Ver desglose por turno</summary>
          <div class="row" style="margin-top:10px;">
            <div>
              <div class="muted" style="margin-bottom:6px;"><b>DIA</b></div>
              <table>
                <thead><tr><th>Material</th><th>Valor</th></tr></thead>
                <tbody>${rows("DIA", dia)}</tbody>
              </table>
            </div>
            <div>
              <div class="muted" style="margin-bottom:6px;"><b>NOCHE</b></div>
              <table>
                <thead><tr><th>Material</th><th>Valor</th></tr></thead>
                <tbody>${rows("NOCHE", noche)}</tbody>
              </table>
            </div>
          </div>
        </details>
      `;
    }

    box.innerHTML = `
      <div style="margin-bottom:10px;">${head}</div>
      <table>
        <thead>
          <tr>
            <th>Material</th>
            <th>Predicción</th>
          </tr>
        </thead>
        <tbody>
          ${rowsMain || `<tr><td colspan="2" class="muted">Sin predicción</td></tr>`}
        </tbody>
      </table>
      ${desgloseHtml}
    `;
  }

  async function predecir(){
    const fecha = $("fecha").value;
    const turno = $("turno").value || null;
    const diseno = $("diseno").value || "OTROS";
    const volumen = $("volumen").value;

    if(!fecha){
      setStatus($("predStatus"), "Debes seleccionar una fecha.", "err");
      return;
    }

    const payload = {
      fecha,
      turno: turno,     
      diseno,
      volumen
    };

    setStatus($("predStatus"), "Prediciendo...", "muted");

    try{
      const res = await fetch("/api/ml/predecir", {
        method:"POST",
        headers:{ "Content-Type":"application/json" },
        body: JSON.stringify(payload)
      });

      const data = await res.json().catch(() => ({}));

      if(!res.ok){
        setStatus($("predStatus"), data?.error || `Error HTTP ${res.status}`, "err");
        renderResultado(null);
        window.__ml_last_result = null;
        return;
      }

      setStatus($("predStatus"), "OK", "ok");
      renderResultado(data);
      window.__ml_last_result = data;

    } catch(err){
      console.error(err);
      setStatus($("predStatus"), "No se pudo conectar con /api/ml/predecir", "err");
      renderResultado(null);
      window.__ml_last_result = null;
    }
  }

  async function predecirBatch(){
    const txt = ($("batchJson").value || "").trim();
    if(!txt){
      setStatus($("batchStatus"), "Pega un JSON válido en el cuadro.", "err");
      return;
    }

    let payload;
    try{
      payload = JSON.parse(txt);
    } catch(e){
      setStatus($("batchStatus"), "JSON inválido (revisa comillas y llaves).", "err");
      return;
    }

    setStatus($("batchStatus"), "Ejecutando batch...", "muted");
    $("batchOut").innerHTML = "";

    try{
      const res = await fetch("/api/ml/predecir_batch", {
        method:"POST",
        headers:{ "Content-Type":"application/json" },
        body: JSON.stringify(payload)
      });

      const data = await res.json().catch(() => ({}));

      if(!res.ok){
        setStatus($("batchStatus"), data?.error || `Error HTTP ${res.status}`, "err");
        return;
      }

      setStatus($("batchStatus"), `OK (éxitos: ${data.exitos ?? "?"}, errores: ${data.errores ?? "?"})`, "ok");

      const okList = Array.isArray(data.resultados) ? data.resultados : [];
      const errList = Array.isArray(data.fallos) ? data.fallos : [];

      let html = "";

      if(okList.length){
        html += `<div class="pill">Predicciones OK: <b>${okList.length}</b></div>`;
        html += `<table style="margin-top:10px;">
          <thead><tr><th>#</th><th>Fecha</th><th>Turno</th><th>Diseño</th><th>Vol (m³)</th><th>Predicción</th></tr></thead><tbody>`;
        okList.forEach((r, i) => {
          const p = r.prediccion || {};
          html += `<tr>
            <td>${i+1}</td>
            <td>${r.fecha ?? "—"}</td>
            <td>${r.turno ?? "—"}</td>
            <td>${r.diseno ?? "—"}</td>
            <td>${fmtNum(r.volumen_m3 ?? r.volumen ?? "—")}</td>
            <td class="mono">${JSON.stringify(p)}</td>
          </tr>`;
        });
        html += `</tbody></table>`;
      } else {
        html += `<div class="muted">No hubo resultados exitosos.</div>`;
      }

      if(errList.length){
        html += `<div style="margin-top:12px;" class="pill">Errores: <b>${errList.length}</b></div>`;
        html += `<table style="margin-top:10px;">
          <thead><tr><th>#</th><th>Entrada</th><th>Error</th></tr></thead><tbody>`;
        errList.forEach((r, i) => {
          html += `<tr>
            <td>${i+1}</td>
            <td class="mono">${JSON.stringify(r.entrada ?? r)}</td>
            <td>${r.error ?? "Error"}</td>
          </tr>`;
        });
        html += `</tbody></table>`;
      }

      $("batchOut").innerHTML = html;

    } catch(err){
      console.error(err);
      setStatus($("batchStatus"), "No se pudo conectar con /api/ml/predecir_batch", "err");
    }
  }

  async function copiarJson(){
    const obj = window.__ml_last_result;
    if(!obj){
      setStatus($("predStatus"), "No hay resultado para copiar.", "err");
      return;
    }
    try{
      await navigator.clipboard.writeText(JSON.stringify(obj, null, 2));
      setStatus($("predStatus"), "JSON copiado al portapapeles.", "ok");
    } catch(e){
      setStatus($("predStatus"), "No se pudo copiar (tu navegador bloqueó el portapapeles).", "err");
    }
  }

  function cargarEjemplo(){
    const example = {
      predicciones: [
        { fecha: "2026-03-01", turno: "DIA", diseno: "OTROS", volumen: 6 },
        { fecha: "2026-03-02", turno: "NOCHE", diseno: "OTROS", volumen: 8 },
        { fecha: "2026-03-03", turno: null, diseno: "OTROS", volumen: 10 }
      ]
    };
    $("batchJson").value = JSON.stringify(example, null, 2);
  }

  document.addEventListener("DOMContentLoaded", () => {
    // default fecha = hoy (local)
    const d = new Date();
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth()+1).padStart(2,"0");
    const dd = String(d.getDate()).padStart(2,"0");
    if($("fecha")) $("fecha").value = `${yyyy}-${mm}-${dd}`;

    $("btnRefreshInfo")?.addEventListener("click", cargarInfo);
    $("btnPredecir")?.addEventListener("click", predecir);
    $("btnCopiarJson")?.addEventListener("click", copiarJson);

    $("btnPredecirBatch")?.addEventListener("click", predecirBatch);
    $("btnCargarEjemplo")?.addEventListener("click", cargarEjemplo);

    cargarInfo();
  });

})();
