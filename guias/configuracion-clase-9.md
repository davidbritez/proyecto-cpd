# Guía de Laboratorio Práctico: Gobernanza de Recursos, Abstracción de Configuración y Balanceo de Carga (Clase 9)
## Cátedra: Procesamiento de Datos — UCOM
### Docente: Ing. David Britez

Este manual contiene el paso a paso detallado y el código completo para avanzar con la **Fase 4 del Proyecto Integrador** en tu entorno de **GitHub Codespaces**. 

Aprenderemos a optimizar el Centro de Procesamiento de Datos (CPD) corporativo aplicando tres pilares fundamentales de la ingeniería de sistemas modernos:
1. **Gobernanza Física (cgroups v2):** Restringir el uso de CPU y memoria RAM de los servidores de base de datos para evitar que un proceso defectuoso sature el nodo anfitrión.
2. **Abstracción de Configuración (.env & Secrets):** Desacoplar el código de los parámetros lógicos de conexión y proteger de forma criptográfica la contraseña en memoria volátil (`tmpfs`).
3. **Balanceo de Carga TCP (HA-Proxy en Capa 4):** Desplegar un contenedor de borde de red empresarial para canalizar y distribuir de forma transparente el tráfico transaccional hacia nuestras bases de datos distribuidas.

---

## 🛠️ PASO 1: GOBERNANZA FÍSICA CON CGROUPS V2

En sistemas de producción reales, si un contenedor de una sucursal experimenta un bucle infinito en Python o una fuga de memoria, consumirá todo el silicio (CPU y RAM) del Host de la Casa Matriz, provocando una caída total del CPD. Para evitar esto, limitaremos el hardware físico utilizando la API de **cgroups v2** integrada en Docker Compose.

### Modificación de `compose.yaml`
Abre tu archivo `compose.yaml` en **VS Code** y añade la directiva `deploy.resources` en cada uno de tus servicios de base de datos. El archivo debe quedar estructurado de la siguiente forma (mostrando la Casa Matriz y la Sucursal A como referencia):

```yaml
version: '3.8'

services:
  # ==========================================================
  # NODO MATRIZ (ASUNCIÓN)
  # ==========================================================
  postgres-matriz:
    image: postgres:15-alpine
    container_name: cpd-matriz-db
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: matriz_db
      POSTGRES_USER: ucom_admin
      POSTGRES_PASSWORD: password_matriz
    networks:
      - red_empresarial
    volumes:
      - datos_matriz:/var/lib/postgresql/data
    # ==========================================================
    # LIMITACIÓN FÍSICA CGROUPS V2 (Novedad Clase 9)
    # ==========================================================
    deploy:
      resources:
        limits:
          cpus: '0.50'        # El contenedor usará como máximo el 50% de un núcleo de CPU
          memory: 512M        # Evita que el servicio consuma más de 512 Megabytes de RAM
        reservations:
          memory: 256M        # Reserva garantizada de 256 MB de RAM física para este motor

  # ==========================================================
  # NODO SUCURSAL A (CIUDAD DEL ESTE)
  # ==========================================================
  postgres-sucursal-a:
    image: postgres:15-alpine
    container_name: cpd-sucursala-db
    ports:
      - "5433:5432"
    environment:
      POSTGRES_DB: sucursal_a_db
      POSTGRES_USER: ucom_admin
      POSTGRES_PASSWORD: password_sucursal_a
    networks:
      - red_empresarial
    volumes:
      - datos_sucursal_a:/var/lib/postgresql/data
    # ==========================================================
    # LIMITACIÓN FÍSICA CGROUPS V2 (Novedad Clase 9)
    # ==========================================================
    deploy:
      resources:
        limits:
          cpus: '0.25'        # Las sucursales se limitan a un 25% de un núcleo de CPU
          memory: 256M        # Límite máximo de 256 MB de RAM
        reservations:
          memory: 128M        # Garantía mínima de 128 MB de RAM

  # (Repetir la sección 'deploy' idéntica en 'postgres-sucursal-b' y 'postgres-sucursal-c' para gobernarlos de la misma manera)

networks:
  red_empresarial:
    driver: bridge

volumes:
  datos_matriz:
  datos_sucursal_a:
  datos_sucursal_b:
  datos_sucursal_c:
```

---

## 📁 PASO 2: ABSTRACCIÓN DE CONFIGURACIÓN (.ENV / CONFIGMAP)

