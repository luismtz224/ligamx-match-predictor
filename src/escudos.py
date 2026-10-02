"""Versiones ligeras de los escudos. `python -m src.escudos` las regenera desde
assets/escudos_originales/ (no se sube al repo) en assets/escudos/256 y assets/escudos/512."""
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
DIR_ORIGINALES = RAIZ / "assets" / "escudos_originales"
DIR_ESCUDOS = RAIZ / "assets" / "escudos"
LADOS = (256, 512)


def cuadrado(img, lado):
    """Recorta el margen transparente y centra el escudo en un lienzo RGBA de lado x lado."""
    img = img.convert("RGBA")
    caja = img.getchannel("A").getbbox()
    if caja:
        img = img.crop(caja)
    escala = lado / max(img.size)
    nuevo = (max(1, round(img.width * escala)), max(1, round(img.height * escala)))
    img = img.resize(nuevo, Image.Resampling.LANCZOS)
    lienzo = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    lienzo.paste(img, ((lado - img.width) // 2, (lado - img.height) // 2), img)
    return lienzo


def main():
    for lado in LADOS:
        destino = DIR_ESCUDOS / str(lado)
        destino.mkdir(parents=True, exist_ok=True)
        for ruta in sorted(DIR_ORIGINALES.glob("*.png")):
            cuadrado(Image.open(ruta), lado).save(destino / ruta.name, optimize=True)
        total = sum(p.stat().st_size for p in destino.glob("*.png"))
        print(f"{lado} px: {total / 1024:.0f} KB en {destino}")


if __name__ == "__main__":
    main()
