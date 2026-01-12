import pandas as pd
import numpy as np
from datetime import datetime
import os

class LimpiadorDatos:
    def __init__(self, archivo_entrada='Datos_Stat_Model.csv', archivo_salida='DatosLimpios.csv'):

        self.archivo_entrada = archivo_entrada
        self.archivo_salida = archivo_salida
        self.df_original = None
        self.df_limpio = None
        self.datos_eliminados = {
            'faltantes': [],
            'irracionales': [],
            'outliers': []
        }
        
    def cargar_datos(self):
        try:
            ruta_completa = os.path.join(os.path.dirname(__file__), self.archivo_entrada)
            self.df_original = pd.read_csv(ruta_completa)
            print(f"Datos cargados exitosamente")
            print(f"Total de filas: {len(self.df_original)}")
            print(f"Total de columnas: {len(self.df_original.columns)}")
            print(f"\nColumnas: {list(self.df_original.columns)}\n")
            return True
        except FileNotFoundError:
            print(f"Error: No se encontró el archivo {self.archivo_entrada}")
            return False
        except Exception as e:
            print(f"Error al cargar datos: {str(e)}")
            return False
    
    def eliminar_datos_faltantes(self):
        print("1. ELIMINANDO DATOS FALTANTES")
        
        # Identificar filas con datos faltantes
        filas_con_faltantes = self.df_limpio[self.df_limpio.isnull().any(axis=1)]
        
        if len(filas_con_faltantes) > 0:
            print(f"\nSe encontraron {len(filas_con_faltantes)} filas con datos faltantes:")
            print("\nPrimeras 10 filas con datos faltantes:")
            print(filas_con_faltantes.head(10).to_string())
            
            # Mostrar resumen de columnas con faltantes
            columnas_faltantes = filas_con_faltantes.isnull().sum()
            columnas_faltantes = columnas_faltantes[columnas_faltantes > 0]
            print(f"\nColumnas con datos faltantes:")
            for col, cantidad in columnas_faltantes.items():
                print(f"  - {col}: {cantidad} valores faltantes")
            
            # Guardar datos eliminados
            self.datos_eliminados['faltantes'] = filas_con_faltantes.copy()
            
            # Eliminar filas con datos faltantes
            self.df_limpio = self.df_limpio.dropna()
            print(f"\nFilas eliminadas: {len(filas_con_faltantes)}")
        else:
            print("\nNo se encontraron datos faltantes")
        
        print(f"Filas restantes: {len(self.df_limpio)}\n")
    
    def eliminar_datos_irracionales(self):
        """Elimina filas con datos irracionales"""
        print("2. ELIMINANDO DATOS IRRACIONALES")

        
        filas_eliminadas = pd.DataFrame()
        tamaño_inicial = len(self.df_limpio)
        
        # Columnas numéricas a validar
        columnas_numericas = [
            'Volumen (m3)', 'Humedad arena (%)', 'Arena (kg)', 'Grava (kg)',
            'Cemento (kg)', 'Agua (kg)', 'RHEO 1000 (kg)', 'BASF 719 (kg)',
            'Delvo (litros)', 'MasterGlenium 7950', 'MasterGlenium 7970',
            'Sika PP 48 (kg)-BARCHIP'
        ]
        
        # 1. Valores negativos
        print("\n Buscando valores negativos...")
        for col in columnas_numericas:
            if col in self.df_limpio.columns:
                filas_negativas = self.df_limpio[self.df_limpio[col] < 0]
                if len(filas_negativas) > 0:
                    print(f"{col}: {len(filas_negativas)} valores negativos encontrados")
                    filas_eliminadas = pd.concat([filas_eliminadas, filas_negativas])
        
        # 2. Humedad fuera de rango razonable (0-100%)
        print("\n Validando humedad...")
        if 'Humedad arena (%)' in self.df_limpio.columns:
            filas_humedad_invalida = self.df_limpio[
                (self.df_limpio['Humedad arena (%)'] < 0) | 
                (self.df_limpio['Humedad arena (%)'] > 1)
            ]
            if len(filas_humedad_invalida) > 0:
                print(f"Humedad fuera de rango (0-100%): {len(filas_humedad_invalida)} filas")
                filas_eliminadas = pd.concat([filas_eliminadas, filas_humedad_invalida])
        
        # 3. Volumen cero o muy pequeño
        print("\n Validando volumen...")
        if 'Volumen (m3)' in self.df_limpio.columns:
            filas_volumen_invalido = self.df_limpio[self.df_limpio['Volumen (m3)'] <= 0]
            if len(filas_volumen_invalido) > 0:
                print(f"  Volumen cero o negativo: {len(filas_volumen_invalido)} filas")
                filas_eliminadas = pd.concat([filas_eliminadas, filas_volumen_invalido])
        
        # 4. Inconsistencias en proporciones (ejemplo: cemento muy alto para volumen bajo)
        print("\n Validando proporciones...")
        if 'Volumen (m3)' in self.df_limpio.columns and 'Cemento (kg)' in self.df_limpio.columns:
            # Razón cemento/volumen mayor a 1000 kg/m3 es irracional
            self.df_limpio['ratio_cemento'] = self.df_limpio['Cemento (kg)'] / self.df_limpio['Volumen (m3)']
            filas_ratio_alto = self.df_limpio[self.df_limpio['ratio_cemento'] > 1000]
            if len(filas_ratio_alto) > 0:
                print(f" Proporción cemento/volumen muy alta: {len(filas_ratio_alto)} filas")
                filas_eliminadas = pd.concat([filas_eliminadas, filas_ratio_alto])
            self.df_limpio = self.df_limpio.drop('ratio_cemento', axis=1)
        
        # Eliminar duplicados en filas_eliminadas
        if len(filas_eliminadas) > 0:
            filas_eliminadas = filas_eliminadas.drop_duplicates()
            print(f"\n Total de filas con datos irracionales: {len(filas_eliminadas)}")
            print("\nPrimeras 10 filas con datos irracionales:")
            print(filas_eliminadas.head(10).to_string())
            
            # Guardar datos eliminados
            self.datos_eliminados['irracionales'] = filas_eliminadas.copy()
            
            # Eliminar filas irracionales
            self.df_limpio = self.df_limpio.drop(filas_eliminadas.index)
            self.df_limpio = self.df_limpio.reset_index(drop=True)
        else:
            print("\n No se encontraron datos irracionales")
        
        filas_eliminadas_total = tamaño_inicial - len(self.df_limpio)
        print(f"\n Filas eliminadas: {filas_eliminadas_total}")
        print(f" Filas restantes: {len(self.df_limpio)}\n")
    
    def eliminar_outliers(self, columnas_a_revisar=None, factor_iqr=1.5):
        """
        Elimina outliers usando el método IQR (Rango Intercuartílico)
        
        Args:
            columnas_a_revisar: Lista de columnas para detectar outliers (None = todas las numéricas)
            factor_iqr: Factor multiplicador del IQR (1.5 = outliers, 3.0 = outliers extremos)
        """

        print("3. ELIMINANDO OUTLIERS (DATOS EXTREMOS)")
  
        print(f"Método: IQR (Rango Intercuartílico) con factor {factor_iqr}")
        
        if columnas_a_revisar is None:
            # Seleccionar solo columnas numéricas
            columnas_a_revisar = self.df_limpio.select_dtypes(include=[np.number]).columns.tolist()
        
        filas_con_outliers = pd.DataFrame()
        tamaño_inicial = len(self.df_limpio)
        
        print(f"\n Analizando {len(columnas_a_revisar)} columnas numéricas...\n")
        
        for columna in columnas_a_revisar:
            if columna in self.df_limpio.columns:
                # Calcular Q1, Q3 e IQR
                Q1 = self.df_limpio[columna].quantile(0.25)
                Q3 = self.df_limpio[columna].quantile(0.75)
                IQR = Q3 - Q1
                
                # Definir límites
                limite_inferior = Q1 - factor_iqr * IQR
                limite_superior = Q3 + factor_iqr * IQR
                
                # Identificar outliers
                outliers = self.df_limpio[
                    (self.df_limpio[columna] < limite_inferior) | 
                    (self.df_limpio[columna] > limite_superior)
                ]
                
                if len(outliers) > 0:
                    print(f"  {columna}:")
                    print(f"      Rango normal: [{limite_inferior:.2f}, {limite_superior:.2f}]")
                    print(f"      Outliers encontrados: {len(outliers)}")
                    filas_con_outliers = pd.concat([filas_con_outliers, outliers])
        
        # Eliminar duplicados
        if len(filas_con_outliers) > 0:
            filas_con_outliers = filas_con_outliers.drop_duplicates()
            print(f"\n Total de filas con outliers: {len(filas_con_outliers)}")
            print("\nPrimeras 10 filas con outliers:")
            print(filas_con_outliers.head(10).to_string())
            
            # Guardar datos eliminados
            self.datos_eliminados['outliers'] = filas_con_outliers.copy()
            
            # Eliminar outliers
            self.df_limpio = self.df_limpio.drop(filas_con_outliers.index)
            self.df_limpio = self.df_limpio.reset_index(drop=True)
        else:
            print("\n No se encontraron outliers")
        
        filas_eliminadas_total = tamaño_inicial - len(self.df_limpio)
        print(f"\n Filas eliminadas: {filas_eliminadas_total}")
        print(f" Filas restantes: {len(self.df_limpio)}\n")
    
    def exportar_datos_limpios(self):
        """Exporta los datos limpios a un archivo CSV"""
        try:
            ruta_completa = os.path.join(os.path.dirname(__file__), self.archivo_salida)
            self.df_limpio.to_csv(ruta_completa, index=False)
            print(f" Datos limpios exportados exitosamente a: {self.archivo_salida}")
            return True
        except Exception as e:
            print(f" Error al exportar datos: {str(e)}")
            return False
    
    def mostrar_resumen(self):
        """Muestra un resumen de la limpieza de datos"""

        print("RESUMEN DE LIMPIEZA DE DATOS")
     
        
        total_eliminados = sum([
            len(self.datos_eliminados['faltantes']),
            len(self.datos_eliminados['irracionales']),
            len(self.datos_eliminados['outliers'])
        ])
        
        print(f"\n Estadísticas:")
        print(f"   Filas originales: {len(self.df_original)}")
        print(f"   Filas eliminadas por datos faltantes: {len(self.datos_eliminados['faltantes'])}")
        print(f"   Filas eliminadas por datos irracionales: {len(self.datos_eliminados['irracionales'])}")
        print(f"   Filas eliminadas por outliers: {len(self.datos_eliminados['outliers'])}")
        print(f"   Total de filas eliminadas: {total_eliminados}")
        print(f"   Filas finales: {len(self.df_limpio)}")
        print(f"   Porcentaje de datos conservados: {(len(self.df_limpio)/len(self.df_original)*100):.2f}%")
        print(f"   Porcentaje de datos eliminados: {(total_eliminados/len(self.df_original)*100):.2f}%")
        
        print(f"\n Archivos:")
        print(f"   Entrada: {self.archivo_entrada}")
        print(f"   Salida: {self.archivo_salida}")

    
    def ejecutar_limpieza_completa(self, factor_iqr=1.5):
        """
        Ejecuta el proceso completo de limpieza de datos
        
        Args:
            factor_iqr: Factor para detección de outliers (1.5=normal, 3.0=extremo)
        """
        print("\n" + "="*80)
        print("INICIO DE LIMPIEZA Y PREPARACIÓN DE DATOS")
        print(f"Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Cargar datos
        if not self.cargar_datos():
            return False
        
        # Copiar datos originales para trabajar
        self.df_limpio = self.df_original.copy()
        
        # Ejecutar limpieza
        self.eliminar_datos_faltantes()
        self.eliminar_datos_irracionales()
        self.eliminar_outliers(factor_iqr=factor_iqr)
        
        # Exportar datos limpios
        if self.exportar_datos_limpios():
            self.mostrar_resumen()
            return True
        return False


def main():
    """Función principal"""
    # Crear instancia del limpiador
    limpiador = LimpiadorDatos(
        archivo_entrada='Datos_Stat_Model.csv',
        archivo_salida='DatosLimpios.csv'
    )
    
    # Ejecutar limpieza completa
    # factor_iqr: 1.5 = outliers moderados, 3.0 = solo outliers extremos
    exito = limpiador.ejecutar_limpieza_completa(factor_iqr=1.5)
    
    if exito:
        print(" Proceso completado exitosamente")
    else:
        print(" El proceso terminó con errores")


if __name__ == "__main__":
    main()
