import sys
import time
from utils.loaders import cargar_datos_tabla, convertir_formato_historial
from ed.estructuras import ArbolBinarioBusqueda, ArbolAVL

# Aumentar límite de recursión para árboles con muchos nodos
sys.setrecursionlimit(10000)


def buscar_por_rango(inicio, fin):
    """
    Compara tiempos de búsqueda BST vs AVL.
    Retorna formato compatible con historial.js
    """
    # Carga datos
    datos = cargar_datos_tabla('despachos')
    
    # BST simple (Árbol Binario de Búsqueda sin balanceo)
    bst = ArbolBinarioBusqueda()
    for d in datos:
        bst.insertar(d)
    t0 = time.perf_counter()  
    resultado_bst = bst.buscar_rango(inicio, fin)
    tiempo_bst = time.perf_counter() - t0
    
    # AVL (Árbol Binario de Búsqueda auto-balanceado)
    avl = ArbolAVL()
    for d in datos:
        avl.insertar(d)
    t0 = time.perf_counter()  # Mayor resolución que time.time()
    resultado_avl = avl.buscar_rango(inicio, fin)
    tiempo_avl = time.perf_counter() - t0
    
    # Convertir a microsegundos para mejor legibilidad
    tiempo_bst_ms = tiempo_bst * 1000
    tiempo_avl_ms = tiempo_avl * 1000
    
    print(f"Búsqueda '{inicio}' a '{fin}':")
    print(f"  BST: {len(resultado_bst)} registros en {tiempo_bst_ms:.4f}ms ({tiempo_bst:.6f}s)")
    print(f"  AVL: {len(resultado_avl)} registros en {tiempo_avl_ms:.4f}ms ({tiempo_avl:.6f}s)")
    
    # Convertir a formato esperado por frontend
    resultado = convertir_formato_historial(resultado_avl)
    
    return resultado, tiempo_bst, tiempo_avl


def busqueda_diseno_destino(resultados, diseno=None, destino=None, turno=None, wbs=None):
    """
    Filtra en memoria sobre los resultados ya obtenidos.
    """
    data = resultados or []

    if diseno and diseno != "Todos":
        data = [x for x in data if str(x.get("diseno", "")).strip() == str(diseno).strip()]

    if destino:
        d = str(destino).strip().lower()
        data = [x for x in data if d in str(x.get("zona", "")).strip().lower()]


    if turno and turno != "Todos":
        data = [x for x in data if str(x.get("turno", "")).strip() == str(turno).strip()]

    if wbs:
        w = str(wbs).strip().lower()
        data = [x for x in data if w in str(x.get("wbs", "")).strip().lower()]

    return data
