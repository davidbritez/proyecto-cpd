# importar_ventas_v4.py
# Simulador Transaccional de Escala de Producción con Exportador de Métricas Nativo
# Cátedra: Procesamiento de Datos - UCOM
# Docente: Ing. David Britez

import os
import time
import random
import pandas as pd
import psycopg2
# Importamos los componentes oficiales de instrumentación de Prometheus
from prometheus_client import start_http_server, Counter, Histogram

# ==============================================================================
# INSTRUMENTACIÓN DE TELEMETRÍA (MÉTRICAS PERSONALIZADAS)
# ==============================================================================
# Definimos un Contador para rastrear la cantidad total de facturas asentadas
METRICA_VENTAS_TOTAL = Counter(
    "cpd_ventas_procesadas_total",
    "Cantidad total de facturas de venta registradas de manera exitosa",
    ["sucursal", "estado"]  # Etiquetas (labels) de filtrado dinámico
)

# Definimos un Contador para el volumen acumulado de facturación (Garantiza análisis de RED)
METRICA_MONTO_TOTAL = Counter(
    "cpd_monto_facturado_total",
    "Volumen monetario acumulado de transacciones comerciales exitosas",
    ["sucursal"]
)

# Definimos un Histograma para auditar la latencia exacta de inserción TCP en Postgres
METRICA_LATENCIA_TRANSACCION = Histogram(
    "cpd_latencia_transaccion_segundos",
    "Tiempo de respuesta del apretón de manos TCP e inserción SQL en el CPD",
    ["sucursal"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0) # Cubetas de tiempo para medir cuellos de botella
)

# Configuración de base de datos abstracta utilizando variables del .env
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"), # Apunta a nuestro balanceador perimetral HA-Proxy
    "database": os.getenv("DB_NAME", "matriz_db"),
    "user": os.getenv("DB_USER", "ucom_admin"),
    "password": os.getenv("DB_PASSWORD", "password_matriz")
}

SUCURSALES_DISPLAY = {
    "Sucursal_Asuncion": {"color": "\033[93m"},  # Amarillo
    "Sucursal_CDE": {"color": "\033[96m"},       # Cian
    "Sucursal_ENC": {"color": "\033[92m"},       # Verde
    "Sucursal_COV": {"color": "\033[94m"}        # Azul
}
RESET_COLOR = "\033[0m"

def ejecutar_simulacion_produccion():
    # 1. Detectar archivo de datos (Programación Defensiva)
    ruta_dataset = "online_retail_II.csv"
    ruta_backup = "ventas_muestra.csv"

    if os.path.exists(ruta_dataset):
        print(f"🔥 [OK] Dataset de producción pesado localizado: '{ruta_dataset}'")
        archivo_a_read = ruta_dataset
    elif os.path.exists(ruta_backup):
        print(f"⚠️ [AVISO] Dataset de producción no encontrado. Usando archivo de respaldo: '{ruta_backup}'")
        archivo_a_read = ruta_backup
    else:
        print("❌ [FALLO] No se localizó ningún archivo de ventas para procesar en el directorio.")
        return

    # 2. Levantar el servidor de métricas de Prometheus en el puerto 8000
    # Prometheus consumirá los datos desde http://localhost:8000/metrics
    start_http_server(8000)
    print("📊 [TELEMETRÍA] Exportador HTTP iniciado. Métricas listas en http://localhost:8000/metrics")
    print("🔌 Conectándose dinámicamente al CPD a través del balanceador...")

    # 3. Cargar datos usando Pandas
    df = pd.read_csv(archivo_a_read)
    print(f"📋 Cargados {len(df)} registros listos para la simulación transaccional continua.\n")

    lista_sucursales = list(SUCURSALES_DISPLAY.keys())

    # Procesar transacciones indefinidamente
    try:
        for idx, row in df.iterrows():
            sucursal_elegida = random.choice(lista_sucursales)
            color = SUCURSALES_DISPLAY[sucursal_elegida]["color"]

            # Saneamiento del registro
            desc = row["Description"] if not pd.isnull(row["Description"]) else "Facturación de Sucursal"
            cust_id = str(row["CustomerID"]).replace(".0", "") if not pd.isnull(row["CustomerID"]) else "Consumidor Final"
            monto_venta = float(row["Quantity"]) * float(row["Price"])

            # Si la fila tiene cantidades negativas (devoluciones), las saltamos para este ejercicio
            if monto_venta <= 0:
                continue

            print(f"{color}[CONEXIÓN REMOTA: {sucursal_elegida.upper()} ➔ CPD CENTRAL]{RESET_COLOR}")
            print(f"   🧾 Factura: {row['Invoice']} | Cliente: {cust_id} | Total: Gs. {monto_venta:,.2f}")

            # Registrar tiempo inicial para cálculo de latencia
            tiempo_inicio = time.time()

            try:
                # Conexión TCP al clúster de la base de datos central
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
                    str(row["Invoice"]),
                    str(row["StockCode"]),
                    desc,
                    int(row["Quantity"]),
                    row["InvoiceDate"],
                    float(row["Price"]),
                    cust_id,
                    sucursal_elegida
                ))
                conn.commit()
                cursor.close()
                conn.close()

                # Calcular latencia de la transacción exitosa
                latencia = time.time() - tiempo_inicio

                print(f"   ✅ [ÉXITO] Transacción registrada en {latencia:.4f}s.")

                # ==================================================================
                # REGISTRO DE MÉTRICAS EN CALIENTE
                # ==================================================================
                METRICA_VENTAS_TOTAL.labels(sucursal=sucursal_elegida, estado="exito").inc()
                METRICA_MONTO_TOTAL.labels(sucursal=sucursal_elegida).inc(monto_venta)
                METRICA_LATENCIA_TRANSACCION.labels(sucursal=sucursal_elegida).observe(latencia)

            except Exception as e:
                # En caso de fallo de conexión de red o caída de la base de datos
                latencia = time.time() - tiempo_inicio
                print(f"   ❌ [FALLO DE CONEXIÓN] La sucursal no pudo comunicarse con el host central.")
                print(f"      Detalle del error: {e}")

                # Registramos el fallo en las métricas para visibilidad en el panel
                METRICA_VENTAS_TOTAL.labels(sucursal=sucursal_elegida, estado="fallo").inc()
                METRICA_LATENCIA_TRANSACCION.labels(sucursal=sucursal_elegida).observe(latencia)

            print("-" * 90)
            # Retraso controlado para ver pasar los gráficos dinámicamente en el Dashboard
            time.sleep(1.5)

    except KeyboardInterrupt:
        print("\n🛑 Simulación pausada por el operador.")

if __name__ == "__main__":
    ejecutar_simulacion_produccion()