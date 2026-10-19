# Metodo Simplex

Aplicacion de escritorio que resuelve problemas de programacion lineal con el metodo Simplex y explica cada paso. Pensada como herramienta de estudio: ademas de la solucion optima muestra las tablas intermedias, el razonamiento de cada iteracion y un glosario de terminos.

## Caracteristicas

- Resolucion de problemas de maximizacion y minimizacion con restricciones.
- Soporte del metodo de la Gran M para restricciones de tipo mayor o igual e igualdad.
- Interfaz grafica de escritorio (Tkinter) para capturar el problema y ver los resultados.
- Explicaciones paso a paso y graficas de apoyo (matplotlib).
- Generacion de un documento PDF explicativo del metodo (en `docs/`).
- Pruebas automatizadas del nucleo de calculo.

## Estructura

- `simplex/` - nucleo de calculo: modelo del problema, metodo de la Gran M y validaciones.
- `gui/` - interfaz grafica: formulario del problema, vista de resultados y estado.
- `explain/` - generacion de explicaciones paso a paso y glosario.
- `viz/` - graficas.
- `docs/` - generador y PDF explicativo del metodo.
- `tests/` - pruebas del nucleo (`test_simplex.py`).
- `main.py` - punto de entrada que lanza la interfaz grafica.

## Requisitos

- Python 3.11 o superior. Tkinter viene incluido en la instalacion estandar de Python.

## Puesta en marcha

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux o macOS

pip install -r requirements.txt
python main.py
```

## Pruebas

Las pruebas estan escritas para pytest:

```bash
pip install pytest
python -m pytest
```
