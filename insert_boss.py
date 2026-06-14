import os
import argparse
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

project_url = os.getenv('SUPABASE_URL')
anon_key = os.getenv('SUPABASE_ANON_KEY')

def _headers(content_type='application/json'):
    return {
        'Authorization': f'Bearer {anon_key}',
        'apikey': anon_key,
        'Content-Type': content_type,
    }

def clear_table(table_name):
    print(f"Limpando tabela public.{table_name}...")
    # Supabase PostgREST exige um filtro para DELETE
    url = f"{project_url}/rest/v1/{table_name}?id=gt.0"
    response = requests.delete(url, headers=_headers())
    if response.status_code not in (200, 204):
        print(f"Erro ao limpar tabela '{table_name}': {response.status_code} - {response.text}")
    else:
        print(f"Tabela '{table_name}' limpa com sucesso.")

def upload_csv(csv_path, table_name):
    print(f"Lendo arquivo CSV: {csv_path}...")
    df = pd.read_csv(csv_path)
    
    def clean_val(v):
        if pd.isna(v):
            return None
        return v

    records = []
    for _, row in df.iterrows():
        filename = row['FILENAME']
        
        record = {
            'nome_arquivo': filename,
            'dataset': clean_val(row.get('Dataset')),
            'pct_dko': clean_val(row.get('% DKO')),
            'pct_dkn': clean_val(row.get('% DKN')),
            'pct_tot': clean_val(row.get('% TOT')),
            'nome_modal': clean_val(row.get('Modal name')),
            'pct_concordancia_nome': clean_val(row.get('% Name Agreement (/Fq names)')),
            'qtd_nomes_alt': clean_val(row.get('Nb diff names')),
            'valor_h': clean_val(row.get('H-value')),
            'categoria_modal': clean_val(row.get('Modal category')),
            'pct_concordancia_categoria': clean_val(row.get('% Category Agreement')),
            'hcat_value': clean_val(row.get('Hcat-value')),
            'categoria_nao_normativa': clean_val(row.get('Non-Normative Category')),
            'familiaridade_media': clean_val(row.get('Familiarity Mean')),
            'familiaridade_dp': clean_val(row.get('Familiarity StDev')),
            'complexidade_visual_media': clean_val(row.get('Visual Complexity Mean')),
            'complexidade_visual_dp': clean_val(row.get('Visual Complexity StDev')),
            'concordancia_objeto_media': clean_val(row.get('Object Agreement Mean')),
            'concordancia_objeto_dp': clean_val(row.get('Object Agreement StDev')),
            'concordancia_angulo_media': clean_val(row.get('Viewpoint Agreement Mean')),
            'concordancia_angulo_dp': clean_val(row.get('Viewpoint Agreement StDev')),
            'manipulabilidade_media': clean_val(row.get('Manipulability Mean')),
            'manipulabilidade_dp': clean_val(row.get('Manipulability StDev')),
            'selection_score': clean_val(row.get('Score')),
            'url_imagem': f"{project_url}/storage/v1/object/public/boss-images/{filename}.webp"
        }
        records.append(record)
    
    url = f"{project_url}/rest/v1/{table_name}"
    
    # Fazer inserção em lotes (batch) para evitar timeouts ou payloads muito grandes
    batch_size = 50
    print(f"Iniciando inserção de {len(records)} registros...")
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        response = requests.post(url, headers=_headers(), json=batch)
        if response.status_code in (200, 201, 204):
            print(f"  ✓ Inseridos {min(i+batch_size, len(records))}/{len(records)} registros.")
        else:
            print(f"  ✗ Erro ao inserir lote: {response.status_code} - {response.text}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Insere métricas das imagens (BOSS) no banco de dados do Supabase.")
    parser.add_argument("--csv", required=True, help="Caminho do arquivo CSV contendo as métricas (ex: output/boss_selecionadas_160.csv)")
    parser.add_argument("--table", default="estimulos", help="Nome da tabela destino no Supabase (padrão: estimulos)")
    parser.add_argument("--action", choices=["append", "replace"], default="replace", help="Ação a ser tomada: 'replace' apaga os dados antigos antes de inserir, 'append' apenas adiciona")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.csv):
        print(f"Erro: Arquivo não encontrado: {args.csv}")
        print("Você precisa primeiro rodar o pipeline para gerar este arquivo.")
    else:
        if args.action == "replace":
            clear_table(args.table)
            
        upload_csv(args.csv, args.table)
        print("\nSincronização com o banco de dados finalizada com sucesso!")
