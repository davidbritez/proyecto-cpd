# importar_ventas_v2.py
# Script de simulación transaccional distribuida en tiempo real
# Cada fila del CSV simula ser procesada y conectada por una sucursal distinta
# Cátedra: Procesamiento de Datos - UCOM 2026
# Docente: Ing. David Britez

import os
import time
import random
import pandas as pd
import psycopg2

# Configuración de conexiones para cada sucursal en el CPD
# Mapeamos cada sucursal lógica a su puerto de red expuesto por Docker Compose
CONFIG_SUCURSALES = {
    "Sucursal_Asuncion": {
        "host": "localhost",
        "port": "5432",
        "database": "matriz_db",
        "user": "ucom_admin",
        "password": "password_matriz",
        "color": "\033[93m"  # Amarillo
    },
    "Sucursal_CDE": {
        "host": "localhost",
        "port": "5433",
        "database": "sucursal_a_db",
        "user": "ucom_admin",
        "password": "password_sucursal_a",
        "color": "\033[96m"  # Cian
    },
    "Sucursal_ENC": {
        "host": "localhost",
        "port": "5434",
        "database": "sucursal_b_db",
        "user": "ucom_admin",
        "password": "password_sucursal_b",
        "color": "\033[92m"  # Verde
    },
    "Sucursal_COV": {
        "host": "localhost",
        "port": "5435",
        "database": "sucursal_c_db",
        "user": "ucom_admin",
        "password": "password_sucursal_c",
        "color": "\033[94m"  # Azul
    }
}

RESET_COLOR = "\033[0m"

def ejecutar_simulacion(ruta_csv, db_offline=False):
    print("🚀 INICIANDO SIMULACIÓN DE TRÁFICO TRANSACCIONAL DISTRIBUIDO EN EL CPD...")
    print("=" * 90)
    
    # 1. Leer el archivo CSV
    if not os.path.exists(ruta_csv):
        print(f"❌ Error: No se encuentra el archivo '{ruta_csv}' en el directorio actual.")
        return
        
    df = pd.read_csv(ruta_csv)
    
    # 2. Limitar estrictamente a los primeros 9 registros
    df_simulacion = df.head(9).copy()
    print(f"📋 Cargados los primeros {len(df_simulacion)} registros para la demostración en vivo.\n")
    
    # Lista de nombres de sucursales para selección aleatoria
    lista_sucursales = list(CONFIG_SUCURSALES.keys())
    
    # 3. Procesar fila por fila con delay de 2 segundos
    for idx, row in df_simulacion.iterrows():
        # Selección aleatoria de la sucursal que genera la venta
        sucursal_elegida = random.choice(lista_sucursales)
        conf = CONFIG_SUCURSALES[sucursal_elegida]
        color = conf["color"]
        
        # Formatear el debug visual por consola
        print(f"{color}[TRANSACCIÓN #{idx + 1}] — Procesando en el nodo: {sucursal_elegida.upper()}{RESET_COLOR}")
        print(f"   ↳ Datos: Factura: {row['InvoiceNo']} | Item: {row['Description']} | Cantidad: {row['Quantity']} | Precio: L {row['UnitPrice']}")
        
        # Saneamiento rápido del registro
        desc = row["Description"] if not pd.isnull(row["Description"]) else "Sin descripción"
        cust_id = str(row["CustomerID"]).replace(".0", "") if not pd.isnull(row["CustomerID"]) else None
        
        if db_offline:
            # Simulación visual si la base de datos no está activa (modo demostración local)
            print(f"   ⚡ [SIMULADO] Conectándose a {conf['host']}:{conf['port']} -> DB: {conf['database']}")
            print(f"   ✅ [SIMULADO] Datos insertados con éxito en la tabla 'ventas_locales' de {sucursal_elegida}.")
        else:
            # Inserción real en la base de datos correspondiente
            try:
                print(f"   🔌 Conectando a {conf['host']}:{conf['port']} (Base de datos: {conf['database']})...")
                conn = psycopg2.connect(
                    host=conf["host"],
                    port=conf["port"],
                    database=conf["database"],
                    user=conf["user"],
                    password=conf["password"],
                    connect_timeout=3
                )
                cursor = conn.cursor()
                
                # Sentencia SQL de inserción
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
                print(f"   ✅ [ÉXITO] Transacción asentada físicamente en el nodo {sucursal_elegida}.")
                
            except Exception as e:
                print(f"   ❌ [FALLO DE CONEXIÓN] No se pudo escribir en {sucursal_elegida}.")
                print(f"      Detalle técnico: {e}")
                print("      💡 Asegúrate de haber ejecutado 'docker compose up -d' y el DDL en las sucursales.")
        
        print("-" * 90)
        # Delay pedagógico de 2 segundos para ver el flujo transaccional en tiempo real
        time.sleep(2)
        
    print("\n🏁 SIMULACIÓN FINALIZADA. El clúster ha procesado de forma distribuida las ventas del archivo CSV.")

if __name__ == "__main__":
    # Si ejecutas localmente sin los contenedores encendidos, cambia db_offline=True para simular el comportamiento visual
    # En el Codespaces del alumno, con Docker corriendo, debe ser db_offline=False
    ejecutar_simulacion("ventas_muestra.csv", db_offline=False)