El script `importar_ventas_v3.py` de la Clase 6 tenía los datos de la base de datos (IP, puerto, base de datos) hardcodeados en su código. Siguiendo el principio de diseño de la "Twelve-Factor App" (Separación estricta de código y configuración), crearemos un archivo de entorno externo que actuará como nuestro ConfigMap local.

### 1. Crear el archivo `.env` en la raíz del proyecto
Crea un nuevo archivo en tu explorador de VS Code llamado exactamente `.env` y define los parámetros lógicos de conexión:

```text
# .env (Configuración abstracta del clúster del CPD)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=matriz_db
DB_USER=ucom_admin
```

### 2. Refactorizar el script de Python (`importar_ventas_v3.py`)
Abre tu script en el editor y modifícalo para que consuma de forma dinámica las variables de entorno utilizando la librería `os` de Python:

```python
# importar_ventas_v3.py
# Refactorizado de forma abstracta para la Clase 9
import os
import time
import random
import pandas as pd
import psycopg2

# Configuración única recuperada de las variables del sistema (.env)
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "matriz_db"),
    "user": os.getenv("DB_USER", "ucom_admin"),
    "password": os.getenv("DB_PASSWORD", "password_matriz")  # Se inyectará por separado
}

SUCURSALES_DISPLAY = {
    "Sucursal_Asuncion": {"color": "\033[93m"},
    "Sucursal_CDE": {"color": "\033[96m"},
    "Sucursal_ENC": {"color": "\033[92m"},
    "Sucursal_COV": {"color": "\033[94m"}
}
RESET_COLOR = "\033[0m"

def ejecutar_simulacion_centralizada(ruta_csv):
    print("🚀 INICIANDO SIMULACIÓN DE CONEXIÓN REMOTA ABSTRACTA (CLASE 9)...")
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
```

---

## 🔐 PASO 3: PROTECCIÓN DE CREDENCIALES CON SECRETS

Las contraseñas de las bases de datos no deben ser expuestas en variables de entorno normales que cualquiera puede ver corriendo un comando `env`. Docker permite usar `secrets`, inyectando el dato sensible a través de un archivo temporal de memoria RAM volátil (`tmpfs`) dentro de la ruta `/run/secrets/`.

### 1. Crear el archivo físico de clave local
Crea un archivo llamado `db_password.txt` en la raíz de tu Codespace con el siguiente texto sin espacios:
```text
password_matriz
```

### 2. Actualizar el archivo `.gitignore`
Para asegurarnos de que la contraseña física nunca se suba a tu repositorio público de GitHub, edita tu archivo `.gitignore` añadiendo la referencia:
```text
almacenamiento/
db_password.txt
```

### 3. Integrar Secrets en `compose.yaml`
Modifica la definición del servicio `postgres-matriz` en tu `compose.yaml` para indicarle que consuma de forma cifrada el secreto y que inicialice el motor leyéndolo desde el sistema de archivos volátil:

```yaml
services:
  postgres-matriz:
    image: postgres:15-alpine
    container_name: cpd-matriz-db
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: matriz_db
      POSTGRES_USER: ucom_admin
      # Indicamos a Postgres que busque la clave de inicio en el archivo del Secret
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    secrets:
      - db_password
    networks:
      - red_empresarial
    volumes:
      - matriz_data:/var/lib/postgresql/data

# Definimos los secretos que Docker Compose cargará al iniciar el contenedor
secrets:
  db_password:
    file: ./db_password.txt
```

---

## 🌐 PASO 4: DESPLIEGUE DEL BALANCEADOR DE CARGA TCP (HA-PROXY)

En un CPD real, los clientes remotos no conocen las IPs directas de tus servidores internos. Se sitúa un Balanceador de Carga de Capa 4 en el borde perimetral que recibe todas las conexiones entrantes (Puerto Front-End) y las enruta inteligentemente hacia las bases de datos activas en el back-end (utilizando el DNS lógico interno de Docker Compose).

### 1. Crear el archivo de configuración `haproxy.cfg`
Crea una nueva carpeta llamada `balanceador` en la raíz de tu proyecto, y dentro de ella crea un archivo de configuración de texto llamado `haproxy.cfg`:

```text
# haproxy.cfg
# Configuración del Balanceador de Carga TCP (Capa 4) para el CPD de la UCOM

global
    log stdout format raw local0

defaults
    log     global
    mode    tcp                # Operamos en Capa 4 (Sockets TCP puros para bases de datos)
    timeout connect 5s
    timeout client  30s
    timeout server  30s

# Front-End: Puerto perimetral expuesto por el que ingresa el tráfico
frontend db_gateway
    bind *:5432                # Escucha peticiones TCP en el puerto 5432 del balanceador
    default_backend db_cluster

# Back-End: Lista de servidores internos del CPD a los que se redirige el tráfico
backend db_cluster
    mode tcp
    balance roundrobin         # Algoritmo de distribución de carga por turnos lógicos
    option pgsql-check user ucom_admin  # Auditador de salud nativo de Postgres
    server nodo_central postgres-matriz:5432 check
```

### 2. Añadir el servicio `cpd-balanceador` a `compose.yaml`
Abre tu `compose.yaml` y agrega el balanceador como el quinto contenedor de tu infraestructura, mapeando el puerto expuesto del host (`5432`) **únicamente hacia el balanceador** y removiendo el puerto expuesto del contenedor original `postgres-matriz` (para que la base de datos quede totalmente blindada dentro de la red privada):

```yaml
services:
  # Base de datos central (Blindada internamente, sin mapeo de puertos hacia el host)
  postgres-matriz:
    image: postgres:15-alpine
    container_name: cpd-matriz-db
    environment:
      POSTGRES_DB: matriz_db
      POSTGRES_USER: ucom_admin
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    secrets:
      - db_password
    networks:
      - red_empresarial
    volumes:
      - matriz_data:/var/lib/postgresql/data

  # Balanceador de Carga (Único nodo expuesto al puerto del Host de Codespaces)
  cpd-balanceador:
    image: haproxy:2.8-alpine
    container_name: cpd-balanceador
    ports:
      - "5432:5432"            # Mapeamos el puerto 5432 del host al HA-Proxy
    networks:
      - red_empresarial
    volumes:
      - ./balanceador/haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro
    depends_on:
      - postgres-matriz
```

---

## 🧪 PASO 5: FLUJO DE EJECUCIÓN Y PRUEBAS EN CODESPACES

Ejecuta esta secuencia completa de terminal para desplegar la infraestructura inteligente en caliente y validar el balanceo de carga:

```bash
# 1. Apagar cualquier clúster antiguo de forma segura
docker compose down

# 2. Levantar la nueva infraestructura optimizada (Cgroups, Secrets y Balanceador)
docker compose up -d

# 3. Validar que los 5 contenedores estén corriendo de forma estable
docker compose ps
```

**Resultado esperado del listado de contenedores:**
```text
NAME                IMAGE               COMMAND                  SERVICE             CREATED             STATUS              PORTS
cpd-balanceador     haproxy:2.8-alpine  "/docker-entrypoint.…"   cpd-balanceador     10 seconds ago      Up 9 seconds        0.0.0.0:5432->5432/tcp
cpd-matriz-db       postgres:15-alpine  "docker-entrypoint.s…"   postgres-matriz     10 seconds ago      Up 9 seconds        5432/tcp
cpd-sucursala-db    postgres:15-alpine  "docker-entrypoint.s…"   cpd-sucursala-db    10 seconds ago      Up 9 seconds        0.0.0.0:5433->5432/tcp
...
```
*(Nota que el puerto 5432 del host ya no apunta directamente a `postgres-matriz`, sino que está tomado por el `cpd-balanceador` de forma segura)*.

### 4. Inicializar la Base de Datos a través del Balanceador
Inyecta el esquema de la tabla de ventas locales enviando el archivo DDL. La petición pasará de forma transparente a través de la tubería del HA-Proxy hacia la Matriz:
```bash
docker exec -i cpd-matriz-db psql -U ucom_admin -d matriz_db < ddl-v3.sql
```

### 5. Correr el Script de Simulación con Configuración Abstracta
Ejecuta la simulación transaccional:
```bash
python3 importar_ventas_v3.py
```
*El script leerá dinámicamente el archivo `.env`, se conectará a `localhost:5432` (que ahora es el puerto del HA-Proxy), pasará de forma segura el canal TCP, y asentará las 9 facturas de forma consistente y exitosa en Asunción.*

### 6. Guardar los cambios del Hito de la Clase 9 en GitHub
Sube tu código limpio a tu repositorio público de GitHub:
```bash
git add .
git commit -m "Fase 4 - Implementación de Cgroups, Secrets, Variables de Entorno y Balanceador de Carga TCP"
git push origin main
```
