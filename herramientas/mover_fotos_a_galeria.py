"""mover_fotos_a_galeria.py — MUEVE tus fotos a la carpeta que lee el sitio.

PROBLEMA QUE RESUELVE:
    La galería del sitio solo muestra las fotos que viven en  fotos/galeria/.
    Si tus fotos terminadas están en otra parte (por-procesar/, por-procesar/t4/,
    fotos/Legado/, fotos/t9test/, una carpeta "Trimestre 4"...), aquí llegan solas.

QUÉ HACE (en orden):
    1) Crea la carpeta fotos/galeria/ si no existe.
    2) Busca fotos (.jpg .jpeg .png .webp, y también .heic/.tif que convierte a .jpg)
       en estas zonas del proyecto:
          - por-procesar/            (todo su contenido, recursivo: es tu cantera)
          - fotos/<cualquier subcarpeta>  (Legado, t9test, trimestres viejos...)
             * NO toca fotos que ya estén dentro de fotos/galeria/.
        Si tus fotos están en OTRO lado, pásalo como argumento:
            py herramientas/mover_fotos_a_galeria.py "D:\\Fotos\\T4"
    3) Las COPIA primero a fotos/galeria/ (nunca borra nada sin permiso):
        - nombres repetidos -> se agrega _1, _2... detrás.
    4) Te pregunta si quieres BORRAR los originales ya copiados.
       Responde "si" para dejar el proyecto limpio, o enter/"no" para conservarlos.
    5) Regenera assets/js/fotos.js ejecutando actualizar_galeria.py
       (asi la galería del sitio muestra de inmediato las fotos movidas).

USO (consola dentro de la carpeta del proyecto, Windows):
    py herramientas/mover_fotos_a_galeria.py
    py herramientas/mover_fotos_a_galeria.py --solo-ver      (ensayo: no mueve nada)
    py herramientas/mover_fotos_a_galeria.py --borrar-si     (sin preguntas: copia y borra originales)
    py herramientas/mover_fotos_a_galeria.py --no-borrar     (solo copia, conserva todo)
    py herramientas/mover_fotos_a_galeria.py "otra/carpeta/con/fotos"

Después de mover: abre GitHub Desktop, haz Commit to main y Push origin.
"""
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "fotos" / "galeria"
EXT_WEB = (".jpg", ".jpeg", ".png", ".webp")
EXT_EXTRA = (".heic", ".heif", ".tif", ".tiff")   # el navegador no las muestra: se convierten a .jpg
LADO_MAXIMO = 1920


