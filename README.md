# boss-stimuli-pipeline

Scripts para selecionar, otimizar e carregar estímulos do **BOSS** (Brief Standardized Object Naming, Brodeur et al.) para o jogo **To Remember**.

O pipeline cobre quatro etapas sequenciais automáticas: **seleção** de imagens a partir das normas BOSS → **separação** dos arquivos originais → **otimização** das imagens (PNG → WebP 512 × 512) → **upload** para o bucket do Supabase.

---

## Organização do repositório

| Arquivo                     | Descrição                                                                                       |
| --------------------------- | ------------------------------------------------------------------------------------------------- |
| `input/2010_2014.xlsx`      | Quadro combinado dos datasets BOSS-2010 e BOSS-2014 com métricas prontas para filtragem.         |
| `main.py`                   | **Script principal (Recomendado)**. Orquestra a execução automática das etapas de imagem.  |
| `select_stimuli.py`         | Seleciona automaticamente*N* estímulos a partir do Excel com critérios clínicos.             |
| `optimize_images.py`        | Redimensiona imagens PNG para 512 × 512 px e converte para WebP (qualidade 80).                  |
| `insert_bucket_supabase.py` | Envia as imagens `.webp` otimizadas para o bucket `boss-images` no Supabase Storage via HTTP. |
| `insert_boss.py`            | Insere as métricas das imagens na tabela do banco de dados (ex: `estimulos`) no Supabase.       |
| `images/boss/`              | Pasta onde você deve colocar todas as imagens originais `.png` do banco BOSS.                  |
| `images/selected/`          | Pasta gerada automaticamente com as imagens escolhidas e otimizadas.                              |
| `output/`                   | Diretório gerado automaticamente com as CSVs e XLSXs de resultado da seleção.                  |
| `.env`                      | Variáveis de ambiente com credenciais do Supabase (não versionado).                             |

---

## Requisitos

- Python 3.12+
- Um projeto no [Supabase](https://supabase.com/).

### Instalação das dependências

Este projeto usa **uv** como gerenciador de pacotes:

```bash
# Instalar dependências a partir do pyproject.toml
uv sync
```

---

## Variáveis de ambiente (`.env`)

Crie um arquivo `.env` na raiz do projeto. O `.gitignore` já ignora esse arquivo para evitar commits acidentais de credenciais.

```env
SUPABASE_URL=https://<seu-projeto>.supabase.co
SUPABASE_ANON_KEY=<sua-chave-secret-ou-publishable>
```

> ⚠️ **MUITO IMPORTANTE SOBRE A CHAVE E O BUCKET:**
> O script tenta criar automaticamente o bucket `boss-images` no seu Supabase.
>
> - Para que a criação automática funcione, você **precisa** usar a sua **Secret Key** (`service_role` key) no `.env`. A Publishable key (antiga `anon`) bloqueia a criação de buckets via código por padrão devido ao RLS (Row Level Security).
> - Se você preferir usar a Publishable key, você precisará **criar o bucket `boss-images` manualmente** no painel do Supabase (Storage) antes de rodar o pipeline, e configurar as políticas (RLS) para permitir os uploads.

---

## Execução do Pipeline Automatizado (Recomendado)

O jeito mais fácil de rodar tudo é usando o script unificador `main.py`. Ele faz todo o trabalho braçal por você: roda a seleção, cria uma pasta isolada, copia apenas as imagens escolhidas, otimiza para WebP e faz o upload.

```bash
uv run python main.py --input input/2010_2014.xlsx --n 160
```

**Parâmetros do `main.py`:**

- `--input`: Caminho para o arquivo BOSS `.xlsx` (obrigatório).
- `--n`: Total de imagens a selecionar (padrão: `160`).
- `--source-images`: Pasta com as imagens originais completas (padrão: `images/boss`).
- `--selected-dir`: Pasta para onde as escolhidas serão copiadas e otimizadas (padrão: `images/selected`).
- `--output`: Diretório de saída para as planilhas geradas (padrão: `output`).

A seleção segue **4 etapas clínicas explícitas** baseadas em Brodeur et al. (2014) e Hodges & Patterson (1995), priorizando a ausência de DKO, alta familiaridade e baixa complexidade visual.

---

## Execução Manual (Passo a Passo Opcional)

Caso precise rodar partes isoladas do processo:

**1. Apenas selecionar (Gera planilhas CSV/Excel):**

```bash
uv run python select_stimuli.py --input input/2010_2014.xlsx --n 160 --output output
```

**2. Apenas otimizar:**

```bash
uv run python optimize_images.py --dir images/selected
```

**3. Apenas upload das imagens (Bucket):**

```bash
uv run python insert_bucket_supabase.py --dir images/selected
```

**4. Atualizar o banco de dados (Tabela de métricas):**

```bash
uv run python insert_boss.py --csv output/boss_selecionadas_160.csv --table estimulos --action replace
```

---

## Checklist rápida

1. Coloque todas as imagens originais do BOSS na pasta `images/boss/`.
2. `cp .env.example .env` e preencha `SUPABASE_URL` e `SUPABASE_ANON_KEY` (use a **Secret Key** para evitar erros de permissão).
3. `uv sync` para instalar dependências.
4. `uv run python main.py --input input/2010_2014.xlsx --n 160`
5. Verificar no painel Supabase → **Storage** → bucket `boss-images`.
6. Rodar o script de banco de dados para salvar as métricas na tabela (opcional, requer o arquivo CSV gerado na etapa 4): `uv run python insert_boss.py --csv output/boss_selecionadas_160.csv --table estimulos --action replace`
