(() => {
  "use strict";

  function $(id){ return document.getElementById(id); }

  function val(id){
    const el = $(id);
    return el ? el.value : "";
  }

  function num(v) {
    if (v === null || v === undefined || v === "") return "";
    const n = Number(v);
    if (Number.isNaN(n)) return v;
    return n.toLocaleString("es-EC", { maximumFractionDigits: 3 });
  }

  async function cargarDisenos(){
    const sel = $("diseno_mezcla");
    if (!sel) return;

    // Limpia y deja placeholder
    sel.innerHTML = `<option value="">Seleccione un diseño</option>`;

    const res = await fetch("/api/recetas", { method: "GET" });
    if (!res.ok){
      const txt = await res.text().catch(() => "");
      throw new Error(`No se pudo cargar /api/recetas (HTTP ${res.status}). ${txt.slice(0,120)}`);
    }

    const data = await res.json();
    const disenos = Array.isArray(data.disenos) ? data.disenos : [];

    for (const d of disenos){
      const opt = document.createElement("option");
      opt.value = d;
      opt.textContent = d;
      sel.appendChild(opt);
    }
  }

  function renderAlertasRegistro(payload) {
    const box = $("alertsBox");
    const tbody = $("tbodyAlertas");
    const hint = $("alertsHint");
    const alertaDeficit = $("alertaDeficit");
    if (!box || !tbody || !hint || !alertaDeficit) return;
    tbody.innerHTML = "";
    hint.textContent = "";
    alertaDeficit.style.display = "none";
    alertaDeficit.textContent = "";
    let hayDeficit = false;
    if (!payload || !payload.ok) {
      box.style.display = "none";
      return false;
    }
    for (const row of (payload.datos || [])) {
      if (row.estado && row.estado.toLowerCase().includes("deficit")) hayDeficit = true;
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${row.material}</td>
        <td>${row.unidad}</td>
        <td>${num(row.stock_actual)}</td>
        <td>${num(row.minimo)}</td>
        <td>${num(row.consumo_estimado)}</td>
        <td>${num(row.saldo)}</td>
        <td>${row.estado}</td>
      `;
      tbody.appendChild(tr);
    }
    if (hayDeficit) {
      alertaDeficit.textContent = "No puedes guardar: hay déficit de materiales. Corrige el stock o el consumo.";
      alertaDeficit.style.display = "block";
    }
    box.style.display = "block";
    return !hayDeficit;
  }

  async function mostrarCruceConsumo() {
    // Toma los valores del formulario actual
    const payload = {
      fecha: val("fecha"),
      volumen_m3: Number(val("volumen_m3")),
      diseno_mezcla: val("diseno_mezcla"),
      zona: val("zona"),
      wbs: val("wbs"),
      turno: val("turno"),
      arena_humedad_pct: Number(val("arena_humedad_pct") || 0),
      asentamiento_final_cm: Number(val("asentamiento_final_cm") || 0),
      temperatura_c: Number(val("temperatura_c") || 0),
    };
    // Validación básica
    if (!payload.fecha || !payload.diseno_mezcla) {
      alert("Completa la fecha y el diseño de mezcla para ver el cruce.");
      return;
    }
    const res = await fetch("/api/cruce_consumo_registro", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.ok) {
      alert(data.error || `Error al consultar cruce consumo (HTTP ${res.status})`);
      return;
    }
    // Render tabla y mensaje en el DOM
    const puedeGuardar = renderAlertasRegistro(data);
    // Deshabilitar o habilitar el botón de guardar
    const btnGuardar = document.querySelector("#registroForm button[type='submit']");
    if (btnGuardar) btnGuardar.disabled = !puedeGuardar;
    if (btnGuardar && !puedeGuardar) {
      btnGuardar.title = "No puedes guardar: hay déficit de materiales";
    } else if (btnGuardar) {
      btnGuardar.title = "";
    }
  }
  async function obtenerCsrfToken(){
  const res = await fetch("/api/csrf-token");
  const data = await res.json();
  return data.csrf_token;
  }
  async function guardarDespacho(e){
    e.preventDefault();

    const payload = {
      fecha: val("fecha"),
      volumen_m3: Number(val("volumen_m3")),
      diseno_mezcla: val("diseno_mezcla"),
      zona: val("zona"),
      wbs: val("wbs"),
      turno: val("turno"),
      arena_humedad_pct: Number(val("arena_humedad_pct") || 0),
      asentamiento_final_cm: Number(val("asentamiento_final_cm") || 0),
      temperatura_c: Number(val("temperatura_c") || 0),
    };

    const res = await fetch("/api/despachos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json().catch(() => ({}));

    if (!res.ok || !data.ok){
      const msg = data.error || `Error al guardar (HTTP ${res.status})`;
      alert(msg);
      return;
    }

    window.location.href = "/dashboard";
  }

  document.addEventListener("DOMContentLoaded", async () => {
    try {
      await cargarDisenos();
    } catch (err){
      console.error(err);
      alert(String(err.message || err));
    }

    const form = document.querySelector("#registroForm");
    if (!form){
      console.warn("No existe #registroForm en registro.html");
      return;
    }
    form.addEventListener("submit", guardarDespacho);
    // Botón de cruce
    const btnCruce = $("btnCruceConsumo");
    if (btnCruce) btnCruce.onclick = mostrarCruceConsumo;
    // Al cargar, el botón de guardar debe estar deshabilitado hasta que se haga el cruce
    const btnGuardar = document.querySelector("#registroForm button[type='submit']");
    if (btnGuardar) btnGuardar.disabled = true;
    // Ocultar la tabla de alertas al inicio
    const box = $("alertsBox");
    if (box) box.style.display = "none";
  });
})();
