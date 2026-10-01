# RESPOSTAS.md — ICEIBank Sprint 1

## Parte B — Seção 6.4: Perguntas sobre o Relógio de Lamport

### Pergunta 1
**Por que `max(contador_local, timestamp_recebido) + 1` ao invés de adotar o timestamp recebido diretamente?**

Adotar o timestamp recebido diretamente (`contador = timestamp_recebido`) seria incorreto por dois motivos:

1. **Preservar eventos locais:** Se a agência local já está em um contador maior que o timestamp recebido, descartar o valor local apagaria a memória dos eventos que já aconteceram neste processo. Por isso usamos `max(local, recebido)` — garantimos que o novo contador seja pelo menos tão grande quanto o maior evento já observado, seja local ou remoto.

2. **O recebimento é um evento:** O `+1` é obrigatório porque o próprio ato de receber a mensagem é um evento que deve ter um timestamp **estritamente maior** do que todos os eventos que causaram o envio da mensagem. Se simplesmente adotarmos `max(local, recebido)` sem o `+1`, o recebimento poderia ter o mesmo timestamp que o envio. O `+1` garante a propriedade fundamental do Lamport: se o evento A causou o evento B, então `ts(A) < ts(B)`.

Em resumo: `max` garante que nenhum evento passado seja esquecido; `+1` garante que o recebimento seja logicamente posterior ao envio.

### Pergunta 2
**Se a Agência 0 está no contador 10 e recebe uma mensagem com timestamp 3, qual o novo valor?**

Novo valor: `max(10, 3) + 1 = 11`

A Agência 0 estava "na frente" (contador 10) enquanto a mensagem vinha de uma agência "atrasada" (timestamp 3). O resultado é que o contador local apenas avança em 1.

**Implicação:** o Relógio de Lamport não mede tempo real — mede causalidade. Uma agência que processa muitos eventos rapidamente terá um contador alto. Quando recebe uma mensagem antiga (timestamp baixo), simplesmente ignora esse valor e continua de onde estava. Já uma agência lenta que recebe uma mensagem de uma agência rápida "salta" seu contador para refletir que ela agora conhece eventos mais avançados. A regra `max + 1` garante que, após a comunicação, ambas as agências têm um contador que reflete o conhecimento combinado dos eventos de ambas.

---

## Parte D — Seção 8.3: Perguntas sobre Transferências

### Pergunta 1
**Por que a transferência local não usa `ao_enviar()`/`ao_receber()`, enquanto a entre agências usa?**

A transferência local acontece inteiramente dentro de um único processo (a agência). Não há troca de mensagens entre processos distintos — débito e crédito são dois eventos locais no mesmo processo, e o relógio avança normalmente com `evento_local()` em cada um.

A transferência entre agências envolve dois processos distintos (duas agências). A mensagem enviada de uma para outra é exatamente o cenário que o Relógio de Lamport foi projetado para tratar: `ao_enviar()` incrementa o relógio e anexa o timestamp à mensagem; `ao_receber(ts)` garante que a agência de destino atualize seu contador para refletir o conhecimento causal da mensagem recebida. Sem isso, eventos na agência de destino poderiam receber timestamps menores que o evento de envio, quebrando a ordenação causal.

### Pergunta 2
**O saldo da conta de origem foi revertido após a falha? O que isso significa?**

Não, o saldo não foi revertido. O débito foi aplicado antes da tentativa de chamada REST. Quando a chamada falhou (agência de destino fora do ar), o dinheiro "sumiu" — saiu da conta de origem mas nunca chegou à conta de destino.

Isso significa que o sistema está **temporariamente inconsistente**: a soma dos saldos de todas as contas diminuiu sem que nenhuma transação completa tenha ocorrido. Em um banco real, isso seria inaceitável. O log registra `TRANSFERENCIA_FALHOU`, documentando a inconsistência, mas não há correção automática neste sprint.

### Pergunta 3
**Duas formas de corrigir o problema no Sprint 4:**

1. **Two-Phase Commit (2PC):** antes de debitar, a agência coordenadora pergunta a todas as participantes "você consegue creditar?" (fase prepare). Só aplica o débito quando todas confirmam (fase commit). Se alguma falhar, envia abort para todas. Garante atomicidade, mas bloqueia recursos durante a coordenação.

