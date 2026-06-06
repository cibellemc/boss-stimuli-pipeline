"""
select_stimuli_v3.py
====================
Seleciona N imagens do banco BOSS para o jogo To Remember.

Lógica em 4 etapas explícitas e defensáveis:

  1. FILTROS OBRIGATÓRIOS
     Critérios clínicos com base na literatura:
     - % DKO == 0        : nenhum participante deixou a imagem sem nomear
                           (Brodeur et al., 2014)
     - Familiarity > 4.0 : objetos altamente familiares a adultos mais velhos
                           (Hodges & Patterson, 1995)

  2. SCORE INDIVIDUAL
     Score composto normalizado [0, 1] com pesos clinicamente justificados:
     - Familiarity Mean        0.35  — via memória semântica preservada na DA
     - % Name Agreement        0.30  — estímulo sem ambiguidade lexical
     - Object Agreement Mean   0.20  — clareza perceptual da fotografia
     - Visual Complexity Mean  0.15  — preferência por imagens simples (invertido)

  3. SCORE DE CATEGORIA
     Média dos scores individuais por Modal category.
     Categorias com média mais alta = objetos mais fáceis para pacientes com DA.
     Serve de critério de ordenação: o algoritmo tenta cobrir primeiro as
     categorias mais fáceis (maior média), depois as demais.

  4. SELEÇÃO
     - Conta quantas categorias existem no pool filtrado.
     - Para cada categoria, em ordem decrescente de score médio,
       seleciona as melhores imagens até o limite por categoria.
     - Ordena o resultado final por score individual (melhores primeiro).
     - Retorna as primeiras N.

Uso:
    python select_stimuli_v3.py --input <arquivo.xlsx> [--n 80] [--output <dir>]

Parâmetros opcionais:
    --n              Total de imagens a selecionar (padrão: 80)
    --per-category   Máximo de imagens por categoria (padrão: automático = N / n_categorias, mínimo 2)
    --output         Diretório de saída (padrão: diretório atual)
"""

import argparse
import sys
from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------------
# 1. Carregamento e filtros obrigatórios
# ---------------------------------------------------------------------------

def load(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=0)
    df.columns = df.columns.str.strip()
    return df


