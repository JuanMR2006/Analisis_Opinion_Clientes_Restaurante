"""Análisis estadístico (ANOVA de un factor y alternativa no paramétrica).

Lee las tablas de datos_limpios/ (hay que ejecutar antes etl/etl_main.py) y responde:

  Encuesta
    E1-E16  ¿Calif_Promedio / Servicio / Comida / Ambiente cambian según Cocina_Preferida, Ocasion,
            Franja_Visita o Frecuencia_Visita?
    E17     ¿Tiempo_Espera_Min cambia según Franja_Visita?
  Reseñas
    R1      ¿Rating cambia según el nivel de precio? (sin "Sin dato")
    R2      ¿Rating cambia según el año?
    R3      ¿Rating cambia según la cocina principal? (solo cocinas con >= MIN_RESENAS_COCINA reseñas)

Para cada prueba:
  1. Supuestos: normalidad de los residuos (Shapiro-Wilk sobre una muestra de hasta 5.000) y
     homogeneidad de varianzas (Levene centrado en la mediana, o Brown-Forsythe).
  2. ANOVA clásico (F, p, eta²) y Kruskal-Wallis (H, p, épsilon²).
     Prueba principal: ANOVA si se cumplen ambos supuestos; si no, Kruskal-Wallis.
  3. Si la prueba principal es significativa: post-hoc de Tukey HSD (y Mann-Whitney con corrección
     de Holm cuando la prueba principal es Kruskal-Wallis).

Salidas en analisis/resultados/: resumen_pruebas.csv, descriptivos.csv, posthoc.csv,
resultados_anova.md y graficos/*.png.

Uso:  python analisis/anova.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from statsmodels.stats.multitest import multipletests

RAIZ = Path(__file__).resolve().parent.parent
LIMPIOS = RAIZ / "datos_limpios"
SALIDA = RAIZ / "analisis" / "resultados"
GRAFICOS = SALIDA / "graficos"

ALFA = 0.05
SEMILLA = 42
MAX_SHAPIRO = 5000          # Shapiro-Wilk no es fiable con más de 5.000 datos: se usa una muestra
MIN_RESENAS_COCINA = 1000   # R3: solo cocinas con suficientes reseñas para comparar

# Orden lógico de las categorías (para tablas y gráficos)
ORDEN = {
    "Franja_Visita": ["Breakfast", "Lunch", "Dinner"],
    "Frecuencia_Visita": ["Daily", "Weekly", "Monthly", "Rarely"],
    "Precio_Etiqueta": ["Económico", "Medio", "Alto"],
}


# ----------------------------------------------------------------------------- carga
def cargar():
    leer = lambda n: pd.read_csv(LIMPIOS / f"{n}.csv", encoding="utf-8-sig")
    try:
        enc = leer("Fact_Encuesta")
        res = leer("Fact_Resenas")
        rest = leer("Dim_Restaurante")
    except FileNotFoundError:
        raise SystemExit("No encuentro datos_limpios/. Ejecuta primero: python etl/etl_main.py")
    res = res.merge(rest[["Restaurant_ID", "Precio_Etiqueta", "Cocina_Principal"]], on="Restaurant_ID")
    res["Anio"] = res["Fecha"].str[:4]
    return enc, res


# ----------------------------------------------------------------------------- estadística
def magnitud(efecto: float) -> str:
    """Convención de Cohen para eta² (se usa igual para épsilon²)."""
    if efecto < 0.01:
        return "despreciable"
    if efecto < 0.06:
        return "pequeño"
    if efecto < 0.14:
        return "mediano"
    return "grande"


def fmt_p(p: float) -> str:
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


def prueba(df, y, factor, codigo, pregunta, poblacion):
    datos = df[[y, factor]].dropna()
    if factor == "Cocina_Principal":  # de mayor a menor media, para leer el gráfico como ranking
        orden = datos.groupby(factor)[y].mean().sort_values(ascending=False).index.tolist()
    else:
        orden = ORDEN.get(factor) or sorted(datos[factor].unique())
    orden = [g for g in orden if g in set(datos[factor])]
    grupos = [datos.loc[datos[factor] == g, y].to_numpy(float) for g in orden]
    n, k = len(datos), len(grupos)

    # Descriptivos
    desc = (
        datos.groupby(factor)[y]
        .agg(n="size", media="mean", desv="std", mediana="median")
        .reindex(orden)
        .reset_index()
        .rename(columns={factor: "grupo"})
    )
    desc["ic95"] = 1.96 * desc["desv"] / np.sqrt(desc["n"])
    desc.insert(0, "codigo", codigo)
    desc.insert(1, "variable", y)
    desc.insert(2, "factor", factor)

    # Supuestos (residuos = valor - media de su grupo)
    residuos = datos[y] - datos.groupby(factor)[y].transform("mean")
    muestra = residuos.sample(min(len(residuos), MAX_SHAPIRO), random_state=SEMILLA)
    p_shapiro = stats.shapiro(muestra).pvalue
    p_levene = stats.levene(*grupos, center="median").pvalue
    normal, homogenea = p_shapiro >= ALFA, p_levene >= ALFA

    # ANOVA clásico
    f, p_anova = stats.f_oneway(*grupos)
    media_total = datos[y].mean()
    ss_entre = sum(len(g) * (g.mean() - media_total) ** 2 for g in grupos)
    ss_total = ((datos[y] - media_total) ** 2).sum()
    eta2 = ss_entre / ss_total

    # Kruskal-Wallis
    h, p_kw = stats.kruskal(*grupos)
    eps2 = max((h - k + 1) / (n - k), 0.0)

    usa_anova = normal and homogenea
    principal = "ANOVA" if usa_anova else "Kruskal-Wallis"
    p_principal = p_anova if usa_anova else p_kw
    efecto = eta2 if usa_anova else eps2
    significativo = p_principal < ALFA

    # Post-hoc
    posthoc = []
    if significativo:
        tukey = pairwise_tukeyhsd(datos[y], datos[factor], alpha=ALFA)
        tabla = pd.DataFrame(tukey._results_table.data[1:], columns=tukey._results_table.data[0])
        for _, fila in tabla.iterrows():
            posthoc.append({
                "codigo": codigo, "metodo": "Tukey HSD",
                "grupo_1": fila["group1"], "grupo_2": fila["group2"],
                "diferencia_medias": round(float(fila["meandiff"]), 4),
                "p_ajustado": float(fila["p-adj"]), "significativo": bool(fila["reject"]),
            })
        if not usa_anova:
            pares, ps = [], []
            for i in range(k):
                for j in range(i + 1, k):
                    pares.append((orden[i], orden[j], grupos[i].mean() - grupos[j].mean()))
                    ps.append(stats.mannwhitneyu(grupos[i], grupos[j]).pvalue)
            rechaza, p_holm, _, _ = multipletests(ps, alpha=ALFA, method="holm")
            for (g1, g2, dif), p_aj, r in zip(pares, p_holm, rechaza):
                posthoc.append({
                    "codigo": codigo, "metodo": "Mann-Whitney (Holm)",
                    "grupo_1": g1, "grupo_2": g2, "diferencia_medias": round(float(-dif), 4),
                    "p_ajustado": float(p_aj), "significativo": bool(r),
                })

    resumen = {
        "codigo": codigo, "poblacion": poblacion, "pregunta": pregunta,
        "variable": y, "factor": factor, "n": n, "grupos": k,
        "p_shapiro": p_shapiro, "p_levene": p_levene,
        "F": f, "p_anova": p_anova, "eta2": eta2,
        "H": h, "p_kruskal": p_kw, "epsilon2": eps2,
        "prueba_principal": principal, "p_principal": p_principal,
        "efecto": efecto, "magnitud_efecto": magnitud(efecto),
        "significativo": significativo,
    }
    grafico(desc, y, factor, codigo, resumen)
    return resumen, desc, posthoc


def grafico(desc, y, factor, codigo, r):
    fig, ax = plt.subplots(figsize=(7, 4))
    x = np.arange(len(desc))
    ax.errorbar(x, desc["media"], yerr=desc["ic95"], fmt="o", color="#1F4E79",
                ecolor="#7F7F7F", capsize=4, markersize=7)
    ax.set_xticks(x, desc["grupo"], rotation=30 if len(desc) > 5 else 0, ha="right" if len(desc) > 5 else "center")
    ax.set_ylabel(f"{y} (media ± IC 95 %)")
    ax.set_xlabel(factor)
    estad = f"F = {r['F']:.2f}" if r["prueba_principal"] == "ANOVA" else f"H = {r['H']:.2f}"
    ax.set_title(f"{codigo}: {y} según {factor}\n{r['prueba_principal']}: {estad}, "
                 f"p {fmt_p(r['p_principal'])}, efecto {r['efecto']:.3f} ({r['magnitud_efecto']})",
                 fontsize=10)
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(GRAFICOS / f"{codigo}_{y}_{factor}.png", dpi=150)
    plt.close(fig)


# ----------------------------------------------------------------------------- reporte
def reporte_md(resumen: pd.DataFrame, desc: pd.DataFrame, posthoc: pd.DataFrame, n_cocinas: list) -> str:
    L = ["# Resultados del análisis estadístico (ANOVA)", "",
         "Generado por `analisis/anova.py` a partir de `datos_limpios/`. Nivel de significancia: α = 0,05.", "",
         "## Método", "",
         "- **Supuestos:** normalidad de los residuos con Shapiro-Wilk (muestra aleatoria de hasta 5.000 datos, "
         "semilla 42) y homogeneidad de varianzas con Levene centrado en la mediana.",
         "- **Prueba principal:** ANOVA de un factor si se cumplen ambos supuestos; si no, Kruskal-Wallis. "
         "Se reportan las dos para comparar.",
         "- **Tamaño del efecto:** η² para ANOVA y ε² para Kruskal-Wallis. Referencia: < 0,01 despreciable, "
         "0,01–0,06 pequeño, 0,06–0,14 mediano, ≥ 0,14 grande.",
         "- **Post-hoc:** Tukey HSD si la prueba principal es significativa; con Kruskal-Wallis se agrega "
         "Mann-Whitney por pares con corrección de Holm.",
         f"- **R3** usa solo cocinas con al menos {MIN_RESENAS_COCINA} reseñas y excluye \"Sin dato\": "
         f"{', '.join(n_cocinas)}.",
         "- **R1** excluye las reseñas con nivel de precio \"Sin dato\".",
         "- **Comparaciones múltiples:** el p de la prueba principal se corrige con Holm dentro de cada familia "
         "(17 pruebas de la encuesta, 3 de las reseñas). Una prueba solo se considera significativa si lo sigue "
         "siendo tras la corrección.",
         "- **Post-hoc:** la diferencia de medias es grupo 2 − grupo 1.", "",
         "## Resumen", "",
         "| Código | Pregunta | n | Supuestos (Shapiro / Levene) | Prueba | Estadístico | p | p Holm | Efecto | ¿Significativo? |",
         "|---|---|---:|---|---|---|---|---|---|---|"]
    for _, r in resumen.iterrows():
        sup = f"{'✓' if r.p_shapiro >= ALFA else '✗'} / {'✓' if r.p_levene >= ALFA else '✗'}"
        est = f"F = {r.F:.2f}" if r.prueba_principal == "ANOVA" else f"H = {r.H:.2f}"
        L.append(f"| {r.codigo} | {r.pregunta} | {r.n:,} | {sup} | {r.prueba_principal} | {est} | "
                 f"{fmt_p(r.p_principal)} | {fmt_p(r.p_holm_familia)} | {r.efecto:.4f} ({r.magnitud_efecto}) | "
                 f"{'Sí' if r.significativo_ajustado else ('Solo sin corregir' if r.significativo else 'No')} |")
    L += ["", "✓ = se cumple el supuesto (p ≥ 0,05); ✗ = no se cumple.", ""]

    L += ["## Detalle por prueba", ""]
    for _, r in resumen.iterrows():
        L += [f"### {r.codigo}. {r.pregunta}", "",
              f"- ANOVA: F = {r.F:.3f}, p {fmt_p(r.p_anova)}, η² = {r.eta2:.4f}",
              f"- Kruskal-Wallis: H = {r.H:.3f}, p {fmt_p(r.p_kruskal)}, ε² = {r.epsilon2:.4f}",
              f"- Supuestos: Shapiro-Wilk p {fmt_p(r.p_shapiro)}, Levene p {fmt_p(r.p_levene)}",
              f"- Prueba principal: {r.prueba_principal}; p corregido (Holm) {fmt_p(r.p_holm_familia)}", "",
              "| Grupo | n | Media | Desv. | Mediana |", "|---|---:|---:|---:|---:|"]
        for _, d in desc[desc.codigo == r.codigo].iterrows():
            L.append(f"| {d.grupo} | {d.n:,} | {d.media:.3f} | {d.desv:.3f} | {d.mediana:.1f} |")
        ph = posthoc[(posthoc.codigo == r.codigo) & posthoc.significativo] if len(posthoc) else posthoc
        if r.significativo:
            if not r.significativo_ajustado:
                L += ["", "**Atención:** deja de ser significativa al corregir por comparaciones múltiples, "
                      "así que los pares de abajo no deben tomarse como hallazgo."]
            if len(ph):
                L += ["", "Pares con diferencia significativa:", ""]
                for _, q in ph.iterrows():
                    L.append(f"- {q.metodo}: {q.grupo_1} vs {q.grupo_2} "
                             f"(diferencia de medias {q.diferencia_medias:+.3f}, p ajustado {fmt_p(q.p_ajustado)})")
            else:
                L += ["", "La prueba global es significativa, pero ningún par sale significativo en el post-hoc."]
        L += ["", f"![{r.codigo}](graficos/{r.codigo}_{r.variable}_{r.factor}.png)", ""]
    return "\n".join(L)


# ----------------------------------------------------------------------------- main
def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    GRAFICOS.mkdir(parents=True, exist_ok=True)
    enc, res = cargar()

    pruebas = []
    nombres = {"Calif_Promedio": "calificación promedio", "Calif_Servicio": "calificación de servicio",
               "Calif_Comida": "calificación de comida", "Calif_Ambiente": "calificación de ambiente"}
    factores = {"Cocina_Preferida": "la cocina preferida", "Ocasion": "la ocasión",
                "Franja_Visita": "la franja de visita", "Frecuencia_Visita": "la frecuencia de visita"}
    i = 1
    for y, ny in nombres.items():
        for f, nf in factores.items():
            pruebas.append((enc, y, f, f"E{i}", f"¿La {ny} cambia según {nf}?", "Encuesta"))
            i += 1
    pruebas.append((enc, "Tiempo_Espera_Min", "Franja_Visita", f"E{i}",
                    "¿El tiempo de espera cambia según la franja de visita?", "Encuesta"))

    con_precio = res[res["Precio_Etiqueta"] != "Sin dato"]
    pruebas.append((con_precio, "Rating", "Precio_Etiqueta", "R1",
                    "¿El rating cambia según el nivel de precio?", "Reseñas"))
    pruebas.append((res, "Rating", "Anio", "R2", "¿El rating cambia según el año?", "Reseñas"))
    conteo = res.loc[res["Cocina_Principal"] != "Sin dato", "Cocina_Principal"].value_counts()
    cocinas = conteo[conteo >= MIN_RESENAS_COCINA].index.tolist()
    pruebas.append((res[res["Cocina_Principal"].isin(cocinas)], "Rating", "Cocina_Principal", "R3",
                    "¿El rating cambia según la cocina principal?", "Reseñas"))

    resumenes, descs, posthocs = [], [], []
    for args in pruebas:
        r, d, p = prueba(*args)
        resumenes.append(r)
        descs.append(d)
        posthocs.extend(p)

    resumen = pd.DataFrame(resumenes)
    # Corrección por comparaciones múltiples (Holm) dentro de cada familia de pruebas:
    # con 17 pruebas en la encuesta, al menos una puede salir "significativa" solo por azar.
    resumen["p_holm_familia"] = np.nan
    for pob, idx in resumen.groupby("poblacion").groups.items():
        resumen.loc[idx, "p_holm_familia"] = multipletests(resumen.loc[idx, "p_principal"], method="holm")[1]
    resumen["significativo_ajustado"] = resumen["p_holm_familia"] < ALFA
    desc = pd.concat(descs, ignore_index=True)
    posthoc = pd.DataFrame(posthocs, columns=["codigo", "metodo", "grupo_1", "grupo_2",
                                              "diferencia_medias", "p_ajustado", "significativo"])
    for _, r in resumen.iterrows():
        print(f"{r.codigo:>4} {r.prueba_principal:<15} p {fmt_p(r.p_principal):>8}  p Holm {fmt_p(r.p_holm_familia):>8}  "
              f"efecto {r.efecto:.4f} ({r.magnitud_efecto:<12})  {r.pregunta}")
    resumen.round(6).to_csv(SALIDA / "resumen_pruebas.csv", index=False, encoding="utf-8-sig")
    desc.round(4).to_csv(SALIDA / "descriptivos.csv", index=False, encoding="utf-8-sig")
    posthoc.to_csv(SALIDA / "posthoc.csv", index=False, encoding="utf-8-sig")
    (SALIDA / "resultados_anova.md").write_text(
        reporte_md(resumen, desc, posthoc, [f"{c} ({conteo[c]:,})" for c in cocinas]), encoding="utf-8")
    print(f"\nListo. Resultados en {SALIDA.relative_to(RAIZ)}/")


if __name__ == "__main__":
    main()
