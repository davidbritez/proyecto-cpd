# 📊 Sistema de Facturación Transaccional Distribuido (Simulación de CPD)

Este proyecto consiste en el diseño, virtualización y gestión de un entorno simulado de **Centro de Procesamiento de Datos (CPD)** de misión crítica para la asignatura *Procesamiento de Datos* de la **UCOM**.

## 🚀 Propósito del Proyecto
El objetivo principal es resolver un desafío clásico de consistencia de datos en sistemas distribuidos: garantizar la generación de un **número de factura autoincremental único** en tiempo real para tres sucursales comerciales remotas (Sucursales A, B y C), evitando colisiones de datos y duplicados cuando se realizan ventas concurrentes en un nodo central de persistencia.

---

## 🏗️ Arquitectura del CPD Virtualizado

El sistema se compone de las siguientes capas lógicas ejecutadas sobre un único host mediante virtualización ligera:

1. **Infraestructura Base:** Ejecución sobre **WSL 2 (Ubuntu Linux)** integrado de forma nativa con **Docker**.
2. **Red de CPD (LAN Corporativa):** Una red virtual aislada de tipo bridge denominada `red_empresarial` que conecta a todos los servidores.
3. **Persistencia Transaccional (Nodo Matriz):** Un contenedor con el motor de base de datos **PostgreSQL** configurado con volúmenes persistentes montados en el disco del host y lógica de bloqueo mediante el tipo de datos `SERIAL`.
4. **Seguridad y Hardening:** Segmentación lógica y endurecimiento de accesos mediante el archivo de control `pg_hba.conf` para filtrar peticiones únicamente desde el clúster.
5. **Alta Disponibilidad (HA):** Un balanceador de carga de red (**Nginx / HA-Proxy**) que enruta el tráfico de ventas.
6. **Telemetría y Monitorización:** Un stack de monitorización en tiempo real compuesto por **Prometheus** (recolector de métricas de hardware de los contenedores) y **Grafana** (cuadro de mando visual para el análisis de estrés bajo ráfagas de transacciones concurrentes).

---

## 🛠️ Herramientas Utilizadas (Stack Tecnológico)
* **Sistema Operativo:** Ubuntu Linux (vía WSL 2)
* **Motor de Contenedores:** Docker Desktop
* **Base de Datos:** PostgreSQL
* **Balanceador de Carga:** Nginx / HA-Proxy
* **Observabilidad:** Prometheus + Grafana Open Source
* **Control de Versiones:** Git + GitHub