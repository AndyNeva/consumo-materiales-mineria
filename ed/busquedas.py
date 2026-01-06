from ed.estructuras import ArbolAVL, ArbolBinarioBusqueda
from utils.loaders import cargar_datos_tabla
import time
import sys

# Aumentar límite de recursión para BST degenerado
sys.setrecursionlimit(10000)

def comparar_tiempos_busqueda(fecha_objetivo: str):
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
    resultado_bst = bst.buscar(fecha_objetivo)
    t1 = time.time()  # Termina cronómetro para BST

    # AVL (Árbol Binario de Búsqueda auto-balanceado)
    avl = ArbolAVL()
    for d in datos:
        avl.insertar(d)
    t2 = time.time()  # Inicia cronómetro para AVL
    resultado_avl = avl.buscar(fecha_objetivo)
    t3 = time.time()  # Termina cronómetro para AVL

    # Muestra resultados comparativos de ambas estructuras
    print(f"Búsqueda por '{fecha_objetivo}':")
    print(f"  BST: {len(resultado_bst)} registros en {t1 - t0:.6f}s")
    print(f"  AVL: {len(resultado_avl)} registros en {t3 - t2:.6f}s")


def buscar_por_fecha(fecha: str):
    """Busca todos los despachos de una fecha específica usando AVL."""
    datos = cargar_datos_tabla('despachos')
    avl = ArbolAVL()
    for fila in datos:
        avl.insertar(fila)
    # Retorna todos los registros que coincidan con la fecha
    return avl.buscar(fecha)

def buscar_por_rango(fecha_inicio: str, fecha_fin: str):
    """Busca despachos dentro de un rango de fechas usando AVL."""
    datos = cargar_datos_tabla('despachos')
    avl = ArbolAVL()
    for fila in datos:
        avl.insertar(fila)
    # Retorna registros entre fecha_inicio y fecha_fin (inclusivo)
    return avl.buscar_rango(fecha_inicio, fecha_fin)

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

comparar_tiempos_busqueda('2025-11-15')