2. **Saga com compensação:** debita e registra uma "transação pendente". Um serviço de saga tenta o crédito remotamente; se falhar, executa uma transação compensatória (credita de volta na conta de origem). Não bloqueia recursos, mas é eventual — há uma janela de inconsistência temporária enquanto a saga não concluiu.

---

## Parte E — Seção 10.3: Perguntas sobre a Linha do Tempo

### Pergunta 1
**O que significa ver dois eventos com timestamps diferentes mas sem saber se um influenciou o outro?**

O Relógio de Lamport garante apenas: se A causou B, então ts(A) < ts(B). Mas **não** garante a volta: ts(A) < ts(B) não implica que A causou B. Ao ver dois eventos com timestamps diferentes na linha do tempo, sabemos que um veio "antes" logicamente — mas isso pode ter sido apenas coincidência de contadores, não uma relação causal real. Os eventos podem ter sido concorrentes (independentes), e o timestamp menor ser resultado de um processo simplesmente mais lento naquele momento.

Na prática: não dá para determinar com certeza se A influenciou B olhando só para timestamps de Lamport diferentes.

### Pergunta 2
**O Lamport sozinho seria suficiente para distinguir concorrência de causalidade? Por que isso motiva o relógio vetorial?**

Não. O Lamport consegue detectar causalidade em um sentido (se ts(A) >= ts(B), A definitivamente não causou B), mas não consegue confirmar com certeza que A causou B quando ts(A) < ts(B) — pode ser coincidência.

O Relógio Vetorial resolve isso: cada processo mantém um vetor com o último timestamp conhecido de todos os processos. Com isso, é possível determinar com certeza quando dois eventos são concorrentes (nenhum dos dois vetores "domina" o outro) e quando um realmente aconteceu antes do outro (um vetor é component-wise menor ou igual ao outro). É exatamente essa limitação do Lamport que motiva o Sprint 2.

---

## Parte F — Seção 11.3: Perguntas sobre Autenticação JWT

### Decisões de design (documentação obrigatória)

**Formato de credenciais:** `idConta` + senha. Cada conta tem uma senha cadastrada no momento da criação (campo `senha` no corpo do POST /contas, padrão "1234"). Login via `POST /auth/login` com `{"idConta": N, "senha": "..."}`.

**Justificativa:** é o modelo mais simples compatível com o domínio — cada conta já é a unidade de negócio, então faz sentido a senha ser por conta.

**Expiração:** 30 minutos (configurável via variável de ambiente `JWT_EXP_MINUTOS`).

**Chamada `creditar-remoto` (máquina-a-máquina):** usa token de serviço (`sub="service"`) gerado no startup da agência, com validade de 1 ano. Justificativa: é uma chamada interna entre backends, não uma sessão de usuário humano. Usar um token de serviço separado é prática padrão em arquiteturas de microsserviços — evita que tokens de usuários precisem circular entre backends e permite revogar/rotacionar os tokens de serviço independentemente dos tokens de usuários.

### Pergunta 1
**Diferença entre autenticação e autorização. Qual a implementação verifica?**

- **Autenticação** (quem é você?): verificar se as credenciais são válidas. O JWT autentica.
- **Autorização** (o que você pode fazer?): verificar se o usuário autenticado tem permissão para aquela ação específica. Nossa implementação **não faz autorização** além da autenticação: qualquer usuário com um token válido pode consultar qualquer conta, sacar de qualquer conta, transferir de qualquer conta. Um usuário autenticado com a conta 0 consegue sacar da conta 3. Isso seria um bug de segurança em produção — uma implementação completa verificaria se `payload["idConta"] == id_conta_operada`.

### Pergunta 2
**Por que o servidor não precisa de banco de dados para validar JWT?**

O JWT é assinado digitalmente com `SECRET_KEY`. Para validar, o servidor apenas re-calcula a assinatura do token recebido e compara com a assinatura que veio no token — se baterem, o token é válido. Toda a informação necessária (quem, quando expira) está dentro do próprio token. Não é necessário consultar nenhuma sessão armazenada.

Implicação de escalabilidade: com sessões em memória, qualquer requisição deve ir para o servidor que criou aquela sessão (ou todos os servidores precisam compartilhar o estado de sessão). Com JWT, qualquer instância do servidor pode validar qualquer token — o sistema pode escalar horizontalmente adicionando servidores sem coordenação de estado.

