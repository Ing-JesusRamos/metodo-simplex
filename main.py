"""Punto de entrada: lanza la interfaz gráfica del método simplex."""

import sys


def main() -> None:
    try:
        from gui.app import SimplexApp
    except ImportError as error:
        print(f"No se pudo iniciar la aplicación: {error}")
        print("Instala las dependencias con:  pip install -r requirements.txt")
        sys.exit(1)
    app = SimplexApp()
    app.mainloop()


if __name__ == "__main__":
    main()