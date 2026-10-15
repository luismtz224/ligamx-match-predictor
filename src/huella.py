"""Huella (hash del contenido) de archivos, para invalidar cachés cuando un archivo cambia.

En Streamlit Cloud un `git push` recarga el código de las páginas pero no vacía `st.cache_resource` ni
`st.cache_data`: una función cacheada que lee un archivo seguía devolviendo el contenido viejo mientras
el HTML ya era el nuevo (HTML nuevo con CSS viejo). La huella se pasa como argumento (normal, no con guion
bajo: esos no entran a la llave) a la función cacheada y, si el archivo cambia, la llave cambia.

Se hashea el contenido y no el `mtime`: el `mtime` depende del checkout. No se memoiza: leer y hashear los
archivos de la app cuesta unos 3 ms por recarga y así siempre es correcto.
"""
import hashlib
from pathlib import Path


def huella(*rutas):
    """Hash corto (16 caracteres hex) del nombre y el contenido de los archivos, en orden.
    Un archivo que no existe cuenta como «ausente» (cambia cuando aparece)."""
    h = hashlib.blake2b(digest_size=8)
    for ruta in rutas:
        p = Path(ruta)
        h.update(p.name.encode("utf-8"))  # el nombre, no la ruta absoluta (cambia entre máquinas)
        try:
            h.update(p.read_bytes())
        except OSError:
            h.update(b"<ausente>")
        h.update(b"\0")
    return h.hexdigest()
