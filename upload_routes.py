# upload_routes.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import boto3
from uuid import uuid4
import certifi  # usamos pra validar SSL de forma correta

# vamos manter o mesmo padrão das suas outras rotas
router = APIRouter(prefix="/upload", tags=["Upload"])

# =========================================================
# CONFIGURAÇÃO BACKBLAZE B2 (S3 compatível)
# Aqui você já colocou direto no código, vou manter assim.
# =========================================================
B2_KEY_ID = "00462489b1467b00000000001"            # <- application key ID
B2_APP_KEY = "K004LwBpIMCWwyq3E500WtNa5FJEd70"     # <- application key (secret)
B2_BUCKET_NAME = "tracking-saidas-pictures"        # <- nome do bucket
B2_ENDPOINT = "https://s3.us-west-004.backblazeb2.com"  # <- endpoint S3 da sua região
B2_REGION = "us-west-004"                          # <- só a região

# cria o client S3 apontando para o Backblaze
# (se no seu Windows der aquele erro de certificado, você pode trocar
# verify=certifi.where() por verify=False só no ambiente local)
s3_client = boto3.client(
    "s3",
    endpoint_url=B2_ENDPOINT,
    aws_access_key_id=B2_KEY_ID,
    aws_secret_access_key=B2_APP_KEY,
    region_name=B2_REGION,
    verify=certifi.where(),
)

# =========================================================
# MODELOS DE ENTRADA
# =========================================================
class PresignRequest(BaseModel):
    """
    O front vai mandar algo assim:
    {
      "filename": "foto.jpg",
      "encomenda_id": "BR1230849"
    }
    """
    filename: str
    encomenda_id: str | None = None


class RegistrarFoto(BaseModel):
    """
    Opcional: depois que o front subir direto pro B2,
    ele pode te avisar qual encomenda ficou com qual URL.
    """
    encomenda_id: str
    url: str
    key: str | None = None


# =========================================================
# 1) ROTA QUE GERA A URL DE UPLOAD (presigned URL)
# =========================================================
@router.post("/presign")
def gerar_url_upload(dados: PresignRequest):
    """
    Gera uma URL PRÉ-ASSINADA para o front fazer upload direto no Backblaze.
    Essa rota NÃO recebe arquivo. Ela só diz:
    - "pode subir aqui"
    - "o caminho vai ser esse"
    - "vale por X segundos"
    """
    # tenta descobrir a extensão a partir do nome que o front mandou
    if "." in dados.filename:
        ext = dados.filename.split(".")[-1]
    else:
        ext = "bin"

    # monta o caminho dentro do bucket
    # se veio encomenda_id, vamos colocar numa pasta por encomenda
    if dados.encomenda_id:
        key = f"encomendas/{dados.encomenda_id}/{uuid4()}.{ext}"
    else:
        key = f"uploads/{uuid4()}.{ext}"

    try:
        # gera uma URL de PUT válida por 5 minutos (300s)
        presigned_url = s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": B2_BUCKET_NAME,
                "Key": key,
            },
            ExpiresIn=300,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar URL: {e}")

    # essa é a URL que, em bucket público, abre direto a imagem
    final_url = f"{B2_ENDPOINT}/{B2_BUCKET_NAME}/{key}"

    return {
        "upload_url": presigned_url,  # o front faz PUT aqui
        "final_url": final_url,       # o front pode salvar no back depois
        "key": key,                   # caminho interno no bucket
        "expires_in": 300,
    }


# =========================================================
# 2) (OPCIONAL) ROTA PARA REGISTRAR A FOTO NO SEU BANCO
# =========================================================
@router.post("/registrar")
def registrar_foto(dados: RegistrarFoto):
    """
    Aqui você faria o insert no Postgres ligando:
    encomenda_id -> url -> key
    Por enquanto vou só devolver o que recebi.
    """
    # Exemplo do que você faria aqui:
    # foto = EncomendaFoto(
    #     encomenda_id=dados.encomenda_id,
    #     caminho=dados.key,
    #     url_publica=dados.url,
    # )
    # db.add(foto); db.commit()
    return {
        "ok": True,
        "encomenda_id": dados.encomenda_id,
        "url": dados.url,
        "key": dados.key,
        "msg": "Foto registrada (simulação)",
    }
