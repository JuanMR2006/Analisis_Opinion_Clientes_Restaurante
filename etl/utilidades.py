"""Utilidades compartidas por los dos pipelines: bitácora de reglas, cuarentena y helpers de limpieza."""
import hashlib
import json
import shutil
from datetime import datetime

import pandas as pd

import config


class Bitacora:
    """Registro de cada regla aplicada (código, dimensión, filas afectadas).
    Se convierte en reporte_calidad.md y metricas_etl.json: nada se pierde en silencio."""

    def __init__(self):
        self.pasos = []
        self.metricas = {}
        self.decisiones = []

    def registrar(self, fuente, codigo, dimension, regla, accion, filas):
        filas = int(filas)
        self.pasos.append({"fuente": fuente, "codigo": codigo, "dimension": dimension, "regla": regla,
                           "accion": accion, "filas": filas})
        print(f"  [{codigo}] {regla}: {filas:,}")

    def metrica(self, clave, valor):
        self.metricas[clave] = valor

    def decision(self, fuente, texto):
        self.decisiones.append({"fuente": fuente, "texto": texto})


class Cuarentena:
    """Guarda las filas rechazadas con sus valores ORIGINALES (texto crudo) y el Motivo."""

    def __init__(self):
        self.partes = {}

    def rechazar(self, df, mascara, crudo, fuente, codigo, regla, dimension, bit):
        """Quita de df las filas donde mascara es True y las envía a cuarentena.
        `crudo` es el DataFrame original (mismo índice) para guardar el dato tal como venía."""
        mascara = mascara.fillna(False).astype(bool)   # un NaN en la condición no debe hacer desaparecer filas
        n = int(mascara.sum())
        bit.registrar(fuente, codigo, dimension, regla, "Eliminar (cuarentena)", n)
        if n:
            malos = crudo.loc[df.index[mascara]].copy()
            malos["Codigo_Regla"] = codigo
            malos["Motivo"] = regla
            self.partes.setdefault(fuente, []).append(malos)
        return df.loc[~mascara]

    def total(self, fuente):
        return sum(len(p) for p in self.partes.get(fuente, []))

    def guardar(self, fuentes):
        """Carga idempotente: borra la carpeta y la regenera. Siempre se escribe un archivo por fuente
        (aunque esté vacío) para que la validación pueda comprobar el balance."""
        if config.CUARENTENA.exists():
            shutil.rmtree(config.CUARENTENA)
        config.CUARENTENA.mkdir(parents=True)
        for fuente, columnas in fuentes.items():
            partes = self.partes.get(fuente)
            df = pd.concat(partes) if partes else pd.DataFrame(columns=columnas + ["Codigo_Regla", "Motivo"])
            ruta = config.CUARENTENA / f"{fuente.lower()}_rechazados.csv"
            df.to_csv(ruta, index=False, encoding="utf-8-sig")
            print(f"  rechazados/{ruta.name} -> {len(df):,} filas")


def exigir_columnas(df, esperadas, fuente):
    """Contrato de esquema: si el archivo no trae las columnas esperadas, se detiene todo."""
    faltan = [c for c in esperadas if c not in df.columns]
    if faltan:
        raise ValueError(f"[{fuente}] el archivo no cumple el contrato, faltan columnas: {faltan}")
    sobran = [c for c in df.columns if c not in esperadas]
    if sobran:
        print(f"  AVISO [{fuente}] columnas no esperadas (se ignoran): {sobran}")


def leer_csv_texto(ruta):
    """Extract: todo como texto (dtype=str) y sin convertir nada a NaN automáticamente,
    para que cada conversión sea explícita y auditable. Falla si el archivo no es UTF-8."""
    if not ruta.exists():
        raise FileNotFoundError(f"No existe {ruta}")
    return pd.read_csv(ruta, dtype=str, keep_default_na=False, encoding="utf-8")


def a_nulo(serie, texto_libre=False):
    """Normaliza: trim y marcas de 'sin dato' -> NA. En texto libre solo el vacío es nulo."""
    limpio = serie.astype("string").str.strip()
    if texto_libre:
        return limpio.mask(limpio == "")
    return limpio.mask(limpio.str.lower().isin(config.TEXTOS_NULOS))


def a_numero(serie):
    return pd.to_numeric(serie, errors="coerce")


def no_es_numero(texto, numero):
    """Hay texto pero no convirtió a número."""
    return texto.notna() & numero.isna()


def no_es_entero(numero):
    return numero.notna() & (numero % 1 != 0)


def fuera_de(numero, rango):
    return numero.notna() & ((numero < rango[0]) | (numero > rango[1]))


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def escribir_manifiesto(archivos):
    """Huella de cada crudo (tamaño + SHA-256): si la fuente cambia, la huella cambia (trazabilidad).
    Se guarda APARTE de los CSV, que no se tocan."""
    datos = {"generado": datetime.now().isoformat(timespec="seconds"), "archivos": []}
    for ruta in archivos:
        datos["archivos"].append({"archivo": ruta.name, "bytes": ruta.stat().st_size, "sha256": sha256(ruta)})
    config.MANIFIESTO.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")
    return datos


def guardar_tabla(df, nombre):
    """Load: CSV utf-8-sig (Excel/Power BI leen bien tildes) + Parquet (tipos exactos)."""
    df.to_csv(config.LIMPIOS / f"{nombre}.csv", index=False, encoding="utf-8-sig")
    df.to_parquet(config.LIMPIOS / "parquet" / f"{nombre}.parquet", index=False)
    print(f"  {nombre:28s} {len(df):>8,} filas  {len(df.columns):>2} columnas")
    return len(df)


def perfil_nulos(df, columnas, fuente, codigo, bit):
    """Evalúa % de nulos por columna. Las que pasan del umbral se registran para decidir (no se borran solas)."""
    altas = {}
    for c in columnas:
        pct = float(df[c].isna().mean())
        if pct > config.MAX_NULOS_COLUMNA:
            altas[c] = round(pct, 4)
    bit.registrar(fuente, codigo, "Completitud", f"Columnas con > {config.MAX_NULOS_COLUMNA:.0%} de nulos "
                  f"(se evalúan, no se borran){': ' + str(altas) if altas else ''}", "Evaluar", len(altas))
    return altas
