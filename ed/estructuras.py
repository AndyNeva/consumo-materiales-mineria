from abc import ABC, abstractmethod

class Nodo(ABC):
    """
    Nodo base abstracto para árboles binarios.
    """
    def __init__(self, fecha):
        self.fecha = fecha  # Clave de ordenamiento en el árbol
        self.registros = []  # Lista para manejar varias entradas el mismo día
        self._izq = None    # Atributo privado para hijo izquierdo
        self._der = None    # Atributo privado para hijo derecho


class ArbolBinario(ABC):
    """
    Árbol binario abstracto que implementa los métodos públicos insertar, buscar y recorrer.
    También define el método privado insertar recursivo e implementa los métodos privados buscar recursivo
    y recorrer recursivo. 
    """
    def __init__(self):
        self._raiz = None  # Raíz privada del árbol
    
    # Método público para insertar una nueva entrada
    def insertar(self, dato:dict):
        if not isinstance(dato, dict):
            raise TypeError("El dato debe ser un diccionario")
        if 'fecha' not in dato:
            raise KeyError("El dato debe contener la clave 'fecha'")
        fecha = dato['fecha']
        if not isinstance(fecha, str):
            raise TypeError("La fecha debe ser una cadena (YYYY-MM-DD)")
        self._raiz = self._insertar_recursivo(self._raiz, fecha, dato)
    
    # Método público para buscar entradas por fecha
    def buscar(self, fecha: str):
        if not isinstance(fecha, str):
            raise TypeError("La fecha debe ser una cadena (YYYY-MM-DD)")
        resultado = []
        self._buscar_recursivo(self._raiz, fecha, resultado)
        if resultado is None:
            raise ValueError("El árbol está vacío")
        return resultado
    
    # Método público para buscar entradas por rango de fecha
    def buscar_rango(self, fecha_inicio: str, fecha_fin: str):
        if not isinstance(fecha_inicio, str) and not isinstance(fecha_fin, str):
            raise TypeError("La fecha debe ser una cadena (YYYY-MM-DD)")
        resultado = []
        self._buscar_rango_recursivo(self._raiz, fecha_inicio, fecha_fin, resultado)
        return resultado

    # Método público para recorrer el árbol
    def inorden(self):
        resultado = []
        self._inorden_recursivo(self._raiz, resultado)
        if resultado is None:
            raise ValueError("El árbol está vacío")
        return resultado
    
    # Método abstracto para que cada clase inserte una entrada
    @abstractmethod
    def _insertar_recursivo(self, nodo, fecha, dato):
        pass
    
    # Método recursivo privado para buscar entradas por fecha
    def _buscar_recursivo(self, nodo, fecha, resultado):
        """Búsqueda binaria: descarta la mitad del árbol en cada paso."""
        if nodo is None:
            return  # Caso base: Se llega a hoja sin encontrar
        if fecha == nodo.fecha:
            resultado.extend(nodo.registros)  # Encontrado: agregar todos los registros
        elif fecha < nodo.fecha:
            self._buscar_recursivo(nodo._izq, fecha, resultado)  # Buscar en subárbol izquierdo
        else:
            self._buscar_recursivo(nodo._der, fecha, resultado)  # Buscar en subárbol derecho

    # Método recursivo privado para buscar entradas por rango fecha
    def _buscar_rango_recursivo(self, nodo, inicio, fin, resultado):
        if nodo is None:
            return
        # Si la fecha del nodo está dentro del rango
        if inicio <= nodo.fecha <= fin:
            resultado.extend(nodo.registros)
            self._buscar_rango_recursivo(nodo._izq, inicio, fin, resultado)
            self._buscar_rango_recursivo(nodo._der, inicio, fin, resultado)
        # Si la fecha es menor que el inicio, ir a la derecha
        elif nodo.fecha < inicio:
            self._buscar_rango_rec(nodo._der, inicio, fin, resultado)
        # Si la fecha es mayor que el fin, ir a la izquierda
        else:
            self._buscar_rango_rec(nodo._izq, inicio, fin, resultado)

    # Método recursivo privado para recorrer el árbol
    def _inorden_recursivo(self, nodo, resultado):
        """Recorrido inorden."""
        if nodo:
            self._inorden_recursivo(nodo._izq, resultado)   # 1. Procesar subárbol izquierdo
            resultado.extend(nodo.registros)                 # 2. Procesar raíz
            self._inorden_recursivo(nodo._der, resultado)   # 3. Procesar subárbol derecho

class NodoBST(Nodo):
    """Nodo simple para BST que hereda de Nodo."""
    def __init__(self, fecha):
        super().__init__(fecha)

