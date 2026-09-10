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
# 1. Contador para la cantidad total de facturas asentadas con éxito o fallo
METRICA_VENTAS_TOTAL = Counter(
    "cpd_ventas_procesadas_total",
    "Cantidad total de facturas de venta registradas de manera exitosa",
    ["sucursal", "estado"]  # Etiquetas (labels) de filtrado dinámico en Grafana
)

# 2. Contador para acumular el volumen de dinero facturado (Métrica de RED)
METRICA_MONTO_TOTAL = Counter(
    "cpd_monto_facturado_total",
    "Volumen monetario acumulado de transacciones comerciales exitosas",
    ["sucursal"]
)

# 3. Histograma para auditar la latencia de red e inserción física en PostgreSQL
METRICA_LATENCIA_TRANSACCION = Histogram(
    "cpd_latencia_transaccion_segundos",
    "Tiempo de respuesta de la inserción SQL a través del balanceador",
    ["sucursal"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0) # Segmentos de tiempo para medir cuellos de botella
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
    "Sucursal_Asuncion": {"color": "\033[93m"}, # Amarillo
    "Sucursal_CDE": {"color": "\033[96m"},      # Cian
    "Sucursal_ENC": {"color": "\033[92m"},      # Verde
    "Sucursal_COV": {"color": "\033[94m"}       # Azul
}
RESET_COLOR = "\033[0m"

def ejecutar_simulacion_produccion():
    # 1. Detectar archivo de datos (Programación Defensiva)
    ruta_dataset = "online_retail_II.csv"
    ruta_backup = "ventas_muestra.csv"
    
    if os.path.exists(ruta_dataset):
        print(f"🔥 [OK] Dataset de producción pesado localizado: '{ruta_dataset}'")
        archivo_a_leer = ruta_dataset
    elif os.path.exists(ruta_backup):
        print(f"⚠️ [AVISO] Dataset de producción no encontrado. Usando archivo de respaldo: '{ruta_backup}'")
        archivo_a_leer = ruta_backup
    else:
        print("❌ [FALLO] No se localizó ningún archivo de ventas para procesar en el directorio.")
        return

    # 2. Levantar el servidor de métricas de Prometheus en el puerto 8000
    # Forzamos addr='0.0.0.0' para abrir el puerto en todas las interfaces de red del contenedor/Codespace
    start_http_server(8000, addr='0.0.0.0')
    print("📊 [TELEMETRÍA] Exportador HTTP iniciado. Métricas listas en http://localhost:8000/metrics")
    print("🔌 Conectándose dinámicamente al CPD a través del balanceador...")

    # 3. Cargar datos usando Pandas optimizado en tipos de datos
    df = pd.read_csv(archivo_a_leer, dtype={
        "Invoice": str,
        "StockCode": str,
        "Description": str,
        "Country": str
    })
    print(f"📋 Cargados {len(df)} registros listos para la simulación transaccional continua.\n")
    
    lista_sucursales = list(SUCURSALES_DISPLAY.keys())

    # Procesar transacciones secuencialmente con retraso controlado
    try:
        for idx, row in df.iterrows():
            sucursal_elegida = random.choice(lista_sucursales)
            color = SUCURSALES_DISPLAY[sucursal_elegida]["color"]
            
            # Mapeo exacto según el df.info() de online_retail_II.csv
            factura_id = str(row["Invoice"])
            stock_code = str(row["StockCode"])
            desc = row["Description"] if not pd.isnull(row["Description"]) else "Facturación de Sucursal"
            
            # Saneamiento del identificador de cliente
            if pd.isnull(row["CustomerID"]):
                cust_id = "Consumidor Final"
            else:
                cust_id = str(int(row["CustomerID"])) # Evita flotantes feos de Pandas como 12345.0
                
            cantidad = int(row["Quantity"])
            precio_unitario = float(row["Price"])
            monto_venta = cantidad * precio_unitario
            
            # Saltamos transacciones de devoluciones o ajustes negativos
            if monto_venta <= 0:
                continue

            print(f"{color}[CONEXIÓN REMOTA: {sucursal_elegida.upper()} ➔ CPD CENTRAL]{RESET_COLOR}")
            print(f"   🧾 Factura: {factura_id} | Cliente: {cust_id} | Total: Gs. {monto_venta:,.2f}")
            
            # Guardamos la marca de tiempo de inicio
            tiempo_inicio = time.time()
            
            try:
                # Intento de conexión TCP al balanceador de carga del clúster central
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
                    factura_id,
                    stock_code,
                    desc,
                    cantidad,
                    row["InvoiceDate"],
                    precio_unitario,
                    cust_id,
                    sucursal_elegida
                ))
                conn.commit()
                cursor.close()
                conn.close()
                
                # Calcular latencia de extremo a extremo
                latencia = time.time() - tiempo_inicio
                print(f"   ✅ [ÉXITO] Transacción registrada de forma consistente en {latencia:.4f}s.")
                
                # ==================================================================
                # REGISTRO DE MÉTRICAS EN CALIENTE EN EL EXPORTADOR
                # ==================================================================
                METRICA_VENTAS_TOTAL.labels(sucursal=sucursal_elegida, estado="exito").inc()
                METRICA_MONTO_TOTAL.labels(sucursal=sucursal_elegida).inc(monto_venta)
                METRICA_LATENCIA_TRANSACCION.labels(sucursal=sucursal_elegida).observe(latencia)

            except Exception as e:
                # En caso de caída de la red, firewall o saturación de base de datos
                latencia = time.time() - tiempo_inicio
                print(f"   ❌ [FALLO DE CONEXIÓN] La sucursal no pudo comunicarse con el host central.")
                print(f"      Detalle del error: {e}")
                
                # Registramos el fallo en telemetría para alertar al operador
                METRICA_VENTAS_TOTAL.labels(sucursal=sucursal_elegida, estado="fallo").inc()
                METRICA_LATENCIA_TRANSACCION.labels(sucursal=sucursal_elegida).observe(latencia)
                
            print("-" * 90)
            # Retraso didáctico para permitir ver pasar los datos dinámicos en Grafana
            time.sleep(1.5)
            
    except KeyboardInterrupt:
        print("\n🛑 Simulación detenida de forma segura por el operador.")

if __name__ == "__main__":
    ejecutar_simulacion_produccion()