### Pergunta 3
**O que aconteceria se a chave secreta vazasse?**

Um atacante poderia assinar seus próprios tokens com qualquer payload que quisesse — por exemplo, `{"idConta": 0}` — e a API aceitaria como legítimo. Todos os tokens existentes teriam que ser invalidados imediatamente (o que com JWT é difícil, pois o servidor é stateless — uma lista negra seria necessária). A única solução é trocar a `SECRET_KEY` imediatamente (invalida todos os tokens) e investigar o vazamento.

---

## Parte G — Seção 12.3: Perguntas sobre o Frontend

### Pergunta 1
**Como o frontend "lembra" de reenviar o token?**

O token é salvo em `localStorage` após o login (`setToken(data.token)` em `api.js`). A função `request()` em `api.js` lê o token do `localStorage` a cada chamada e injeta automaticamente o header `Authorization: Bearer <token>`. Não é necessário passar o token explicitamente de componente em componente — qualquer chamada via `api.js` já inclui o token.

### Pergunta 2
**O que acontece se o token expirar durante o uso?**

A próxima requisição retorna 401. O `request()` em `api.js` detecta o 401, remove o token do `localStorage` com `clearToken()`, e lança um erro. O `useAuth.js` detecta a remoção via evento `storage` e atualiza `estaLogado` para `false` — a tela de login é exibida automaticamente com a mensagem "Não autorizado. Faça login novamente." O usuário vê o erro claramente, não apenas uma falha silenciosa.

### Pergunta 3
**Onde fica o M, V e C no frontend React?**

- **Model (M):** `src/services/api.js` — todas as chamadas à API, regras de persistência do token e da URL da agência. Não tem estado visual, só dados e comunicação.
- **View (V):** `src/components/*.jsx` — cada componente renderiza apenas o que o usuário vê. Recebem dados via props/estado e chamam funções do Model.
- **Controller (C):** `src/hooks/useAuth.js` e a lógica de estado em `App.jsx` — coordenam as interações do usuário, chamam o Model e atualizam o estado que alimenta as Views. O hook `useAuth.js` é o controller mais explícito: gerencia login, logout e o estado de autenticação.

A separação ficou razoavelmente clara, especialmente para `api.js` (Model) e os componentes (View). A parte de Controller ficou distribuída entre o hook e o App, o que é idiomático em React mas menos explícito do que um Controller tradicional da arquitetura MVC clássica.

---

## Funcionalidade Adicional — Health-check por Agência

**O que faz:** `GET /status` retorna o estado atual de uma agência: seu ID, o valor atual do relógio de Lamport e a quantidade de contas sob sua responsabilidade.

**Exemplo de resposta:**
```json
{"agencia": 0, "relogioLamportAtual": 42, "quantidadeContas": 3}
```

**Por que foi escolhida:** é a funcionalidade de menor complexidade da lista do roteiro, mas com alto valor prático — em sistemas reais, health-checks são usados por load balancers e dashboards de monitoramento para verificar se um serviço está operacional. No contexto do ICEIBank, também serve para observar o avanço do relógio de Lamport sem precisar abrir o arquivo `.jsonl`.

**Por que não exige JWT:** health-checks são endpoints de infraestrutura, geralmente públicos. Não expõem dados sensíveis de nenhuma conta específica — apenas métricas agregadas de operação da agência.

**Evidência:** `evidencias/sprint1/funcionalidade-adicional.png`

---

# RESPOSTAS Sprint 2 - ICEIBank

## Secao 6.4 - Perguntas sobre RabbitMQ e Mensageria

### Pergunta 1
**Por que usamos uma exchange do tipo "topic" em vez de "direct" ou "fanout"?**

A exchange "direct" roteia mensagens para uma fila especifica por chave exata - nao tem flexibilidade
para padroes. A "fanout" manda para TODAS as filas ligadas - nao serve para direcionar a credito para
uma agencia especifica.

O tipo "topic" permite routing keys com padroes (wildcards). Usamos:
  - "agencia.0.creditar"            -> fila-agencia-0 so recebe creditos para ela
  - "agencia.0.alerta-saldo-baixo"  -> poderia ter consumidor dedicado para alertas

