# Sistema de Ventas — Guía de instalación y desarrollo

## 1) Pre-requisitos

- **Windows** (recomendado) o Linux con acceso a SQL Server.
- **SQL Server** local o remoto (Express funciona).
- **ODBC Driver for SQL Server** (18 o 17).
- **Python 3.10+** y `pip`.


## 2) Clonar e instalar dependencias

```bash
git clone <URL-DE-TU-REPO>
cd <carpeta-del-repo>

# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Linux/Mac (si usás SQL Server remoto)
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
> Si no usás `requirements.txt`, podés instalar manualmente: `pip install pyodbc reportlab ttkbootstrap`.


## 3) Configurar la conexión (archivo `config.py`)

Editá `config.py` según tu entorno. Ejemplos habituales:

### a) SQL Server local con Windows Authentication (por defecto)
```python
SERVER = r"localhost\SQLEXPRESS"  
DATABASE = "VentasDB"             
TRUSTED = True                    
PASSWORD = ""
```

### b) Servidor central con usuario/clave de SQL
```python
SERVER = r"MI-SERVIDOR\PROD"  
DATABASE = "VentasDB"         
TRUSTED = False               
USER = "ventas_app"
PASSWORD = "********"
```

### c) Una base por desarrollador
```python
DATABASE = "VentasDB_TuNombre"
```


## 4) Ejecutar la aplicación

```bash
python ventas_app.py
```
La primera ejecución:
- Crea la base `VentasDB` (si no existe).
- Crea tablas mínimas: **Productos, Clientes, Ventas, VentaDetalle, Usuarios**.
- Crea un **Admin por defecto**: Usuario **N° 1**, contraseña **admin123** (al iniciar se pide cambiarla).

## 5) Tablas/funciones opcionales

La app detecta y usa automáticamente estas tablas si existen. Para activarlas rápido, ejecutá el script **`schema_opcional.sql`** incluido en este repo:

- `Pagos`: múltiples medios de pago por venta.
- `StockMov`: kardex (INGRESO/VENTA/AJUSTE).
- `IngresosStock`: ingresos de mercadería (con costo y precio).
- `HistorialPrecios`: histórico de costo/precio de productos.
- `CierresCaja`: registros de cierre con totales por período.
- `Auditoria`: log simple de acciones.

