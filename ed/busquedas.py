from ed.estructuras import ArbolAVL, ArbolBinarioBusqueda
from utils.loaders import cargar_datos_tabla
import time
import sys

# Aumentar límite de recursión para BST degenerado
sys.setrecursionlimit(10000)

def buscar_por_rango(fecha_inicio: str, fecha_fin:str):
    """
    Método para comparar tiempos de búsqueda de ambas estructuras de datos.
    """
    # Carga todos los registros de despachos desde la base de datos
    datos = cargar_datos_tabla('despachos')

    # BST simple (Árbol Binario de Búsqueda sin balanceo)
    bst = ArbolBinarioBusqueda()
    for d in datos:
        bst.insertar(d)
    t0 = time.time()  # Inicia cronómetro para BST
    resultado_bst = bst.buscar_rango(fecha_inicio, fecha_fin)
    t1 = time.time()  # Termina cronómetro para BST
    tiempo_bst = t1-t0

    # AVL (Árbol Binario de Búsqueda auto-balanceado)
    avl = ArbolAVL()
    for d in datos:
        avl.insertar(d)
    t2 = time.time()  # Inicia cronómetro para AVL
    resultado_avl = avl.buscar_rango(fecha_inicio, fecha_fin)
    t3 = time.time()  # Termina cronómetro para AVL
    tiempo_avl = t3-t2

    # Muestra resultados comparativos de ambas estructuras
    print(f"Búsqueda del '{fecha_inicio}' al '{fecha_fin}':")
    print(f"  BST: {len(resultado_bst)} registros en {tiempo_bst:.6f}s")
    print(f"  AVL: {len(resultado_avl)} registros en {tiempo_avl:.6f}s")
    return resultado_avl, tiempo_bst, tiempo_avl

def busqueda_por_diseno(datos:list[dict], diseno:str):
    resultados = []
    for entrada in datos:
        if entrada['diseno_mezcla'] ==diseno:
            resultados.append(entrada)
    
    return resultados

def busqueda_por_destino(datos:list[dict], destino:str):
    resultados = []
    for entrada in datos:
        if entrada['zona'] ==destino:
            resultados.append(entrada)
    
    return resultados

buscar_por_rango('2025-11-15', '2025-11-20')
