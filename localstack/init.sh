#!/bin/sh
# Cria, dentro do LocalStack, os recursos "AWS" do ICEIBank (Sprint 4, Parte F).
# Rode UMA vez a cada vez que o LocalStack subir (ele nao guarda estado entre
# reinicios):  docker compose exec localstack sh /scripts/init.sh
set -e
CONTA=000000000000
REGIAO=us-east-1

echo "Criando tópico SNS, fila SQS e a inscrição entre eles..."
awslocal sns create-topic --name iceibank-transferencias-concluidas
awslocal sqs create-queue --queue-name comprovantes
awslocal sns subscribe \
  --topic-arn arn:aws:sns:$REGIAO:$CONTA:iceibank-transferencias-concluidas \
  --protocol sqs \
  --notification-endpoint arn:aws:sqs:$REGIAO:$CONTA:comprovantes \
  --attributes RawMessageDelivery=true

echo "Criando bucket S3 e tabela DynamoDB..."
awslocal s3 mb s3://iceibank-comprovantes || true
awslocal dynamodb create-table \
  --table-name comprovantes \
  --attribute-definitions AttributeName=txId,AttributeType=S \
  --key-schema AttributeName=txId,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST || true

echo "Criando o papel (IAM) e a função Lambda gerar-comprovante, e ligando a fila a ela..."
awslocal iam create-role \
  --role-name lambda-role \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}' || true
awslocal lambda create-function \
  --function-name gerar-comprovante \
  --runtime python3.12 \
  --handler index.handler \
  --role arn:aws:iam::$CONTA:role/lambda-role \
  --zip-file fileb:///serverless/gerar-comprovante.zip \
  --environment "Variables={BUCKET=iceibank-comprovantes,TABELA=comprovantes}"
awslocal lambda create-event-source-mapping \
  --function-name gerar-comprovante \
  --event-source-arn arn:aws:sqs:$REGIAO:$CONTA:comprovantes \
  --batch-size 5 \
  --function-response-types ReportBatchItemFailures

echo "Criando a segunda função Lambda (consultar-comprovante) e o API Gateway..."
awslocal lambda create-function \
  --function-name consultar-comprovante \
  --runtime python3.12 \
  --handler index.handler \
  --role arn:aws:iam::$CONTA:role/lambda-role \
  --zip-file fileb:///serverless/consultar-comprovante.zip \
  --environment "Variables={BUCKET=iceibank-comprovantes,TABELA=comprovantes}"

API_ID=$(awslocal apigateway create-rest-api --name iceibank-comprovantes-api --tags '{"_custom_id_":"comprovantesapi"}' --query 'id' --output text)
ROOT_ID=$(awslocal apigateway get-resources --rest-api-id "$API_ID" --query 'items[0].id' --output text)
COMP_ID=$(awslocal apigateway create-resource --rest-api-id "$API_ID" --parent-id "$ROOT_ID" --path-part comprovantes --query 'id' --output text)
TX_ID_RES=$(awslocal apigateway create-resource --rest-api-id "$API_ID" --parent-id "$COMP_ID" --path-part "{txId}" --query 'id' --output text)

awslocal apigateway put-method \
  --rest-api-id "$API_ID" \
  --resource-id "$TX_ID_RES" \
  --http-method GET \
  --authorization-type "NONE"

awslocal apigateway put-integration \
  --rest-api-id "$API_ID" \
  --resource-id "$TX_ID_RES" \
  --http-method GET \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri "arn:aws:apigateway:$REGIAO:lambda:path/2015-03-31/functions/arn:aws:lambda:$REGIAO:$CONTA:function:consultar-comprovante/invocations"

awslocal apigateway create-deployment \
  --rest-api-id "$API_ID" \
  --stage-name prod

echo "Pronto. API Gateway disponivel em:"
echo "  http://localhost:4566/restapis/$API_ID/prod/_user_request_/comprovantes/<txId>"