Isso permite usar UMA UNICA exchange para todos os tipos de mensagem (creditos e alertas),
separando os consumidores por routing key. E exatamente o padrao Publish/Subscribe.

### Pergunta 2
**O que significa durable=True na fila e delivery_mode=2 na mensagem? Por que sao importantes?**

  - durable=True na fila: a fila sobrevive a um reinicio do RabbitMQ. Se o broker reiniciar,
    a fila ainda existe e as mensagens persistidas continuam la.

  - delivery_mode=2 na mensagem (PERSISTENT): a mensagem e gravada em disco pelo RabbitMQ
    antes de confirmar o recebimento. Se o broker cair antes de entregar, a mensagem nao some.

Sem essas configuracoes: uma queda do RabbitMQ perderia filas e mensagens.
Com elas: o sistema resiste a falhas do broker.

### Pergunta 3
**O que acontece com uma mensagem se a agencia de destino estiver fora do ar no momento da transferencia?**

A mensagem e publicada na exchange e fica retida na fila duravel da agencia de destino.
O RabbitMQ a guarda ate que o consumidor se conecte.

Quando a agencia volta a funcionar, o consumidor conecta e processa a mensagem automaticamente.
A transferencia e entregue sem nenhuma intervencao manual.

Porem: se a agencia REINICIOU (nao apenas ficou fora do ar), o estado em memoria foi zerado.
Quando o consumidor processa a mensagem, a conta nao existe mais. Nesse caso, o sistema
registra CREDITO_REMOTO_FALHOU no log. A mensagem NAO se perdeu - o problema e a falta de
persistencia dos dados (assunto do Sprint 4).

---

## Secao 7.5 - Perguntas sobre Resiliencia

### Pergunta 1
**No teste de resiliencia, a mensagem se perdeu quando a Agencia 1 ficou fora do ar?**

Nao. A mensagem ficou na fila duravel do RabbitMQ durante todo o tempo que a Agencia 1 esteve
fora do ar. Quando ela voltou, o consumidor processou a mensagem imediatamente.

Isso e a vantagem central da mensageria assincrona sobre a chamada REST direta do Sprint 1:
no Sprint 1, se o destino estivesse fora do ar, a chamada HTTP falhava e o debito ficava
pendurado. No Sprint 2, a mensagem fica na fila ate ser entregue.

### Pergunta 2
**O que aconteceu quando a Agencia 1 reiniciou (nao apenas ficou fora do ar)?**

O estado em memoria foi zerado - as contas nao existem mais. Quando o consumidor processou
a mensagem da fila, a conta de destino nao foi encontrada. O sistema registrou:
  CREDITO_REMOTO_FALHOU, motivo: "conta nao encontrada"

O log mostrou: [Consumidor] ATENCAO: conta 1 nao encontrada - credito nao aplicado!

Isso demonstra a limitacao conhecida do Sprint 2: a mensageria e duravel, mas a persistencia
dos dados nao existe ainda (Sprint 4). A inconsistencia nao e da fila - e da falta de banco.

### Pergunta 3
**Como garantir consistencia mesmo com reinicio da agencia de destino?**

Opcao 1 - Banco de dados persistente: as contas ficam em banco (Sprint 4). Ao reiniciar,
a agencia releia o estado do banco e as contas existem antes do consumidor processar as filas.

Opcao 2 - Reconhecimento (ack) manual: o consumidor so confirma a mensagem ao RabbitMQ DEPOIS
de ter aplicado o credito com sucesso. Se falhar, a mensagem volta para a fila. Porem sem
banco de dados, a conta simplesmente nao existe apos reinicio - o ack nao resolve isso.

A solucao real exige as duas coisas: banco de dados + ack manual.

---

## Secao 8.3 - Perguntas sobre Linha do Tempo Causal (Relogio Vetorial)

### Pergunta 1
**O que exatamente no relogio vetorial torna possivel a comparacao confiavel de concorrencia?**

O Relogio de Lamport usa um UNICO numero. Dados dois timestamps diferentes, A=5 e B=7,
sabemos que 5 < 7... mas nao sabemos se A causou B, ou se foram eventos independentes em
agencias diferentes que so tiveram numeros diferentes por acaso.