class ArbolBinarioBusqueda(ArbolBinario):
    """
    BST clásico que hereda de ArbolBinario.
    
    Complejidad:
    - Mejor caso (balanceado): O(log n)
    - Peor caso (degenerado): O(n)
    """
    def __init__(self):
        self._raiz = None

    # Implementación concreta del método abstracto
    def _insertar_recursivo(self, nodo, fecha, dato):
        if nodo is None:
            nuevo = NodoBST(fecha)
            nuevo.registros.append(dato)
            return nuevo  # Caso base: crear nuevo nodo hoja
         
        # Propiedad BST - Mantener orden: izq < nodo < der
        if fecha < nodo.fecha:
            nodo._izq = self._insertar_recursivo(nodo._izq, fecha, dato)  # Insertar en subárbol izquierdo
        elif fecha > nodo.fecha:
            nodo._der = self._insertar_recursivo(nodo._der, fecha, dato)  # Insertar en subárbol derecho
        else:  # fecha == nodo.fecha
            nodo.registros.append(dato)  # ED: Agregar registro a fecha existente
        return nodo
    
class NodoAVL(Nodo):
    """Nodo AVL con información de altura para balanceo que hereda de Nodo."""
    def __init__(self, fecha):
        super().__init__(fecha)
        self._altura = 1  # Altura necesaria para calcular factor de balance

class ArbolAVL(ArbolBinario):
    """
    Árbol BST auto-balanceado que hereda de ArbolBinario.
    
    Complejidad garantizada: 
    O(log n) para inserción, búsqueda y eliminación
    """
    def __init__(self):
        self._raiz = None

    def _altura(self, nodo):
        """Altura del nodo: distancia máxima hasta una hoja."""
        if nodo is None:
            return 0  # Altura de subárbol vacío es 0
        return nodo._altura

    def _factor_balance(self, nodo):
        """+
        Factor de balance = altura(izq) - altura(der).
        
        Valores:
        - balance > 1: Subárbol izquierdo más pesado 
        - balance < -1: Subárbol derecho más pesado 
        - |balance| <= 1: Árbol balanceado
        """
        if nodo is None:
            return 0
        return self._altura(nodo._izq) - self._altura(nodo._der)

    def _actualizar_altura(self, nodo):
        """ED: Recalcula altura después de inserción/rotación."""
        if nodo:
            nodo._altura = 1 + max(self._altura(nodo._izq), self._altura(nodo._der))

    def _rotar_derecha(self, A):
        """
        Rotación simple derecha. Rebalancea subárbol pesado a la izquierda.
        """
        # Se definen los nodos a ser rotados
        B = A._izq
        T = B._der 
        # Rotación
        B._der = A   # A baja a la derecha
        A._izq = T   # T pasa a ser hijo izquierdo de A
        # Actualizar alturas (orden importante: primero A, luego B)
        self._actualizar_altura(A)
        self._actualizar_altura(B)
        return B  # Nueva raíz del subárbol

    def _rotar_izquierda(self, A):
        """
        Rotación simple izquierda. Rebalancea subárbol pesado a la derecha.
        """
         # Se definen los nodos a ser rotados
        B = A._der
        T = B._izq
        # Rotación
        B._izq = A   # A baja a la izquierda
        A._der = T   # T pasa a ser hijo derecho de A
        # Actualizar alturas (orden importante: primero A, luego B)
        self._actualizar_altura(A)
        self._actualizar_altura(B)
        return B  # Nueva raíz del subárbol

    def _insertar_recursivo(self, nodo, fecha, dato):
        """Inserción AVL con auto-balanceo."""
        # 1. Inserción normal (como BST)
        if nodo is None:
            nuevo = NodoAVL(fecha)
            nuevo.registros.append(dato)
            return nuevo

        # Mantener propiedad BST
        if fecha < nodo.fecha:
            nodo._izq = self._insertar_recursivo(nodo._izq, fecha, dato)
        elif fecha > nodo.fecha:
            nodo._der = self._insertar_recursivo(nodo._der, fecha, dato)
        else:
            nodo.registros.append(dato)
            return nodo  # No cambia la estructura

        # 2. Actualizar altura del nodo actual
        self._actualizar_altura(nodo)

        # 3. Obtener factor de balance para verificar si se desbalanceó
        balance = self._factor_balance(nodo)

        # 4. Casos de desbanlaceo
        
        # Caso 1: Izquierda-Izquierda (rotación simple derecha)
        # Inserción en subárbol izquierdo del hijo izquierdo
        if balance > 1 and fecha < nodo._izq.fecha:
            return self._rotar_derecha(nodo)
        
        # Caso 2: Derecha-Derecha (rotación simple izquierda)
        # Inserción en subárbol derecho del hijo derecho
        if balance < -1 and fecha > nodo._der.fecha:
            return self._rotar_izquierda(nodo)
        
        # Caso 3: Izquierda-Derecha (rotación doble: izq-der)
        # Inserción en subárbol derecho del hijo izquierdo
        if balance > 1 and fecha > nodo._izq.fecha:
            nodo._izq = self._rotar_izquierda(nodo._izq)  # Primera rotación
            return self._rotar_derecha(nodo)              # Segunda rotación
        
        # Caso 4: Derecha-Izquierda (rotación doble: der-izq)
        # Inserción en subárbol izquierdo del hijo derecho
        if balance < -1 and fecha < nodo._der.fecha:
            nodo._der = self._rotar_derecha(nodo._der)    # Primera rotación
            return self._rotar_izquierda(nodo)            # Segunda rotación

        return nodo  # Nodo balanceado

