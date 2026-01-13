(() => {
  "use strict";

  function $(id){ return document.getElementById(id); }

  function val(id){
    const el = $(id);
    return el ? el.value : "";
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
  });
})();
