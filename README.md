# boss-stimuli-pipeline

Scripts para selecionar, otimizar e carregar estímulos do **BOSS** (Brief Standardized Object Naming, Brodeur et al.) para o jogo **To Remember**.

O pipeline cobre três etapas sequenciais: **seleção** de imagens a partir das normas BOSS → **otimização** das imagens (PNG → WebP 512 × 512) → **upload** para o bucket do Supabase.

---

## Organização do repositório

| Arquivo                  | Descrição                                                                                     |
| ------------------------ | --------------------------------------------------------------------------------------------- |
| `input/2010_2014.xlsx`   | Quadro combinado dos datasets BOSS-2010 e BOSS-2014 com métricas prontas para filtragem (DKO/DKN/TOT, acordos de nome/categoria, escalas perceptivo-cognitivas). É a fonte do `select_stimuli.py`. |
| `select_stimuli.py`      | Seleciona automaticamente *N* estímulos a partir do Excel com critérios clínicos e dispersão por categoria. |
| `optimize_images.py`     | Redimensiona imagens PNG para 512 × 512 px e converte para WebP (qualidade 80), apagando os PNGs originais. |
| `upload_to_supabase.py`  | Envia as imagens `.webp` otimizadas para o bucket `stimuli` no Supabase Storage via HTTP. |
| `output/`                | Diretório gerado automaticamente com os CSVs e XLSXs de resultado da seleção. |
| `.env`                   | Variáveis de ambiente com credenciais do Supabase (não versionado). |

---

## Requisitos

- Python 3.12+
- Um projeto no [Supabase](https://supabase.com/) com um bucket chamado `stimuli`.

### Instalação das dependências

Este projeto usa **uv** como gerenciador de pacotes:

```bash
# Instalar dependências a partir do pyproject.toml
uv sync
```

Dependências declaradas: `pandas`, `openpyxl`, `lxml`, `python-dotenv`.  
O `optimize_images.py` usa `Pillow` (instale separadamente se necessário: `uv add pillow`).

---

## Variáveis de ambiente (`.env`)

Crie um arquivo `.env` na raiz do projeto. O `.gitignore` já ignora esse arquivo para evitar commits acidentais de credenciais.

```env
SUPABASE_URL=https://<seu-projeto>.supabase.co
SUPABASE_ANON_KEY=<sua-chave-anon>
```

> **Nota de segurança:** Para cargas em produção ou ambientes sem RLS configurado, prefira usar a `service_role` key em vez da `anon_key`. Nunca exponha a `service_role` no cliente do jogo.

---

## Pipeline passo a passo

### Etapa 1 — Selecionar estímulos

```bash
uv run python select_stimuli.py --input input/2010_2014.xlsx --n 160 --output output
```

**Parâmetros:**

| Parâmetro        | Descrição                                                          | Padrão       |
| ---------------- | ------------------------------------------------------------------ | ------------ |
| `--input`        | Caminho para o arquivo BOSS `.xlsx`                                | obrigatório  |
| `--n`            | Total de imagens a selecionar                                      | `80`         |
| `--per-category` | Máximo de imagens por categoria (0 = automático: N ÷ n_categorias, mínimo 2) | `0` |
| `--output`       | Diretório de saída para CSV e XLSX                                 | `.` (atual)  |

A seleção segue **4 etapas clínicas explícitas**:

1. **Filtros obrigatórios** — `% DKO == 0` e `Familiarity Mean > 4.0` (Brodeur et al., 2014; Hodges & Patterson, 1995).
2. **Score individual** — composto normalizado [0, 1] ponderado por relevância para Doença de Alzheimer: Familiaridade (0,35), Concordância de Nome (0,30), Concordância de Objeto (0,20), Complexidade Visual invertida (0,15).
3. **Score de categoria** — média dos scores por `Modal category`, ordenando categorias do mais fácil ao mais difícil para pacientes com DA.
4. **Seleção** — cobre o máximo de categorias possível, priorizando as mais fáceis, e retorna as *N* melhores imagens.

Os arquivos gerados ficam em `output/`:
- `boss_selecionadas_<N>.csv`
- `boss_selecionadas_<N>.xlsx`

---

### Etapa 2 — Otimizar imagens

Configure o caminho da pasta com as imagens diretamente no script (`target_dir`) e execute:

```bash
uv run python optimize_images.py
```

O script:
- Encontra todos os arquivos `.png` no diretório configurado.
- Redimensiona cada imagem para caber em **512 × 512 px** (mantendo a proporção).
- Salva como `.webp` com qualidade 80.
- **Apaga o `.png` original**.

---

### Etapa 3 — Upload para o Supabase

```bash
uv run python upload_to_supabase.py
```

O script:
- Lê as credenciais do `.env`.
- Envia todos os arquivos `.webp` do diretório configurado para o bucket `stimuli`.
- Pula arquivos que já existem no bucket (status HTTP 409), tornando o comando seguro para reexecutar.

---

## Checklist rápida

1. `cp .env.example .env` e preencha `SUPABASE_URL` e `SUPABASE_ANON_KEY`.
2. `uv sync` para instalar dependências.
3. `uv run python select_stimuli.py --input input/2010_2014.xlsx --n 160 --output output`
4. `uv run python optimize_images.py` (após mover/copiar as imagens selecionadas para a pasta configurada).
5. `uv run python upload_to_supabase.py`
6. Verificar no painel Supabase → **Storage** → bucket `stimuli`.