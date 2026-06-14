import os
import shutil
import subprocess
import argparse
import pandas as pd
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Executa o pipeline completo do BOSS")
    parser.add_argument("--input", required=True, help="Arquivo Excel fonte (ex: input/2010_2014.xlsx)")
    parser.add_argument("--n", type=int, default=160, help="Número de imagens (padrão: 160)")
    parser.add_argument("--source-images", default="images/boss", help="Pasta com as imagens originais")
    parser.add_argument("--selected-dir", default="images/selected", help="Pasta para onde as escolhidas irão")
    parser.add_argument("--output", default="output", help="Pasta para planilhas geradas")
    args = parser.parse_args()

    # 1. Rodar seleção
    print("\n" + "="*50)
    print("ETAPA 1: Selecionando estímulos...")
    print("="*50)
    cmd_select = [
        "uv", "run", "python", "select_stimuli.py",
        "--input", args.input,
        "--n", str(args.n),
        "--output", args.output
    ]
    subprocess.run(cmd_select, check=True)

    # 2. Ler CSV e copiar arquivos
    print("\n" + "="*50)
    print("ETAPA 2: Copiando as imagens selecionadas...")
    print("="*50)
    csv_file = Path(args.output) / f"boss_selecionadas_{args.n}.csv"
    if not csv_file.exists():
        print(f"Erro: CSV {csv_file} não encontrado.")
        return

    df = pd.read_csv(csv_file)
    filenames = df['FILENAME'].tolist()
    
    selected_path = Path(args.selected_dir)
    selected_path.mkdir(parents=True, exist_ok=True)

    # Limpar pasta se já houver imagens antigas
    for f in selected_path.iterdir():
        f.unlink()

    source_path = Path(args.source_images)
    copied_count = 0
    for name in filenames:
        # Tenta achar o .png garantindo a extensão
        if not name.lower().endswith('.png'):
            file_to_copy = f"{name}.png"
        else:
            file_to_copy = name
            
        src = source_path / file_to_copy
        dst = selected_path / file_to_copy
        if src.exists():
            shutil.copy2(src, dst)
            copied_count += 1
        else:
            print(f"  [Aviso] Arquivo não encontrado: {src}")

    print(f"Copiadas {copied_count} imagens originais (.png) para {selected_path}")

    if copied_count == 0:
        print("Nenhuma imagem copiada. Abortando.")
        return

    # 3. Otimizar
    print("\n" + "="*50)
    print("ETAPA 3: Otimizando imagens para WebP...")
    print("="*50)
    cmd_optimize = [
        "uv", "run", "python", "optimize_images.py",
        "--dir", str(selected_path)
    ]
    subprocess.run(cmd_optimize, check=True)

    # 4. Upload
    print("\n" + "="*50)
    print("ETAPA 4: Fazendo upload para o Supabase...")
    print("="*50)
    cmd_upload = [
        "uv", "run", "python", "upload_to_supabase.py",
        "--dir", str(selected_path)
    ]
    subprocess.run(cmd_upload, check=True)

    print("\nPipeline finalizado com sucesso! 🎉")

if __name__ == "__main__":
    main()
