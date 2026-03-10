# -*- coding: utf-8 -*-
"""
setup_dynamodb_local.py — Cria a tabela DynamoDB no emulador local.

Pré-requisito:
    docker compose --profile dynamodb up -d   (na pasta deployment/)

Uso:
    python scripts/setup_dynamodb_local.py [--endpoint http://localhost:8001]

A tabela criada espelha exatamente o esquema esperado por DynamoDBBackend:
  - Partition Key : session_id (String)
  - TTL attribute : expires_at (Number)
  - GSI           : TimestampIndex (timestamp / session_id) para list_recent()
"""
import argparse
import sys
from datetime import datetime, timezone

# Verificação antecipada antes de qualquer import pesado
try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("[ERRO] boto3 não encontrado. Execute:  pip install boto3")
    sys.exit(1)

TABLE_NAME = "agente-macro-conversations"


def create_table(dynamodb, table_name: str) -> None:
    """Cria a tabela se ainda não existir."""
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {"AttributeName": "session_id", "KeyType": "HASH"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "session_id",  "AttributeType": "S"},
                {"AttributeName": "entity_type", "AttributeType": "S"},
                {"AttributeName": "timestamp",   "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    # Padrão de acesso: listar N conversas mais recentes.
                    # entity_type (HASH fixo="conversation") + timestamp (RANGE)
                    # → Query com ScanIndexForward=False retorna mais recentes sem scan.
                    "IndexName": "RecentConversationsIndex",
                    "KeySchema": [
                        {"AttributeName": "entity_type", "KeyType": "HASH"},
                        {"AttributeName": "timestamp",   "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
                }
            ],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        )
        table.wait_until_exists()
        print(f"[OK]   Tabela '{table_name}' criada com sucesso.")

        # Ativa TTL
        dynamodb.meta.client.update_time_to_live(
            TableName=table_name,
            TimeToLiveSpecification={"Enabled": True, "AttributeName": "expires_at"},
        )
        print("[OK]   TTL ativado no atributo 'expires_at'.")

    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ResourceInUseException":
            print(f"[INFO] Tabela '{table_name}' já existe — pulando criação.")
        else:
            raise


def seed_test_record(table) -> None:
    """Insere um registro de teste para confirmar leitura/escrita."""
    item = {
        "session_id": "test-setup-001",
        "entity_type": "conversation",   # obrigatório para o GSI RecentConversationsIndex
        "question": "Teste de setup local",
        "response": "DynamoDB Local funcionando corretamente.",
        "has_data": False,
        "has_plot": False,
        "error": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "expires_at": 9999999999,   # nunca expira (número Unix timestamp alto)
    }
    table.put_item(Item=item)
    print("[OK]   Registro de teste inserido | session_id=test-setup-001")


def read_test_record(table) -> None:
    """Lê o registro de teste para confirmar a persistência."""
    resp = table.get_item(Key={"session_id": "test-setup-001"})
    item = resp.get("Item")
    if item:
        print(f"[OK]   Leitura OK | question='{item['question']}'")
    else:
        print("[ERRO] Leitura falhou — registro não encontrado.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Setup DynamoDB Local para desenvolvimento.")
    parser.add_argument(
        "--endpoint",
        default="http://localhost:8001",
        help="URL do DynamoDB Local (padrão: http://localhost:8001)",
    )
    parser.add_argument(
        "--table",
        default=TABLE_NAME,
        help=f"Nome da tabela (padrão: {TABLE_NAME})",
    )
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  Agente Macro-BR — Setup DynamoDB Local")
    print(f"  Endpoint : {args.endpoint}")
    print(f"  Tabela   : {args.table}")
    print(f"{'='*60}\n")

    dynamodb = boto3.resource(
        "dynamodb",
        region_name="us-east-1",
        endpoint_url=args.endpoint,
        aws_access_key_id="fakeMyKeyId",        # DynamoDB Local ignora credenciais
        aws_secret_access_key="fakeSecretKey",  # mas boto3 exige que sejam fornecidas
    )

    # Cria tabela
    create_table(dynamodb, args.table)

    # Testa escrita/leitura
    table = dynamodb.Table(args.table)
    seed_test_record(table)
    read_test_record(table)

    # Lista tabelas criadas
    client = dynamodb.meta.client
    tables = client.list_tables()["TableNames"]
    print(f"\n[OK]   Tabelas disponíveis no emulador: {tables}")
    print("\n[PRONTO] DynamoDB Local configurado.\n")
    print("Para usar na API, adicione ao .env:")
    print("  STORAGE_BACKEND=dynamodb")
    print(f"  DYNAMODB_ENDPOINT_URL={args.endpoint}")
    print("  AWS_REGION=us-east-1\n")


if __name__ == "__main__":
    main()
