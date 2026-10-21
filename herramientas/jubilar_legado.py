"""Pasa la sección "Legado" de la galería a "por procesar" (la quita del sitio), SIN mover fotos.

Qué hace exactamente (solo toca archivos de texto, no mueve ni copia ninguna foto):
  1. Quita la línea "Legado | ..." de fotos/trimestres.txt  -> Legado deja de aparecer en la galería.
  2. Comenta las líneas de Legado en fotos/fechas.txt y fotos/etiquetas.txt (si las hay),
     para que no estorben. Los datos quedan guardados por si algún día los quieres de vuelta.
  3. Regenera assets/js/fotos.js ejecutando actualizar_galeria.py -> el sitio queda sin Legado.

NO borra nada: la carpeta fotos/Legado y sus webp se quedan tal cual en tu PC.
Cuando quieras pasarlAs físicamente a por-procesar/legado/, usa migrar_legado.py (ese sí copia).

Uso (consola dentro de la carpeta del proyecto):
    py herramientas/jubilar_legado.py          -> aplica los cambios
    py herramientas/jubilar_legado.py --revertir -> devuelve Legado a la galería (deshace el paso 1 y 2)
Para revertir también el paso 3: vuelve a ejecutar preparar_y_actualizar.bat después de --revertir.
"""
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TRIM = RAIZ / "fotos" / "trimestres.txt"
OTRAS = [RAIZ / "fotos" / "fechas.txt", RAIZ / "fotos" / "etiquetas.txt"]
CLAVE = "legado"   # comparamos en minúsculas: sirve tanto "Legado" como "legado"


def jubilar():
    cambiados = []

    # 1) trimestres.txt: comentar la(s) línea(s) cuya carpeta sea Legado
    lineas = TRIM.read_text(encoding="utf-8").splitlines()
    nueva = []
    for ln in lineas:
        partes = [x.strip() for x in ln.split("|")]
        if partes and partes[0].lower() == CLAVE and not ln.strip().startswith("#"):
            nueva.append("# JUBILADO (antes en la galería): " + ln)
            cambiados.append("trimestres.txt: se quitó Legado de la galería")
        else:
            nueva.append(ln)
    if len(nueva) != len(lineas) or any("JUBILADO" in l for l in nueva if l not in lineas):
        TRIM.write_text("\n".join(nueva) + "\n", encoding="utf-8")

    # 2) fechas.txt / etiquetas.txt: comentar las reglas que empiezan por legado (formato 3 partes)
    for ruta in OTRAS:
        if not ruta.exists():
            continue
        ls, tocado = ruta.read_text(encoding="utf-8").splitlines(), False
        out = []
        for ln in ls:
            partes = [x.strip() for x in ln.split("|")]
            if len(partes) == 3 and partes[0].lower() == CLAVE and not ln.strip().startswith("#"):
                out.append("# JUBILADO: " + ln); tocado = True
            else:
                out.append(ln)
        if tocado:
            ruta.write_text("\n".join(out) + "\n", encoding="utf-8")
            cambiados.append(f"{ruta.name}: reglas de legado comentadas")

    # 3) regenerar fotos.js
    r = subprocess.run([sys.executable, str(RAIZ / "herramientas" / "actualizar_galeria.py")], cwd=RAIZ)
    if r.returncode != 0:
        print("AVISO: actualizar_galeria.py falló; revisa lo anterior e inténtalo otra vez.")
        return r.returncode

    if cambiados:
        for c in cambiados:
            print("+ " + c)
        print('Listo: "Legado" ya no aparece en la galería (las fotos siguen en fotos/Legado, intactas).')
        print("Sube los cambios con GitHub Desktop cuando quieras publicarlos.")
    else:
        print('No encontré a "Legado" activo en fotos/trimestres.txt: probablemente ya está jubilado.')
    return 0


def revertir():
    """Descomenta las líneas marcadas como JUBILADO relacionadas con legado."""
    recuperadas = 0
    for ruta in [TRIM] + OTRAS:
        if not ruta.exists():
            continue
        ls = ruta.read_text(encoding="utf-8").splitlines()
        out = []
        for ln in ls:
            s = ln.strip()
            if s.startswith("# JUBILADO") and "|" in s:
                cuerpo = s.split(": ", 1)[1] if ": " in s else ""
                partes = [x.strip() for x in cuerpo.split("|")]
                if partes and partes[0].lower() == CLAVE:
                    out.append(cuerpo); recuperadas += 1
                    continue
            out.append(ln)
        ruta.write_text("\n".join(out) + "\n", encoding="utf-8")
    if recuperadas:
        print(f"+ Se devolvieron {recuperadas} línea(s) de legado.")
        print("Ejecuta ahora preparar_y_actualizar.bat para regenerar la galería con Legado.")
    else:
        print("No había nada jubilado que devolver.")
    return 0


if __name__ == "__main__":
    raise SystemExit(revertir() if "--revertir" in sys.argv else jubilar())