def normalizar(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", str(s).lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def destino_libre(nombre):
    """fotos/galeria/<nombre>; si ya existe, agrega _1, _2... detrás."""
    destino = DESTINO / nombre
    if not destino.exists():
        return destino
    p = Path(nombre)
    i = 1
    while True:
        candidato = DESTINO / f"{p.stem}_{i}{p.suffix}"
        if not candidato.exists():
            return candidato
        i += 1


def convertir_a_jpg(origen, destino):
    """Revela/redimensiona HEIC/TIFF y lo guarda como JPG. True si lo logró."""
    try:
        from PIL import Image, ImageOps
    except ImportError:
        print(f"  AVISO: {origen.name} necesita Pillow para convertirse a JPG (py -m pip install Pillow). Se copia igual.")
        return False
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
    except Exception:
        pass
    try:
        with Image.open(origen) as im:
            im = ImageOps.exif_transpose(im)
            if max(im.size) > LADO_MAXIMO:
                im.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
            if im.mode in ("RGBA", "P", "LA"):
                im = im.convert("RGB")
            im.save(destino, "JPEG", quality=85)
        return True
    except Exception as e:
        print(f"  AVISO: no pude convertir {origen.name} ({e}). Se copia tal cual.")
        return False


def recolectar(carpetas_extra):
    """Lista de archivos-foto candidatos, con etiqueta de dónde están."""
    encontrados = []

    def add(p, origen):
        if p.is_file() and p.suffix.lower() in (EXT_WEB + EXT_EXTRA):
            encontrados.append((p, origen))

    # 1) por-procesar/ (recursivo) — la cantera de fotos terminadas
    pp = RAIZ / "por-procesar"
    if pp.is_dir():
        for p in sorted(pp.rglob("*")):
            add(p, "por-procesar")

    # 2) cualquier subcarpeta de fotos/ que NO sea galeria (Legado, t9test, trimestres...)
    fdir = RAIZ / "fotos"
    if fdir.is_dir():
        for sub in sorted(fdir.iterdir()):
            if not sub.is_dir():
                continue
            if normalizar(sub.name) == "galeria":
                continue
            for p in sorted(sub.rglob("*")):
                add(p, f"fotos/{sub.name}")

    # 3) carpetas pasadas por argumento
    for extra in carpetas_extra:
        e = Path(extra)
        if not e.is_absolute():
            e = (RAIZ / e).resolve()
        if e.is_dir():
            for p in sorted(e.rglob("*")):
                add(p, str(e))
        else:
            print(f"AVISO: la carpeta '{extra}' no existe; la ignoro.")

    # evitar duplicados del mismo archivo (por si un argumento apunta a una zona ya barrida)
    vistos, unicos = set(), []
    for p, origen in encontrados:
        r = p.resolve()
        if r in vistos:
            continue
        vistos.add(r)
        unicos.append((p, origen))
    return unicos


def preguntar(msg):
    try:
        resp = input(msg).strip().lower()
    except EOFError:      # consola sin entrada interactiva: no borrar nada
        return False
    return resp in ("s", "si", "sí", "y", "yes")


def main():
    args = [a for a in sys.argv[1:] if a not in ("--solo-ver", "--borrar-si", "--no-borrar")]
    ensayo = "--solo-ver" in sys.argv
    auto_borrar = "--borrar-si" in sys.argv
    no_borrar = "--no-borrar" in sys.argv

    print("=== mover_fotos_a_galeria.py ===")
    print(f"Destino: {DESTINO}")

    candidatos = recolectar(args)
    if not candidatos:
        print("No encontré fotos por mover (ni en por-procesar/, ni en subcarpetas de fotos/, ni en las rutas que pasaste).")
        print("Si tus fotos están en otra carpeta, ejecuta:  py herramientas/mover_fotos_a_galeria.py \"RUTA\\DE\\TUS\\FOTOS\"")
        return 0

    print(f"Fotos candidatas: {len(candidatos)}")
    DESTINO.mkdir(parents=True, exist_ok=True)

    copiadas, saltadas, avisos = [], [], []
    for p, origen in candidatos:
        try:
            p.relative_to(DESTINO)
            saltadas.append(p)      # ya está en fotos/galeria/: nada que hacer
            continue
        except ValueError:
            pass
        nombre = p.name
        if p.suffix.lower() in EXT_EXTRA:
            nombre = Path(nombre).stem + ".jpg"
        destino = destino_libre(nombre)
        if ensayo:
            print(f"[ensayo] {origen}/{p.name} -> fotos/galeria/{destino.name}")
            copiadas.append((p, destino))
            continue
        try:
            if destino.suffix.lower() == ".jpg" and p.suffix.lower() in EXT_EXTRA:
                if convertir_a_jpg(p, destino):
                    copiadas.append((p, destino))
                    print(f"+ {origen}/{p.name} -> fotos/galeria/{destino.name} (convertida a JPG)")
                    continue
            shutil.copy2(str(p), str(destino))
            copiadas.append((p, destino))
            print(f"+ {origen}/{p.name} -> fotos/galeria/{destino.name}")
        except OSError as e:
            avisos.append(f"No pude copiar {p}: {e}")

    for a in avisos:
        print("AVISO: " + a)
    if saltadas:
        print(f"({len(saltadas)} fotos ya estaban en fotos/galeria/, no las toqué)")
    if ensayo:
        print("\nENSAYO: no moví ni borré nada. Ejecuta sin --solo-ver para aplicar.")
        return 0
    if not copiadas:
        print("No había fotos nuevas que copiar.")

    # --- ¿borrar los originales ya copiados? ---
    a_borrar = [p for p, _ in copiadas if not (RAIZ / "por-procesar").resolve() in p.resolve().parents and p.parent != RAIZ / "por-procesar"]
    # nota: los archivos DIRECTOS de por-procesar/ conviene conservarlos hasta subir;
    # los de subcarpetas jubiladas (fotos/Legado, fotos/t9test...) sí se pueden quitar.
    fuera_de_fotos = [p for p in a_borrar if normalizar(p.parent.name) != "galeria" and "fotos" not in [normalizar(x) for x in p.relative_to(RAIZ).parts[:-1]]]
    originals_en_fotos = [p for p, _ in copiadas if "fotos" in [normalizar(x) for x in p.relative_to(RAIZ).parts[:-1]] and normalizar(p.parent.name) != "galeria"]

    quiero_borrar = []
    if not no_borrar and copiadas:
        if auto_borrar:
            quiero_borrar = originals_en_fotos
        elif originals_en_fotos:
            print(f"\n{len(originals_en_fotos)} fotos fueron COPIADAS desde subcarpetas viejas de fotos/ "
                  f"(Legado, t9test, etc.). ¿Quieres borrar esos originales ahora que están en fotos/galeria/?")
            if preguntar("Borrar originales (si/no, por defecto no): "):
                quiero_borrar = originals_en_fotos
        if fuera_de_fotos and not quiero_borrar and not auto_borrar:
            print("(Los archivos de por-procesar/ se conservan: ahí vives tus RAW y el pedido .ps1 los necesita.)")

    for p in quiero_borrar:
        try:
            p.unlink()
            print(f"- Borrado original: {p.relative_to(RAIZ)}")
        except OSError as e:
            print(f"AVISO: no pude borrar {p}: {e}")
    # carpetas jubiladas que quedaron vacías
    for sub in sorted((RAIZ / "fotos").iterdir()) if (RAIZ / "fotos").is_dir() else []:
        if sub.is_dir() and normalizar(sub.name) != "galeria" and not any(sub.rglob("*")):
            try:
                sub.rmdir()
                print(f"- Carpeta vacía eliminada: fotos/{sub.name}")
            except OSError:
                pass

    # --- regenerar fotos.js para que el sitio muestre las fotos nuevas ---
    print("\nRegenerando assets/js/fotos.js ...")
    r = subprocess.run([sys.executable, str(RAIZ / "herramientas" / "actualizar_galeria.py")], cwd=RAIZ)
    if r.returncode != 0:
        print("AVISO: actualizar_galeria.py falló; revisa lo anterior.")
    print(f"\nListo: {len(copiadas)} foto(s) en fotos/galeria/.")
    print("Ahora: GitHub Desktop -> Commit to main -> Push origin.")
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
