"""
Script de prueba para la función obtener_estado_materiales()
"""

from utils.loaders import obtener_estado_materiales

def main():
    print("=" * 70)
    print("ESTADO DE MATERIALES EN INVENTARIO")
    print("=" * 70)
    
    # Obtener estado de todos los materiales
    materiales = obtener_estado_materiales()
    
    if not materiales:
        print("❌ No se pudieron obtener los materiales")
        return
    
    # Separar por estado
    criticos = [m for m in materiales if m['estado'] == 'critico']
    bajos = [m for m in materiales if m['estado'] == 'bajo']
    ok = [m for m in materiales if m['estado'] == 'ok']
    
    # Mostrar resumen
    print(f"\n📊 RESUMEN:")
    print(f"   Total de materiales: {len(materiales)}")
    print(f"   ❌ Críticos: {len(criticos)}")
    print(f"   ⚠️  Bajos: {len(bajos)}")
    print(f"   ✅ OK: {len(ok)}")
    
    # Mostrar materiales críticos
    if criticos:
        print("\n" + "=" * 70)
        print("❌ MATERIALES EN ESTADO CRÍTICO (< 50% del mínimo)")
        print("=" * 70)
        for m in criticos:
            print(f"\n{m['material']}")
            print(f"   Stock actual: {m['stock_actual']:,.2f} {m['unidad']}")
            print(f"   Stock mínimo: {m['stock_minimo']:,.2f} {m['unidad']}")
            porcentaje = (m['stock_actual'] / m['stock_minimo'] * 100) if m['stock_minimo'] > 0 else 0
            print(f"   Nivel: {porcentaje:.1f}% del mínimo")
    
    # Mostrar materiales bajos
    if bajos:
        print("\n" + "=" * 70)
        print("⚠️ MATERIALES CON STOCK BAJO (<= mínimo)")
        print("=" * 70)
        for m in bajos:
            print(f"\n{m['material']}")
            print(f"   Stock actual: {m['stock_actual']:,.2f} {m['unidad']}")
            print(f"   Stock mínimo: {m['stock_minimo']:,.2f} {m['unidad']}")
            diferencia = m['stock_actual'] - m['stock_minimo']
            print(f"   Diferencia: {diferencia:,.2f} {m['unidad']}")
    
    # Mostrar materiales OK (resumido)
    if ok:
        print("\n" + "=" * 70)
        print(f"✅ MATERIALES CON STOCK ADECUADO ({len(ok)} materiales)")
        print("=" * 70)
        for m in ok:
            excedente = m['stock_actual'] - m['stock_minimo']
            print(f"   {m['material']:30} | Stock: {m['stock_actual']:>10,.2f} {m['unidad']:4} | Excedente: {excedente:>10,.2f}")
    
    # Tabla completa
    print("\n" + "=" * 70)
    print("TABLA COMPLETA DE MATERIALES")
    print("=" * 70)
    print(f"{'Material':<30} {'Unidad':>6} {'Stock Actual':>15} {'Stock Mínimo':>15} {'Estado':>10}")
    print("-" * 70)
    
    for m in materiales:
        icono = "❌" if m['estado'] == 'critico' else ("⚠️" if m['estado'] == 'bajo' else "✅")
        print(f"{m['material']:<30} {m['unidad']:>6} {m['stock_actual']:>15,.2f} {m['stock_minimo']:>15,.2f} {icono:>3} {m['estado']}")
    
    print("=" * 70)

if __name__ == "__main__":
    main()