O Relogio Vetorial mantem um VETOR com um contador por agencia. Cada mensagem carrega o
vetor inteiro. Quando uma agencia recebe uma mensagem, ela sabe exatamente quantos eventos
CADA OUTRA agencia havia feito no momento do envio.

Com dois vetores V1 e V2:
  - Se V1[i] <= V2[i] para todo i: V1 aconteceu ANTES de V2 com CERTEZA.
    (V2 "conhecia" tudo que V1 havia registrado)
  - Se nenhum domina o outro: sao CONCORRENTES com CERTEZA.
    (nenhum dos dois "conhecia" o estado completo do outro)

Essa certeza e impossivel com Lamport: ts(A) < ts(B) nao implica causalidade.
Com vetorial, V1 < V2 (componente a componente) IMPLICA causalidade.

### Pergunta 2
**Encontre um par concorrente no seu teste. Faz sentido que sejam concorrentes?**

Exemplo tipico: apos fazer depositos na Agencia 0 e saques na Agencia 2, sem nenhuma
transferencia entre elas, o script identifica pares como:

  [agencia-0] DEPOSITO ([2, 0, 0]) x [agencia-2] SAQUE ([0, 0, 1])

Faz total sentido: a Agencia 0 fez seu deposito sem saber NADA do que a Agencia 2 estava
fazendo (posicao 2 do vetor de Ag0 = 0 significa que ela nunca recebeu mensagem de Ag2).
Da mesma forma, Ag2 nao sabia nada de Ag0 (posicao 0 do vetor de Ag2 = 0).

Eles realmente nao tem relacao de causa e efeito: sao operacoes em contas diferentes,
em agencias diferentes, sem comunicacao entre si naquele momento.

### Pergunta 3
**O algoritmo O(n^2) seria problema em producao? Como tornar mais escalavel?**

Sim. Com 1 milhao de eventos, seriam 500 bilhoes de comparacoes - impraticavel.

Alternativas mais escalaveis:

1. Analise incremental: ao registrar cada evento, comparar APENAS com os eventos recentes
   (janela de tempo), nao com todos os eventos historicos. A grande maioria dos pares
   concorrentes esta proxima no tempo.

2. Indice por agencia: em vez de comparar todos x todos, manter o "ultimo vetor visto"
   de cada agencia e comparar so os vetores que realmente podem conflitar (quando um
   componente de uma agencia nao aparece no vetor de outra).

3. Analise distribuida: cada agencia detecta concorrencia localmente ao receber mensagens.
   Quando ao_receber() detecta que o vetor recebido tem componentes que a agencia local
   nunca viu, pode-se registrar o evento como potencialmente concorrente com eventos locais
   que aconteceram desde o ultimo recebimento daquela agencia.

4. Ferramentas de stream processing (Kafka Streams, Apache Flink): processam eventos em
   paralelo com janelas de tempo, tornando a comparacao O(n log n) em vez de O(n^2).

---

## Funcionalidade Adicional Sprint 2 - Notificacao de Saldo Baixo

**O que faz:** apos cada deposito ou saque, se o saldo da conta ficar abaixo de R$ 50,00
(LIMITE_SALDO_BAIXO definido em contas_controller.py), a agencia publica automaticamente
um evento de alerta na exchange do RabbitMQ com a routing key:
  agencia.{id}.alerta-saldo-baixo

**Payload da mensagem:**
  {"tipo": "ALERTA_SALDO_BAIXO", "idConta": 0, "saldoAtual": 20.0, "limite": 50.0}

**Por que foi escolhida:** demonstra o uso de topicos separados na mesma exchange topic.
A mesma infraestrutura de mensageria usada para creditos tambem serve para notificacoes,
sem criar uma nova exchange. Em producao, um servico de notificacoes poderia assinar
"agencia.*.alerta-saldo-baixo" e disparar SMS/email para o cliente.

**Implementacao:** _verificar_saldo_baixo() em contas_controller.py, chamada apos
depositar() e sacar(). Usa publicar() do mensageria.py - nao bloqueia a resposta HTTP.

**Por que nao exige consumidor dedicado:** o objetivo e demonstrar a publicacao. O
CloudAMQP Manager confirma que a mensagem chega na exchange com a routing key correta.
