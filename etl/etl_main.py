"""Orquestador del ETL: ejecuta los DOS pipelines independientes (sin join entre ellos) y escribe reportes.

    datasets/ --(Extract: pandas, todo texto)--> reglas E01.. / R01.. --(Load)--> datos_limpios/ (CSV + parquet)
                                                         +--> rechazados/ (cuarentena con Motivo)

Uso:   python etl/etl_main.py      y después:   python etl/validar_calidad.py
"""
import json
import shutil
import sys

import config
import etl_encuesta
import etl_resenas
from utilidades import Bitacora, Cuarentena, escribir_manifiesto, guardar_tabla

sys.stdout.reconfigure(encoding="utf-8")


def escribir_reporte(bit):
    lineas = ["# Reporte de calidad del ETL", "",
              "Generado automáticamente por `etl/etl_main.py`. Cada fila es una regla aplicada y cuántos registros "
              "afectó. Las filas eliminadas están en `rechazados/` con las columnas `Codigo_Regla` y `Motivo`.", ""]
    for fuente, pre in (("Encuesta", "encuesta"), ("Resenas", "resenas")):
        m = bit.metricas
        lineas += ["", f"## {fuente}", "",
                   f"Leídas: **{m[pre + '_filas_leidas']:,}** | Válidas: **{m[pre + '_filas_validas']:,}** | "
                   f"Rechazadas: **{m[pre + '_filas_rechazadas']:,}**", "",
                   "| Código | Regla | Dimensión | Acción | Filas |", "|---|---|---|---|---:|"]
        lineas += [f"| {p['codigo']} | {p['regla']} | {p['dimension']} | {p['accion']} | {p['filas']:,} |"
                   for p in bit.pasos if p["fuente"] == fuente]
    if bit.decisiones:
        lineas += ["", "## Decisiones a revisar", ""] + [f"- **{d['fuente']}**: {d['texto']}" for d in bit.decisiones]
    lineas += ["", "## Tablas cargadas", "", "| Tabla | Filas |", "|---|---:|"]
    lineas += [f"| {k.replace('filas_', '')} | {v:,} |" for k, v in bit.metricas.items() if k.startswith("filas_")]
    (config.LIMPIOS / "reporte_calidad.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")


def main():
    bit, cua = Bitacora(), Cuarentena()

    print("################ MANIFIESTO DE CRUDOS ################")
    man = escribir_manifiesto([config.ARCHIVO_ENCUESTA, config.ARCHIVO_RESENAS, config.ARCHIVO_UBICACION])
    for a in man["archivos"]:
        print(f"  {a['archivo']}: {a['bytes']:,} bytes  sha256={a['sha256'][:16]}...")

    print("\n################ EXTRACT + TRANSFORM ################")
    t_enc, cols_enc = etl_encuesta.procesar(bit, cua)
    t_res, cols_res, a_investigar = etl_resenas.procesar(bit, cua)

    print("\n################ LOAD (idempotente: se borra y se regenera) ################")
    if config.LIMPIOS.exists():
        shutil.rmtree(config.LIMPIOS)
    (config.LIMPIOS / "parquet").mkdir(parents=True)
    for nombre, df in {**t_enc, **t_res}.items():
        bit.metrica(f"filas_{nombre}", guardar_tabla(df, nombre))
    cua.guardar({"Encuesta": cols_enc, "Resenas": cols_res})
    a_investigar.to_csv(config.CUARENTENA / "resenas_a_investigar.csv", index=False, encoding="utf-8-sig")
    print(f"  rechazados/resenas_a_investigar.csv -> {len(a_investigar):,} filas (NO eliminadas, solo marcadas)")

    bit.metrica("manifiesto", {a["archivo"]: a["sha256"] for a in man["archivos"]})
    (config.LIMPIOS / "metricas_etl.json").write_text(
        json.dumps({"metricas": bit.metricas, "reglas": bit.pasos}, indent=2, ensure_ascii=False), "utf-8")
    escribir_reporte(bit)
    print("\nETL terminado. Revisa datos_limpios/reporte_calidad.md y luego ejecuta: python etl/validar_calidad.py")


if __name__ == "__main__":
    main()
