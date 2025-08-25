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

EJECUTA gen_admin.py por primera y unica vez
luego copia y pega el contenido de schema.sql en una query en SSMS 
ejecuta ventas_app.py e ingresa con el admin 1, contraseña 1. 