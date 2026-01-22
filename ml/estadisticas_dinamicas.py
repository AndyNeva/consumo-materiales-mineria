"""
Estadísticas y gráficas dinámicas para el proyecto consumo-materiales.
Genera solo lo adecuado según número de registros y devuelve estructuras listas para JSON.
"""

import math
import pandas as pd


def _safe_float(x):
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _num(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return 0.0
    try:
        return float(v)
    except Exception:
        return 0.0


def _describe_series(s: pd.Series):
    s = pd.to_numeric(s, errors="coerce").dropna()
    if s.empty:
        return None
    return {
        "count": int(s.shape[0]),
        "min": float(s.min()),
        "p25": float(s.quantile(0.25)),
        "median": float(s.median()),
        "mean": float(s.mean()),
        "p75": float(s.quantile(0.75)),
        "max": float(s.max()),
        "std": float(s.std(ddof=1)) if s.shape[0] > 1 else 0.0,
    }


def _freq_table(s: pd.Series, top_n: int = 15):
    s = s.astype(str).fillna("").replace("nan", "")
    s = s[s.str.strip() != ""]
    if s.empty:
        return []
    vc = s.value_counts().head(top_n)
    return [{"label": k, "value": int(v)} for k, v in vc.items()]


def _corr_matrix(df: pd.DataFrame, cols: list[str]):
    work = df[cols].copy()
    for c in cols:
        work[c] = pd.to_numeric(work[c], errors="coerce")
    work = work.dropna()
    if work.shape[0] < 2:
        return None
    corr = work.corr(numeric_only=True)
    labels = list(corr.columns)
    matrix = corr.values.tolist()
    return {"labels": labels, "matrix": matrix}


def generar_graficas_desde_datos(df: pd.DataFrame, chart_name: str | None = None):
    """
    Genera un paquete de graficas/tablas dependiendo del volumen de datos.

    Retorna:
    {
      'num_registros': N,
      'graficas': {
         'resumen_basico': {...},
         'frecuencia_diseno': {...},
         'boxplot_volumen': {...},
         'hist_volumen': {...},
         'correlacion': {...}
      },
      'graficas_disponibles': [...]
    }
    """
    if df is None or df.empty:
        return {"num_registros": 0, "graficas": {}, "graficas_disponibles": []}

    n = int(df.shape[0])

    # Columnas esperadas si existen
    col_diseno = "diseno_mezcla" if "diseno_mezcla" in df.columns else None
    col_zona = "zona" if "zona" in df.columns else None
    col_turno = "turno" if "turno" in df.columns else None
    col_vol = "volumen_m3" if "volumen_m3" in df.columns else None

    graficas = {}

    # 1+) Resumen basico siempre que haya datos
    resumen = {
        "num_registros": n,
        "disenos_unicos": int(df[col_diseno].nunique()) if col_diseno else None,
        "zonas_unicas": int(df[col_zona].nunique()) if col_zona else None,
        "turnos_unicos": int(df[col_turno].nunique()) if col_turno else None,
    }
    if col_vol:
        resumen["volumen_stats"] = _describe_series(df[col_vol])
    graficas["resumen_basico"] = {"type": "summary", "data": resumen}

    # 5+) Frecuencia de disenos
    if n >= 5 and col_diseno:
        freqs = _freq_table(df[col_diseno])
        graficas["frecuencia_diseno"] = {
            "type": "bar",
            "title": "Frecuencia de disenos (Top)",
            "x": [r["label"] for r in freqs],
            "y": [r["value"] for r in freqs],
        }

    # 10+) Boxplot volumen
    if n >= 10 and col_vol:
        desc = _describe_series(df[col_vol])
        if desc:
            graficas["boxplot_volumen"] = {
                "type": "boxplot",
                "title": "Distribucion volumen (boxplot)",
                "stats": desc,
            }

    # 30+) Histograma volumen
    if n >= 30 and col_vol:
        s = pd.to_numeric(df[col_vol], errors="coerce").dropna()
        if not s.empty:
            bins = 10
            cats, edges = pd.cut(s, bins=bins, retbins=True, include_lowest=True)
            vc = cats.value_counts().sort_index()
            labels = [str(i) for i in vc.index.astype(str)]
            values = [int(v) for v in vc.values]
            graficas["hist_volumen"] = {
                "type": "hist",
                "title": "Histograma volumen",
                "labels": labels,
                "values": values,
            }

    # 50+) Correlacion (si hay suficientes columnas numericas)
    if n >= 50:
        numeric_cols = []
        for c in df.columns:
            if c in ("id", "fecha", "diseno_mezcla", "zona", "turno", "wbs", "lote"):
                continue
            # considerar numericos reales (incluye int/float)
            try:
                if df[c].dtype.kind in "biufc":
                    numeric_cols.append(c)
            except Exception:
                pass

        if len(numeric_cols) >= 2:
            corr = _corr_matrix(df, numeric_cols[:12])
            if corr:
                graficas["correlacion"] = {
                    "type": "corr",
                    "title": "Matriz correlacion",
                    "data": corr,
                }

    # Si piden solo una
    if chart_name:
        if chart_name in graficas:
            return {
                "num_registros": n,
                "graficas": {chart_name: graficas[chart_name]},
                "graficas_disponibles": list(graficas.keys()),
            }
        return {
            "num_registros": n,
            "graficas": {},
            "graficas_disponibles": list(graficas.keys()),
        }

    return {
        "num_registros": n,
        "graficas": graficas,
        "graficas_disponibles": list(graficas.keys()),
    }


def generar_graficas_json_desde_datos(df: pd.DataFrame, chart_name: str | None = None):
    """
    Version que devuelve solo dicts seguros para JSON (ya lo son).
    Se deja por compatibilidad si quieres usar un nombre mas explicito.
    """
    return generar_graficas_desde_datos(df, chart_name=chart_name)


# =========================
# Alias de compatibilidad
# =========================
def generar_graficos_dinamicos(df, chart_name=None):
    """
    Alias para compatibilidad con versiones anteriores.
    Redirige a generar_graficas_desde_datos.
    """
    return generar_graficas_desde_datos(df, chart_name=chart_name)


def _plotly_template_dark():
    return {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"color": "rgba(255,255,255,.92)"},
        "xaxis": {"gridcolor": "rgba(255,255,255,.08)", "zerolinecolor": "rgba(255,255,255,.10)"},
        "yaxis": {"gridcolor": "rgba(255,255,255,.08)", "zerolinecolor": "rgba(255,255,255,.10)"},
        "margin": {"l": 40, "r": 20, "t": 40, "b": 40},
    }
