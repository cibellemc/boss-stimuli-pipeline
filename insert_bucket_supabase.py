import os
import requests
from dotenv import load_dotenv
import argparse

load_dotenv()

# ---------------------------------------------------------------------------
# Configuração — ajuste estes valores para o seu ambiente
# ---------------------------------------------------------------------------

# Lidos do .env (não editar aqui; editar o arquivo .env)
project_url = os.getenv('SUPABASE_URL')   # ex.: https://xyzabc.supabase.co
anon_key    = os.getenv('SUPABASE_ANON_KEY')

# Nome do bucket no Supabase Storage (será criado automaticamente se não existir)
bucket_name = 'boss-images'

# ---------------------------------------------------------------------------

def _headers(content_type='application/json'):
    return {
        'Authorization': f'Bearer {anon_key}',
        'apikey': anon_key,
        'Content-Type': content_type,
    }

def ensure_bucket_exists():
    """Cria o bucket caso ainda não exista no Supabase Storage."""
    list_url   = f"{project_url}/storage/v1/bucket"
    create_url = f"{project_url}/storage/v1/bucket"

    response = requests.get(list_url, headers=_headers())
    if response.status_code != 200:
        print(f"Erro ao listar buckets: {response.status_code} - {response.text}")
        return

    existing = [b['name'] for b in response.json()]
    if bucket_name in existing:
        print(f"Bucket '{bucket_name}' já existe.")
        return

    payload  = {"id": bucket_name, "name": bucket_name, "public": False}
    response = requests.post(create_url, headers=_headers(), json=payload)
    if response.status_code in (200, 201):
        print(f"Bucket '{bucket_name}' criado com sucesso.")
    else:
        print(f"Erro ao criar bucket: {response.status_code} - {response.text}")


def upload_files(source_dir):
    ensure_bucket_exists()

    if not os.path.exists(source_dir):
        print(f"Directory {source_dir} does not exist.")
        return

    files = [f for f in os.listdir(source_dir) if f.endswith('.webp')]
    print(f"\nIniciando upload de {len(files)} arquivos para '{bucket_name}'...")

    for filename in files:
        file_path  = os.path.join(source_dir, filename)
        upload_url = f"{project_url}/storage/v1/object/{bucket_name}/{filename}"

        try:
            with open(file_path, 'rb') as f:
                response = requests.post(
                    upload_url,
                    headers=_headers('image/webp'),
                    data=f,
                )

            if response.status_code in (200, 201):
                print(f"  ✓ {filename}")
            elif response.status_code == 409 or (response.status_code == 400 and 'Duplicate' in response.text):
                print(f"  — {filename} (já existe, pulando)")
            else:
                print(f"  ✗ {filename}: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"  ✗ Erro em {filename}: {e}")

    print("\nUpload concluído.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Faz o upload (insert) de imagens WebP para um bucket no Supabase Storage.")
    parser.add_argument("--dir", required=True, help="Diretório contendo as imagens WebP para upload")
    args = parser.parse_args()

    upload_files(args.dir)