def mandatory_filters(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filtros clínicos obrigatórios.
    Critérios: Brodeur et al. (2014); Hodges & Patterson (1995).
    """
    mask = (df["% DKO"] == 0) & (df["Familiarity Mean"] > 4.0)
    pool = df[mask].copy()
    print(f"[1] Filtros obrigatórios (DKO=0, Familiaridade>4.0)")
    print(f"    Total no banco : {len(df)}")
    print(f"    Pool resultante: {len(pool)}")
    return pool


# ---------------------------------------------------------------------------
# 2. Score individual
# ---------------------------------------------------------------------------

def compute_score(pool: pd.DataFrame) -> pd.DataFrame:
    """
    Score composto normalizado. Pesos refletem relevância clínica para DA.
    Todos os componentes normalizados para [0, 1] antes da ponderação.
    """
    def norm(s):
        mn, mx = s.min(), s.max()
        if mx == mn:
            return pd.Series(0.5, index=s.index)
        return (s - mn) / (mx - mn)

    p = pool.copy()
    p["_fam"]  = norm(p["Familiarity Mean"])
    p["_name"] = norm(p["% Name Agreement (/Fq names)"].fillna(0))
    p["_obj"]  = norm(p["Object Agreement Mean"].fillna(
                      p["Object Agreement Mean"].mean()))
    p["_cpx"]  = 1 - norm(p["Visual Complexity Mean"].fillna(
                           p["Visual Complexity Mean"].mean()))

    p["Score"] = (
        0.35 * p["_fam"] +
        0.30 * p["_name"] +
        0.20 * p["_obj"] +
        0.15 * p["_cpx"]
    ).round(4)

    return p


# ---------------------------------------------------------------------------
# 3. Score de categoria (média dos scores individuais por Modal category)
# ---------------------------------------------------------------------------

def category_scores(pool: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega o Score médio por categoria.
    Retorna DataFrame ordenado do mais fácil (maior média) ao mais difícil.
    """
    cat_stats = (
        pool.groupby("Modal category")["Score"]
        .agg(n_disponiveis="count", score_medio="mean")
        .round(4)
        .sort_values("score_medio", ascending=False)
        .reset_index()
    )
    print(f"\n[3] Categorias no pool filtrado: {len(cat_stats)}")
    print(f"    {'Categoria':<45} {'N':>5}  {'Score médio':>11}")
    print(f"    {'-'*45} {'-'*5}  {'-'*11}")
    for _, row in cat_stats.iterrows():
        print(f"    {row['Modal category']:<45} {int(row['n_disponiveis']):>5}  {row['score_medio']:>11.4f}")
    return cat_stats


# ---------------------------------------------------------------------------
# 4. Seleção
# ---------------------------------------------------------------------------

def select(pool: pd.DataFrame, cat_stats: pd.DataFrame,
           n: int, per_category: int) -> pd.DataFrame:
    """
    Seleciona imagens cobrindo o máximo de categorias,
    priorizando as de maior score médio (mais fáceis para DA).

    Para cada categoria em ordem decrescente de score médio:
      - Pega as melhores imagens (maior Score individual) até per_category.
    Depois ordena tudo por Score individual e retorna as primeiras N.
    """
    selected_rows = []

    for _, cat_row in cat_stats.iterrows():
        cat = cat_row["Modal category"]
        candidates = (
            pool[pool["Modal category"] == cat]
            .sort_values("Score", ascending=False)
            .head(per_category)
        )
        selected_rows.append(candidates)

    all_candidates = pd.concat(selected_rows).sort_values("Score", ascending=False)

    # Remove duplicatas (não deve haver, mas garantia)
    all_candidates = all_candidates.drop_duplicates(subset="FILENAME")

    result = all_candidates.head(n).reset_index(drop=True)
    return result


# ---------------------------------------------------------------------------
# Saída
# ---------------------------------------------------------------------------

def build_output(result: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "FILENAME", "Dataset", "% DKO", "% DKN", "% TOT",
        "Modal name", "% Name Agreement (/Fq names)", "Nb diff names", "H-value",
        "Modal category", "% Category Agreement", "Hcat-value",
        "Non-Normative Category",
        "Familiarity Mean", "Familiarity StDev",
        "Visual Complexity Mean", "Visual Complexity StDev",
        "Object Agreement Mean", "Object Agreement StDev",
        "Viewpoint Agreement Mean", "Viewpoint Agreement StDev",
        "Manipulability Mean", "Manipulability StDev",
        "Score",
    ]
    return result[[c for c in cols if c in result.columns]]


def print_summary(result: pd.DataFrame, n: int, per_category: int) -> None:
    print(f"\n{'='*60}")
    print(f"  SELECIONADAS: {len(result)} / {n}  |  per_category: {per_category}")
    print(f"{'='*60}")

    cat_counts = result["Modal category"].value_counts()
    print(f"\nCategorias cobertas: {result['Modal category'].nunique()}")
    for cat, cnt in cat_counts.items():
        print(f"  {cat:<45} {cnt:>3}")

    multi = result.groupby("Modal name").size()
    multi = multi[multi >= 2]
    print(f"\nConceitos com múltiplos exemplares selecionados: {len(multi)}")
    for concept, cnt in multi.items():
        imgs = result[result["Modal name"] == concept]["FILENAME"].tolist()
        print(f"  '{concept}' ({cnt}): {', '.join(imgs)}")

    print(f"\nFamiliaridade — média: {result['Familiarity Mean'].mean():.3f}"
          f"  mínima: {result['Familiarity Mean'].min():.3f}")
    print(f"Score         — média: {result['Score'].mean():.4f}"
          f"  mínimo: {result['Score'].min():.4f}")
    print(f"% DKO == 0    — todas: {(result['% DKO'] == 0).all()}")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Seleciona N imagens do BOSS para o To Remember"
    )
    parser.add_argument("--input", required=True,
                        help="Caminho para o arquivo BOSS .xlsx")
    parser.add_argument("--n", type=int, default=80,
                        help="Total de imagens a selecionar (padrão: 80)")
    parser.add_argument("--per-category", type=int, default=0,
                        help="Máximo por categoria. 0 = automático: N / n_categorias (mínimo 2)")
    parser.add_argument("--output", default=".",
                        help="Diretório de saída (padrão: diretório atual)")
    args = parser.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Carregar e filtrar
    raw  = load(args.input)
    pool = mandatory_filters(raw)

    if len(pool) < args.n:
        print(f"ERRO: apenas {len(pool)} imagens passam nos filtros; "
              f"impossível selecionar {args.n}.")
        sys.exit(1)

    # 2. Score individual
    pool = compute_score(pool)
    print(f"\n[2] Score individual calculado para {len(pool)} imagens")

    # 3. Score de categoria
    cat_stats = category_scores(pool)
    n_cats = len(cat_stats)

    # 4. per_category automático se não informado
    if args.per_category == 0:
        per_category = max(2, -(-args.n // n_cats))  # divisão teto
    else:
        per_category = args.per_category

    print(f"\n[4] Seleção: n={args.n}  n_categorias={n_cats}  per_category={per_category}")

    result = select(pool, cat_stats, args.n, per_category)
    result = build_output(result)
    print_summary(result, args.n, per_category)

    # Aviso se ficou curto
    if len(result) < args.n:
        print(f"[aviso] Selecionadas {len(result)} imagens (abaixo de {args.n}). "
              f"Aumente --per-category ou reduza --n.")

    # Exportar
    csv_path = out_dir / f"boss_selecionadas_{args.n}.csv"
    result.to_csv(csv_path, index=False)
    print(f"\n[saída] CSV  → {csv_path}")

    xlsx_path = out_dir / f"boss_selecionadas_{args.n}.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        result.to_excel(writer, index=False, sheet_name="Selecionadas")
        ws = writer.sheets["Selecionadas"]
        for col in ws.columns:
            w = max(len(str(c.value or "")) for c in col) + 2
            ws.column_dimensions[col[0].column_letter].width = min(w, 40)
    print(f"[saída] XLSX → {xlsx_path}")


if __name__ == "__main__":
    main()