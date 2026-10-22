"""Reporte funcional por defecto; --escalable conserva los conteos en disco."""
import sys

if __name__ == "__main__":
    if "--escalable" in sys.argv:
        sys.argv.remove("--escalable")
        from mensajeria.reporte import main
    else:
        from mensajeria.analisis.reporte import main
    main()
