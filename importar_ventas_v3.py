# importar_ventas_v3.py
# Script de simulación transaccional distribuida en tiempo real (Conexión Centralizada)
# Cada fila del CSV simula ser una venta remota que una sucursal inyecta en la base de datos central de Asunción
# Cátedra: Procesamiento de Datos - UCOM 2026
# Docente: Ing. David Britez

import os
import time
import random
import pandas as pd
import psycopg2

# Configuración única para conectarse a la Casa Matriz (Puerto 5432)
# Las sucursales se conectan remotamente al nodo central del CPD para asentar sus ventas
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "matriz_db"),
    "user": os.getenv("DB_USER", "ucom_admin"),
    "password": os.getenv("DB_PASSWORD", "password_matriz")  # Inyectada dinámicamente
}

# Colores y configuraciones visuales para simular de qué sucursal proviene el tráfico
SUCURSALES_DISPLAY = {
    "Sucursal_Asuncion": {"color": "\033[93m"},  # Amarillo
    "Sucursal_CDE": {"color": "\033[96m"},       # Cian
    "Sucursal_ENC": {"color": "\033[92m"},       # Verde
    "Sucursal_COV": {"color": "\033[94m"}        # Azul
}

RESET_COLOR = "\033[0m"

def ejecutar_simulacion_centralizada(ruta_csv):
    print("🚀 INICIANDO SIMULACIÓN DE CONEXIÓN REMOTA ABSTRACTA (RAMA HARDENING)...")
    print("==========================================================================================")
    
    if not os.path.exists(ruta_csv):
        print(f"❌ Error: No se encuentra el archivo '{ruta_csv}'.")
        return
        
    df = pd.read_csv(ruta_csv)
    df_simulacion = df.head(9).copy()
    lista_sucursales = list(SUCURSALES_DISPLAY.keys())
    
    for idx, row in df_simulacion.iterrows():
        sucursal_elegida = random.choice(lista_sucursales)
        color = SUCURSALES_DISPLAY[sucursal_elegida]["color"]
        desc = row["Description"] if not pd.isnull(row["Description"]) else "Sin descripción"
        cust_id = str(row["CustomerID"]).replace(".0", "") if not pd.isnull(row["CustomerID"]) else None
        
        print(f"{color}[CONEXIÓN REMOTA: {sucursal_elegida.upper()} ➔ CASA MATRIZ]{RESET_COLOR}")
        print(f"   🔌 Conectándose dinámicamente a {DB_CONFIG['host']}:{DB_CONFIG['port']}...")
        
        try:
            conn = psycopg2.connect(
                host=DB_CONFIG["host"],
                port=DB_CONFIG["port"],
                database=DB_CONFIG["database"],
                user=DB_CONFIG["user"],
                password=DB_CONFIG["password"],
                connect_timeout=3
            )
            cursor = conn.cursor()
            
            query = """
                INSERT INTO ventas_locales (invoice_no, stock_code, description, quantity, invoice_date, unit_price, customer_id, sucursal)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            """
            cursor.execute(query, (
                str(row["InvoiceNo"]),
                str(row["StockCode"]),
                desc,
                int(row["Quantity"]),
                row["InvoiceDate"],
                float(row["UnitPrice"]),
                cust_id,
                sucursal_elegida
            ))
            conn.commit()
            cursor.close()
            conn.close()
            print(f"   ✅ \033[92m[ÉXITO]\033[0m Venta asentada correctamente en la base de datos central.")
        except Exception as e:
            print(f"   ❌ [FALLO] No se pudo asentar la transacción.")
            print(f"      Detalle técnico: {e}")
            
        print("-" * 90)
        time.sleep(2)
        
    print("\n🏁 SIMULACIÓN FINALIZADA.")
if __name__ == "__main__":
    ejecutar_simulacion_centralizada("ventas_muestra.csv")
