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

---

# RESPOSTAS Sprint 3 - ICEIBank

## Secao 5.5 - Perguntas sobre Eleicao e Coordenador (Algoritmo de Bully)

### Pergunta 1
**Por que o algoritmo de Bully sempre elege o processo de maior ID, e nao o de menor? O resultado seria diferente (mas ainda assim correto) se a regra fosse invertida?**

A escolha do "maior ID" e uma convencao arbitraria: o que o algoritmo de Bully exige e uma
ordem total deterministica e estrita entre os identificadores dos processos (0 < 1 < 2),
de modo que qualquer subconjunto nao vazio de agencias ativas tenha um unico elemento vencedor
sem ambiguidade. O nome "Bully" ("valentao") vem exatamente da metafora de que o processo de
maior numero "intimida" os menores e assume a lideranca.

Se a regra fosse invertida (eleger sempre o MENOR ID ativo, enviando mensagens de eleicao
apenas para agencias com ID menor que o seu), o algoritmo continuaria 100% correto: todas as
propriedades de seguranca (unicidade da lider apos convergencia) e vivacidade (eventual eleicao
de uma lider ativa) seriam preservadas. O resultado prático seria diferente apenas em QUEM
vence (com todas as 3 ativas, a Agencia 0 seria a lider em vez da Agencia 2), mas o consenso
funcionaria da mesma forma.

### Pergunta 2
**Mais de uma agencia declarou TORNOU_LIDER durante a subida. Isso e um bug ou comportamento esperado?**

E comportamento esperado do algoritmo, nao um bug. Nos logs da minha execucao (horarios UTC,
agencias subidas uma apos a outra, nesta ordem: 0, 1, 2):

  04:59:07  [agencia-0] ELEICAO_INICIADA
  04:59:12  [agencia-0] TORNOU_LIDER          <- ninguem maior respondeu (1 e 2 ainda nao estavam no ar)
  04:59:36  [agencia-1] ELEICAO_INICIADA
  04:59:38  [agencia-1] TORNOU_LIDER          <- a 2 ainda nao estava no ar
  04:59:38  [agencia-0] LIDER_ANUNCIADO  liderId=1
  04:59:49  [agencia-2] ELEICAO_INICIADA
  04:59:49  [agencia-2] TORNOU_LIDER          <- nao existe ID maior que 2
  04:59:50  [agencia-0] LIDER_ANUNCIADO  liderId=2
  04:59:51  [agencia-1] LIDER_ANUNCIADO  liderId=2

Foram tres TORNOU_LIDER (agencias 0, 1 e 2), e depois todas convergiram para a 2.

**Por que acontece:** o Bully so exige que a agencia espere resposta de agencias com ID MAIOR.
Quando a agencia 0 subiu, as agencias 1 e 2 nao responderam (fora do ar, ou ainda sem ouvir a porta),
entao, pela regra do algoritmo, ela concluiu corretamente que era a maior agencia ATIVA e se
declarou lider. Isso era verdade naquele momento. O mesmo vale para a agencia 1 minutos depois.
Nenhuma das duas tinha como saber que uma agencia maior estava prestes a subir.

**Por que converge:** quando a agencia 2 subiu, ela iniciou sua propria eleicao, nao encontrou ID
maior, virou lider e enviou /bully/coordenador para as outras. Ao receber esse anuncio
(LIDER_ANUNCIADO liderId=2), as agencias 0 e 1 sobrescreveram o lider anterior. Por isso a agencia 0
registrou dois anuncios (liderId=1 e depois liderId=2), e as tres terminaram concordando com
liderAtual = 2. Isso e a propriedade que o algoritmo garante: o resultado FINAL e sempre o maior ID
ativo; o que nao e garantido e a ausencia de liderancas transitorias durante a subida.

Em resumo: lideres transitorios sao um efeito colateral previsivel de agencias subindo em momentos
diferentes. Bug seria o estado final divergente (agencias discordando da lider), o que nao ocorreu
(as tres responderam liderAtual = 2 em /bully/lider).

### Pergunta 3
**O endpoint /bully/eleicao nao tem nenhuma autenticacao. Isso e um problema de seguranca real para este projeto? Por que, ou por que nao?**

Em um ambiente de producao real exposto na internet, SIM, seria uma vulnerabilidade grave:
  1. Negacao de servico (DoS) por tempestade de eleicoes: qualquer agente externo que descubra
     a URL pode enviar POST /bully/eleicao repetidamente, forcando a agencia a disparar eleicoes,
     incrementar o relogio vetorial sem parar (o que tambem causa falsos conflitos 409 no
     endpoint /sincronizar) e saturar a rede entre agencias.
  2. Falsificacao de coordenador (spoofing): como /bully/coordenador tambem nao tem autenticacao,
     um atacante poderia enviar {"liderId": 99, "vetorEnvio": [999,999,999]}, corrompendo tanto
     o ponteiro de lider quanto o relogio vetorial de todas as agencias.

No escopo academico deste Sprint 3, porem, o impacto e limitado por dois motivos:
  - As agencias rodam em rede local controlada (localhost) para fins didaticos.
  - A lider eleita neste sprint e puramente informativa (nenhuma transacao bancaria depende dela
    ainda; isso so muda no Sprint 4 com 2PC). Mesmo assim, em producao esses endpoints internos
    deveriam exigir o `token_servico` (JWT maquina-a-maquina que ja criamos no Sprint 1) ou
    mTLS/rede privada entre os nos do cluster.

---
## Secao 6.4 - Perguntas sobre Heartbeat e Failover

### Pergunta 1
**O que aconteceria se o intervalo do heartbeat fosse muito curto (100ms)? E muito longo (60s)?**

E um trade-off entre velocidade de deteccao e custo de rede/CPU.

Intervalo muito curto (100ms): cada agencia que nao e lider faz 10 GET /bully/lider por segundo
na lider. Com 3 agencias o custo ainda e pequeno, mas escala mal: com N agencias seriam
(N-1) x 10 requisicoes/s so de "estou vivo?", mesmo sem nenhuma operacao bancaria acontecendo.
Alem disso, o timeout de resposta (1s) e MAIOR que o intervalo: varias verificacoes ficariam
sobrepostas, e qualquer pequeno atraso ocasional de rede viraria um falso positivo
(LIDER_NAO_RESPONDEU), disparando eleicoes desnecessarias. A lider ficaria instavel sem estar
realmente fora do ar.

Intervalo muito longo (60s): quase nao ha custo de rede, mas o tempo de deteccao da queda pode
chegar a 60s (mais o timeout de 1s). Durante esse tempo as agencias seguem apontando para uma
lider morta e o sistema fica sem lider efetiva. No Sprint 4, quando a lider coordenar transacoes
(2PC), isso significaria transacoes travadas ou falhando por quase um minuto.

O valor padrao de 3s e um meio-termo: nos meus logs, a queda da lider foi detectada pelas duas
agencias restantes em cerca de 1s uma da outra (05:10:34 e 05:10:35) e a nova lider assumiu
em ~2s depois da deteccao (TORNOU_LIDER as 05:10:36).

### Pergunta 2
**A agencia que caiu e voltou "toma" a lideranca de volta. Isso e desejavel? Que problema pode causar?**

Pelo algoritmo de Bully e inevitavel (a regra e "maior ID ativo sempre vence"), mas nem sempre e
desejavel. Nos meus logs: a agencia 2 caiu, a agencia 1 virou lider (05:10:36) e funcionou
normalmente. Quando a 2 voltou (05:15:59), ela iniciou eleicao, nao achou ID maior, virou lider
e anunciou coordenador; as agencias 0 e 1 passaram a apontar para ela (05:16:00 e 05:16:02),
mesmo com a lider anterior (1) perfeitamente saudavel.

Problemas praticos em um sistema real:
  - Troca de lideranca no meio de uma operacao importante: se a agencia 1 estivesse coordenando
    uma transacao distribuida (2PC do Sprint 4), a lideranca mudaria no meio da transacao e a
    nova lider (a 2) nao conheceria o estado dela. A transacao ficaria incompleta ou duplicada.
  - Estado perdido: como o estado atual e so em memoria, a agencia que volta nao tem o historico
    do que a lider interina fez enquanto ela estava fora, e pode decidir com informacao velha.
  - Instabilidade: uma agencia que cai e volta repetidamente (flapping) causaria varias trocas de
    lideranca seguidas, cada uma com custo de eleicao e janela sem lider.

Alternativas usadas na pratica: so aceitar a troca quando a lider atual falhar de fato (como
Raft e ZooKeeper, onde lider so muda por falha) ou fazer a agencia que volta sincronizar o estado
antes de reivindicar a lideranca.

### Pergunta 3
**O que aconteceria se a rede estivesse lenta (resposta demorando mais que o TIMEOUT de 1s), sem a agencia estar fora do ar?**

O codigo nao consegue distinguir "agencia fora do ar" de "agencia lenta": as duas viram a mesma
excecao de timeout. Consequencias:

  - No heartbeat: uma lider viva mas lenta e declarada morta (falso positivo). A agencia registra
    LIDER_NAO_RESPONDEU, esquece a lider e inicia uma eleicao desnecessaria.
  - Na eleicao: se a agencia de ID maior responder depois de 1s, quem perguntou conclui que
    ninguem respondeu e se declara lider. Mas a requisicao CHEGOU na agencia maior, que tambem
    inicia a propria eleicao e se anuncia. Resultado: dois lideres ao mesmo tempo (split-brain)
    ate o anuncio da agencia de maior ID chegar. Uma agencia que acredita ser lider nao verifica
    ninguem no heartbeat (liderAtual == idAgencia), entao se esse anuncio se perder, ela pode
    continuar errada indefinidamente.
  - Na rede lenta, as eleicoes se repetem sem parar, gerando ainda mais trafego (efeito cascata).

Mitigacoes: timeout maior ou adaptativo, exigir varias falhas consecutivas antes de declarar a
lider morta, e (em sistemas reais) usar eleicao com "terms/epochs" para descartar lideres antigos.

---
## Secao 7.3 - Perguntas sobre Observabilidade da Eleicao (Historico de Lideranca)

### Pergunta 1
**Observando a saida do script, quantas vezes a lideranca mudou de maos durante a "tempestade" de eleicoes da subida inicial (Parte A), antes de estabilizar? Isso tem algum custo real para o sistema (rede, tempo), mesmo nao afetando o resultado final?**

Na saida do meu `historico_lideranca.py`, durante a subida inicial houve **3 declaracoes de
TORNOU_LIDER** (ou seja, **2 trocas de maos** antes de estabilizar na Agencia 2):

  A partir de 2026-10-22T05:09:15.475593+00:00: Agencia 0 e a lider
  A partir de 2026-10-22T05:09:20.824735+00:00: Agencia 1 e a lider
  A partir de 2026-10-22T05:09:26.022990+00:00: Agencia 2 e a lider

Mesmo convergindo para o resultado correto (Agencia 2), essa "tempestade" inicial tem custos reais:
  1. **Custo de tempo (latencia de convergencia):** a Agencia 0 precisou esperar 2 timeouts de
     1 segundo cada (tentando falar com 1 e 2) antes de se declarar lider; a Agencia 1 esperou
     1 timeout (tentando falar com a 2). Somando as subidas escalonadas, o cluster levou ~15s
     (de 05:09:11 a 05:09:26) ate estabilizar.
  2. **Custo de rede (mensagens O(N^2)):** no pior caso (processos subindo do menor para o maior
     ou iniciando eleicao juntos), o Bully troca O(N^2) mensagens HTTP de `/bully/eleicao` e
     `/bully/coordenador`. Com 3 agencias sao poucas chamadas, mas com dezenas de nos o trafego
     de subida cresce quadraticamente.
  3. **Inflacao do relogio vetorial:** cada `ELEICAO_INICIADA`, `ao_enviar()`, `ao_receber()` e
     `TORNOU_LIDER` avanca o vetor da agencia. Na subida, o vetor ja comeca em valores como
     `[8, 4, 3]` antes de qualquer operacao bancaria acontecer — e qualquer avanco do vetor por
     eventos de eleicao invalida o `vetorConhecido` de clientes mobile offline (gerando HTTP 409).

---
## Secao 8.3 - Perguntas sobre o App Flutter e Painel de Lideranca

### Pergunta 1
**Como o app decide com que frequencia consultar /bully/lider? Que trade-off voce considerou ao escolher esse intervalo (resposta rapida a mudancas vs. consumo de bateria/rede do celular)?**

O app consulta `GET /bully/lider` a cada **3 segundos** (`Config.intervaloPolling = Duration(seconds: 3)`
em `app_mobile/lib/config.dart`), disparado por um `Timer.periodic` dentro do `LiderProvider`,
com timeout curto de 2 segundos por tentativa.

Escolhi 3 segundos porque e exatamente o mesmo intervalo padrao do heartbeat do backend
(`INTERVALO_HEARTBEAT_S = 3.0`). Consultar muito mais rapido do que o proprio cluster demora
para detectar uma queda (ex.: a cada 200ms) nao traria informacao nova mais cedo, mas manteria
o radio celular ativo continuamente, drenando bateria e dados moveis. Consultar muito devagar
(ex.: a cada 30s) economizaria bateria, mas deixaria a tela mostrando uma lider morta por muito
tempo e prejudicaria a demonstracao de failover em tempo real. Alem disso, para poupar bateria,
o `LiderProvider` implementa `WidgetsBindingObserver` e **pausa o Timer automaticamente** quando
o app vai para segundo plano (`AppLifecycleState.paused`), retomando ao voltar (`resumed`).

### Pergunta 2
**Se, num momento de transicao, voce consultasse duas agencias diferentes e elas respondessem lideres diferentes (uma ainda nao sabe da nova eleicao), como seu app se comporta? Isso e um problema real, ou se resolve sozinho na proxima consulta?**

No `LiderProvider`, o app memoriza em `_ultimaAgenciaOk` o indice da ultima agencia que respondeu
e sempre comeca a proxima rodada de polling por ela, so fazendo fallback para a proxima (`(indice + 1) % 3`)
quando a atual falha por timeout/conexao recusada. Se a agencia que ele consultava cair (por
exemplo, a propria lider Agencia 2 foi derrubada), o app passa a consultar a Agencia 0 ou 1.
Nesse exato instante de transicao, pode acontecer de:
  - A agencia consultada responder `{"liderAtual": null}` (ja detectou a queda, mas a eleicao
    ainda nao terminou) -> o app exibe o estado amarelo **"Eleicao em andamento..."**; ou
  - Uma agencia ainda responder a lider antiga (2) por 1 ou 2 segundos antes do seu heartbeat
    estourar, e na consulta seguinte (3s depois) ja responder a nova lider (1).

Para o escopo do Sprint 3, **isso se resolve sozinho na proxima consulta** (consistencia eventual
da visualizacao, convergindo em ~3 a 6 segundos) e nao causa dano porque a lider e apenas
informativa na UI. Em um sistema real onde o cliente enviasse escritas exclusivas para a lider
(Sprint 4), falar com uma lider obsoleta por alguns segundos poderia causar requisicoes
rejeitadas ou *split-brain*, exigindo numeros de epoca (*term/epoch*) para validar a lideranca.

### Pergunta 3
**Compare a arquitetura do app Flutter com a do frontend web do Sprint 1: o que foi reaproveitavel (conceitos, nao necessariamente codigo) e o que precisou ser pensado de forma diferente por ser uma plataforma mobile?**

**O que foi 100% reaproveitavel:**
  - **Contrato da API REST e regra de particionamento:** mesmos endpoints (`/auth/login`, `/contas/{id}`,
    `/depositar`, `/sacar`, `/transferencias`), mesmo formato de token Bearer JWT e mesma regra
    `id_conta % 3` para escolher em qual agencia bater.
  - **Separacao em camadas (MVC/Provider):** `ApiClient` equivale ao `services/api.js` (Model de
    rede), `AuthProvider`/`ContaProvider`/`LiderProvider` equivalem ao hook `useAuth.js` e estado
    do `App.jsx` (Controller), e os widgets em `screens/` equivalem aos componentes React (View).

**O que precisou ser pensado de forma diferente no mobile:**
  1. **Enderecamento de rede:** no navegador web, `localhost:4046` aponta para a propria maquina.
     No emulador Android, `localhost` e o proprio aparelho virtual; para alcancar o PC host foi
     preciso usar o IP especial de loopback do emulador (`10.0.2.2:4046`) e liberar trafego HTTP
     em texto claro (`usesCleartextTraffic="true"` e permissoes `INTERNET`/`ACCESS_NETWORK_STATE`
     no `AndroidManifest.xml`).
  2. **Persistencia segura e local:** em vez de `localStorage` do navegador (sincrono e volatil),
     o token JWT vai para o `FlutterSecureStorage` (Keystore do Android, assincrono) e os dados
     da conta + fila de operacoes vao para um banco relacional embarcado (`sqflite`).
  3. **Ciclo de vida e conectividade instavel:** celulares mudam entre online/offline (modo
     aviao, queda de sinal) e vao para segundo plano. Foi necessario ouvir eventos do SO
     (`WidgetsBindingObserver` para pausar timers e `connectivity_plus` para detectar reconexao)
     e desenhar toda a experiencia *offline-first* com fila persistida e UI otimista.

---
## Secao 9.6 - Perguntas sobre Sincronizacao Offline-First no Backend

### Pergunta 1
**Por que a agencia compara o vetor inteiro, e nao so verifica se o saldo da conta mudou? O que a comparacao de vetores detecta que uma simples comparacao de saldo nao detectaria?**

Comparar apenas o saldo sofre do **problema ABA**: o estado da conta pode ter mudado mais de
uma vez e voltado exatamente ao mesmo valor numerico. Exemplo: o app leu `saldo = R$ 100,00`
com `vetor = [2, 0, 0]` e ficou offline. Enquanto estava desconectado, a conta recebeu um
deposito de R$ 50 (saldo foi a R$ 150) e depois sofreu um saque ou transferencia de R$ 50
(saldo voltou a R$ 100, mas `vetor` agora e `[4, 0, 0]`).

Se a agencia olhasse apenas `saldoConhecido == saldoAtual` (100 == 100), acharia que nada
aconteceu e aplicaria um saque offline cegamente, ignorando que duas movimentacoes reais
ocorreram no meio do caminho. O relogio vetorial e **monotonicamente crescente**: cada evento
incrementa a posicao da agencia, entao `[2, 0, 0] != [4, 0, 0]` detecta com certeza matematica
que houve eventos intermediarios, mesmo quando o saldo final coincide. Alem disso, o vetor
captura relacoes causais entre agencias (ex.: creditos remotos vindos pelo RabbitMQ).

### Pergunta 2
**Neste exemplo, qualquer mudanca no vetor da agencia (mesmo em uma operacao de outra conta, que nada tem a ver com a sua) e tratada como conflito. Explique por que ela existe e o que seria necessario para tornar a deteccao mais precisa, por conta.**

Essa simplificacao existe porque, desde o Sprint 2, a agencia mantem **um unico `RelogioVetorial`
global por instancia de agencia** (`app.state.relogio`), e nao um relogio por conta. Assim,
qualquer evento naquela agencia — um deposito na conta 3, uma mensagem da conta 6, ou ate um
evento interno do algoritmo de Bully (`ELEICAO_INICIADA`, `LIDER_ANUNCIADO`, `LIDER_NAO_RESPONDEU`)
— incrementa `self.vetor[id_agencia]`. Quando o app da conta 0 tenta sincronizar, o vetor global
da Agencia 0 avancou e `comparar_vetores` devolve `'ANTES'` em vez de `'IGUAIS'`, gerando um
**falso positivo de conflito (HTTP 409)** mesmo que a conta 0 nao tenha sido tocada.

Para tornar a deteccao precisa **por conta**, seria necessario:
  1. Manter um **vetor (ou contador de versao/`etag`) individual dentro de cada conta**, ex.:
     `conta["vetorConta"] = [0, 0, 0]` (ou um inteiro `conta["versao"]`), que so e incrementado
     quando um evento afeta especificamente aquela conta (`criar_conta`, `depositar`, `sacar`,
     `transferir` envolvendo aquela conta, `processar_credito` daquela conta).
  2. Separar os eventos de infraestrutura (Bully/heartbeat) do relogio de dados das contas, para
     que eleicoes de lider nao invalidem a sincronizacao de clientes mobile.
  3. Em `GET /contas/{id}` e `POST /contas/{id}/sincronizar`, enviar e comparar o vetor da
     conta especifica em vez do vetor global da agencia.

### Pergunta 3
**Quando a sincronizacao e recusada (409), a agencia devolve o estado atual da conta. O que o app deveria fazer com essa informacao - descartar a operacao pendente, tentar de novo automaticamente, ou perguntar a pessoa usuaria? Justifique sua escolha de design na Parte F.**

Escolhi **nao descartar em silencio nem reaplicar as cegas, e sim pausar a fila e perguntar a
pessoa usuaria**, mostrando o estado real da conta (`contaAtual.saldo`) e oferecendo dois botoes
explicitos: **"Aplicar mesmo assim"** e **"Descartar"**.

Justificativa das tres alternativas em um dominio bancario:
  - **Descartar automaticamente e ruim:** a pessoa usuaria fez a operacao achando que ela seria
    enviada; sumir com um deposito ou saque sem dar opcao de reaplicar causa perda de intencao do
    usuario.
  - **Tentar de novo automaticamente (sem perguntar) e perigoso em banco:** imagine que a pessoa
    viu saldo de R$ 100 offline e pediu um saque de R$ 80, mas enquanto estava offline ja caiu
    um debito automatico de R$ 50 (saldo real = R$ 50, ou R$ 90). Ou imagine que ela fez o
    deposito pelo frontend web porque achou que o app nao tinha funcionado: reaplicar sozinho
    duplicaria a operacao.
  - **Perguntar ao usuario mostrando o saldo real (escolha adotada):** atualiza imediatamente o
    `saldoConfirmado` na tela com o `contaAtual` devolvido no 409, marca o item na lista como
    `CONFLITO` em vermelho e bloqueia o restante da fila (para preservar a ordem causal das
    operacoes). Se a pessoa confirmar **"Aplicar mesmo assim"**, o app faz `GET /contas/{id}`
    para pegar o `vetorAtual` mais recente e reenvia a operacao com seguranca; se clicar em
    **"Descartar"**, remove a operacao e libera o restante da fila.

---
## Secao 10.3 - Perguntas sobre o App Flutter Offline-First

### Pergunta 1
**Qual biblioteca de armazenamento local voce escolheu, e por que? Quais alternativas voce considerou?**

Escolhi o **`sqflite`** (SQLite embarcado para Flutter, em `app_mobile/lib/services/banco_local.dart`),
com duas tabelas relacionais: `contas` (cache do ultimo `saldo`, `nomeAluno`, `vetor` em JSON e
timestamp `atualizadoEm`) e `pendentes` (fila FIFO com `id AUTOINCREMENT`, `idConta`, `tipo`,
`valor`, `vetorConhecido`, `status`, `mensagem` e `saldoReal`).

Alternativas consideradas:
  - **`SharedPreferences`:** descartado para a fila porque e apenas chave-valor simples, sem
    consultas filtradas por `idConta` nem garantia transacional ao atualizar itens individuais.
    (Para o token JWT usei `flutter_secure_storage`, que usa criptografia do Android Keystore).
  - **`Hive`:** banco NoSQL leve e rapido em Dart puro; seria suficiente, mas exige adaptadores
    ou caixas separadas e nao oferece SQL padrao (`WHERE idConta = ? ORDER BY id ASC`) tao direto
    para manipular uma fila ordenada com estados (`PENDENTE`, `CONFLITO`, `RECUSADA`).
  - **`Drift`:** ORM reativo sobre SQLite, muito poderoso, porem exige geracao de codigo
    (`build_runner`), adicionando complexidade desnecessaria para duas tabelas simples.

O `sqflite` foi o ponto ideal: nativo no Android, transacional (ACID), preserva a ordem exata da
fila via `ORDER BY id ASC` e nao exige `build_runner`.

### Pergunta 2
**Na tarefa 5, o que exatamente aconteceu na tela do app quando a sincronizacao foi recusada? Descreva o comportamento que voce implementou e explique por que escolheu essa abordagem em vez de outra.**

Quando fiz o deposito offline no app, alterei o saldo da mesma conta por fora e reconectei:
  1. O `ContaProvider` detectou a reconexao e chamou `POST /contas/0/sincronizar` enviando o
     `vetorConhecido` antigo que estava salvo na operacao pendente.
  2. O backend respondeu **HTTP 409** com `erro`, `vetorConhecido`, `vetorAtual` e `contaAtual`.
  3. Na tela do app, imediatamente:
     - O saldo principal deixou de somar aquela operacao no saldo provisorio e passou a exibir o
       **saldo real atual da agencia** (`contaAtual.saldo`), atualizado no cache do SQLite.
     - Apareceu um alerta vermelho no topo explicando que a operacao feita offline nao foi
       aplicada automaticamente porque a conta mudou na agencia enquanto o app estava desconectado.
     - Na secao **"Operacoes feitas offline"**, o item mudou de `Pendente` (laranja) para um
       cartao vermelho destacado **`CONFLITO: Deposito de R$ ...`**, exibindo a mensagem do
       servidor, o texto *"Saldo real atual na agencia: R$ ..."* e dois botoes:
       **`Aplicar mesmo assim`** e **`Descartar`**.
  4. Ao clicar em **`Aplicar mesmo assim`**, o app consultou `GET /contas/0` para obter o
     `vetorAtual` vigente, atualizou o `vetorConhecido` da pendente e reenviou ao `/sincronizar`,
     que respondeu HTTP 200 e aplicou o valor sobre o saldo novo.

Escolhi essa abordagem porque torna o conflito 100% transparente na demonstracao (atendendo ao
requisito da secao 10.1 de nao esconder o 409 e mostrar o estado real da conta) e da controle
total ao usuario sobre reenviar ou cancelar.

### Pergunta 3
**UI otimista significa mostrar o resultado esperado antes de ter certeza de que ele vai acontecer. Que risco isso traz para um aplicativo bancario, especificamente? Como seu design tenta reduzir esse risco?**

Em um aplicativo bancario, o risco principal da UI otimista e **induzir a pessoa usuaria a tomar
decisoes financeiras com base em um dinheiro ou operacao que ainda nao foi (e pode nunca ser)
confirmado pelo banco**. Por exemplo:
  - Achar que um deposito offline ja "caiu" de verdade e contar com aquele saldo para outra coisa;
  - Achar que um saque/pagamento foi concluido quando, ao reconectar, ele sera rejeitado por
    conflito (409) ou por falta de saldo real (400), ja que outra operacao consumiu o saldo na
    agencia enquanto o celular estava sem rede.

Como o design do app reduz esse risco:
  1. **Separacao visual clara entre "Saldo Provisorio" e "Saldo Confirmado":** quando ha itens na
     fila, o valor principal muda de cor (amarelo/laranja), exibe um selo explicito
     *"Saldo provisorio: N operacao(oes) pendente(s) de sincronizacao"* e mostra logo abaixo,
     separadamente, o *"Saldo confirmado pela agencia: R$ ..."*.
  2. **Banner de modo offline e lista detalhada da fila:** um banner avisa que o app esta sem
     conexao com a agencia e cada operacao nao confirmada fica listada com horario e status.
  3. **Validacao local conservadora:** o app bloqueia saques offline maiores que o `saldoProvisorio`
     e **proibe transferencias entre contas quando esta offline ou enquanto houver operacoes
     pendentes**, evitando que efeitos nao confirmados se propaguem para outras contas/agencias.
  4. **Reversao imediata em caso de 409 ou 400:** se a agencia recusar a sincronizacao, o efeito
     otimista daquela operacao e retirado na hora do `saldoProvisorio` e o saldo real da agencia
     assume a tela.

---
## Funcionalidade Adicional Sprint 3 - Timeout Configuravel

**O que faz:** o intervalo do heartbeat e o timeout das chamadas HTTP do Bully deixam de ser
fixos no codigo e passam a ser lidos de variaveis de ambiente, em milissegundos:

  BULLY_HEARTBEAT_MS  - intervalo entre verificacoes da lider (padrao: 3000)
  BULLY_TIMEOUT_MS    - timeout de cada chamada /bully/* entre agencias (padrao: 1000)

**Validacao:** se a variavel nao estiver definida, o padrao e usado em silencio. Se o valor
for invalido (nao numerico, zero ou negativo), o padrao e usado e um aviso aparece no console:
  [Bully] AVISO: BULLY_TIMEOUT_MS='abc' invalido (esperado inteiro > 0, em ms). Usando padrao 1000 ms.
Ao subir, cada agencia imprime a configuracao efetiva:
  [Bully] Configuracao: heartbeat=3000 ms, timeout=1000 ms

**Exemplo (PowerShell):**
  $env:BULLY_HEARTBEAT_MS="1000"; $env:BULLY_TIMEOUT_MS="500"
  python -m uvicorn src.main:app --port 4046

**Por que foi escolhida:** as perguntas 6.4.1 e 6.4.3 discutem exatamente o trade-off entre
intervalo curto/longo e timeout curto/longo. Com a configuracao por ambiente, e possivel
reproduzir esses cenarios sem editar codigo: heartbeat de 500 ms detecta a queda mais rapido
(mais trafego), e um timeout muito baixo provoca falsos positivos de "lider nao respondeu".
Tambem permite acelerar a demonstracao do failover em sala.

**Implementacao:** _ler_ms_do_ambiente() e as constantes TIMEOUT_S e INTERVALO_HEARTBEAT_S
no topo de bully_service.py. As variaveis sao lidas uma unica vez, na subida do processo;
mudar o valor exige reiniciar a agencia.

**Evidencia:** evidencias/sprint3/funcionalidade-adicional.png

---

# RESPOSTAS Sprint 4 - ICEIBank

## Secao 5.10 - Perguntas sobre Persistencia Atomica, Containers e Rotas Internas

### Pergunta 1
**Por que o arquivo e gravado em um temporario e depois renomeado, em vez de sobrescrever o arquivo definitivo diretamente? O que poderia ficar no disco se a agencia caisse no meio de uma escrita direta?**

Sobrescrever `estado-agencia-0.json` diretamente com `open(..., "w")` nao e uma operacao
atomica: o sistema operacional primeiro **trunca o arquivo existente para 0 bytes** e depois
vai copiando os blocos do buffer para o disco aos poucos. Se o processo da agencia cair (por
`os._exit(1)`, falta de energia ou kill do container) no meio dessa gravacao, o arquivo no
disco fica **vazio ou cortado pela metade** (JSON invalido/corrompido). Ao reiniciar, o
`json.load()` falharia com `JSONDecodeError` e a agencia perderia tanto a versao nova quanto
a versao anterior de todas as contas, reservas e transacoes 2PC.

No `EstadoDuravel.salvar()` (`agencia/src/services/armazenamento.py`), fazemos em tres passos:
  1. Escrevemos o JSON inteiro em `estado-agencia-0.json.tmp` (enquanto isso, o arquivo
     definitivo `estado-agencia-0.json` continua intacto no disco);
  2. Chamamos `f.flush()` e `os.fsync(f.fileno())`, obrigando o kernel e o controlador de disco
     a persistirem fisicamente todos os bytes do `.tmp` antes de prosseguir;
  3. Chamamos `os.replace(temporario, self.caminho)`: no mesmo filesystem (volume `/dados`), o
     `rename/replace` e uma **operacao atomica de metadados do diretorio** (troca o ponteiro de
     inode de uma so vez).

Assim, se a agencia cair antes do `os.replace`, o arquivo definitivo ainda tem o estado antigo
100% integro; se cair depois, ja tem o estado novo 100% integro — nunca um arquivo pela metade.

### Pergunta 2
**Se voce removesse o volume do docker-compose.yml e recriasse os containers (`docker compose down` seguido de `up`), o que aconteceria com as contas? E se, no meio de uma transacao 2PC, um participante perdesse o disco dessa forma: o que ele "esqueceria" e que problema isso causaria ao protocolo?**

Sem o volume nomeado (`dados-0:/dados`), os arquivos `.json` e `.jsonl` seriam gravados na
camada gravavel efemera (*writable layer*) do proprio container. Um `docker compose restart`
ate preservaria essa camada, mas um `docker compose down` destroi o container e sua camada
efemera; no proximo `docker compose up`, um container novo e limpo seria criado do zero e
**todas as contas, saldos, reservas e transacoes desapareceriam**.

Se um **participante do 2PC** perdesse o disco dessa forma logo apos ter votado `SIM` na Fase 1:
  - Ele **"esqueceria" a promessa feita ao coordenador** (o registro `PREPARADO` em
    `estado.participacoes` e o valor travado em `conta["reservado"]`, alem do proprio saldo).
  - **Problema causado ao protocolo:** o coordenador, tendo recebido `SIM` de todos, decidiria
    `COMMIT` e enviaria `POST /2pc/decidir` com `decisao: "COMMIT"`. Ao chegar no participante
    que perdeu o disco, `minhas` estaria vazio e `participante.decidir()` devolveria **HTTP 409**
    (`{"erro": "Transação desconhecida por este participante."}`). O outro participante ja teria
    aplicado o `COMMIT` (ex.: debitado ou creditado), enquanto este jamais conseguiria aplicar —
    **quebrando a atomicidade do 2PC** (uma metade da transferencia foi efetivada e a outra nao).

### Pergunta 3
**O relogio vetorial (Sprint 2) nao foi persistido: ao reiniciar, a agencia volta a contar de `[0,0,0]`. Isso pode violar a causalidade registrada nos logs? Descreva um cenario concreto e proponha uma correcao simples.**

Sim, reiniciar o vetor em `[0, 0, 0]` enquanto o arquivo de log `.jsonl` no volume `/dados`
continua acumulando eventos **viola a propriedade fundamental do relogio vetorial** (que exige
contadores monotonicamente crescentes por processo).

**Cenario concreto:**
  1. A Agencia 0 processa varios eventos ate atingir o vetor `[10, 4, 8]` e envia uma mensagem
     para a Agencia 1 com `vetorEnvio = [10, 4, 8]`. A Agencia 1 registra um evento `B` com
     vetor `[10, 5, 8]`.
  2. A Agencia 0 reinicia (`docker compose restart agencia-0`). Suas contas sobreviveram no
     volume, mas seu `RelogioVetorial` na RAM volta para `[0, 0, 0]`.
  3. Um cliente faz um novo deposito `C` na Agencia 0 (que aconteceu no mundo real **depois** de
     tudo acima). A Agencia 0 registra `C` no `.jsonl` com `timestampVetorial = [1, 0, 0]`.
  4. Resultado: ao analisar os logs ou comparar vetores, `[1, 0, 0] < [10, 5, 8]` em todas as
     posicoes — fazendo parecer que o evento `C` (novo) aconteceu **causalmente ANTES** de
     eventos antigos, ou gerando comparacoes falsas no `/sincronizar` do app mobile.

**Correcao simples (duas opcoes complementares):**
  - **Opcao 1 (no `EstadoDuravel`):** incluir o campo `"vetor": self.relogio.obter_vetor_atual()`
    dentro do `estado-agencia-{id}.json` a cada `estado.salvar()` e restaurar `relogio.vetor` no
    `carregar()` ao subir.
  - **Opcao 2 (lendo o `.jsonl` no startup):** ao inicializar `RelogioVetorial`, ler a ultima
    linha de `/dados/eventos-agencia-{id}.jsonl`, pegar o `timestampVetorial` do ultimo evento
    gravado antes da queda e inicializar `self.vetor` a partir dele.

### Pergunta 4
**O token interno e um segredo compartilhado: qualquer agencia (ou quem o descobrir) pode chamar qualquer rota interna de qualquer outra. Quais sao os limites dessa protecao? O que seria mais robusto (ex.: TLS mutuo, rede privada)?**

Limites do segredo simetrico compartilhado (`x-token-interno`):
  1. **Ausencia de identidade individual por agencia (nao-repudio / menor privilegio):** todas
     as 3 agencias usam exatamente a mesma string `TOKEN_INTERNO`. A Agencia 0 nao consegue
     verificar criptograficamente se quem chamou `/2pc/decidir` foi realmente a coordenadora
     Agencia 2 ou se foi a Agencia 1 se passando por ela.
  2. **Raio de explosao total em caso de vazamento:** se o segredo vazar de um unico container
     ou arquivo `.env`, o atacante ganha acesso irrestrito a todas as rotas internas (`/2pc/*` e
     `/bully/*`) de todas as agencias ao mesmo tempo, e rotacionar o segredo exige reconfigurar
     todo o cluster simultaneamente.
  3. **Trafego em texto claro (HTTP sem TLS):** como as chamadas internas trafegam em HTTP puro,
     qualquer interceptador na rede (*man-in-the-middle*) pode capturar o cabecalho
     `x-token-interno` e reproduzir requisicoes (*replay attack*).

**O que seria mais robusto em producao:**
  - **Isolamento em rede privada Docker/VPC:** expor para o host/internet apenas um API Gateway
    com as rotas publicas (`/auth/*`, `/contas/*`, `/transferencias`, `/bully/lider`), mantendo
    as rotas `/2pc/*` e `/bully/eleicao` acessiveis somente na bridge interna entre containers
    (ou em uma porta interna nao publicada no `ports:` do compose).
  - **mTLS (Mutual TLS):** cada agencia possui seu proprio certificado X.509 (`agencia-0.crt`,
    `agencia-1.crt`, `agencia-2.crt`) assinado por uma CA interna; o canal e criptografado e o
    servidor valida a identidade exata de qual agencia esta chamando.
  - **JWT assinado com chave assimetrica (RS256/Ed25519) por agencia:** cada agencia assina
    suas chamadas internas com sua chave privada (`iss: "agencia-2"`, `exp` curto + `jti`
    anti-replay) e as demais validam com a chave publica correspondente.

---

## Secao 6.6 - Perguntas sobre o Participante do 2PC

### Pergunta 1
**Por que o participante grava a promessa em disco antes de responder SIM? Descreva o que poderia dar errado se gravasse depois.**

No 2PC, responder `voto: "SIM"` na Fase 1 significa abrir mao da autonomia local: o participante
promete ao coordenador que a operacao ja foi validada, os recursos foram reservados e que ele
**garante** conseguir aplicar `COMMIT` ou `ABORT` quando a Fase 2 chegar, mesmo que caia e
reinicie no meio do caminho.

Se o participante enviasse o HTTP 200 `{voto: "SIM"}` pela rede **antes** de chamar
`estado.salvar()` e caisse exatamente entre o envio da resposta e a gravacao em disco:
  1. O coordenador receberia o `SIM` normalmente, juntaria com o `SIM` do outro participante e
     decidiria **`COMMIT`**.
  2. Enquanto o participante estava reiniciando (ou logo ao voltar), como o `estado.salvar()`
     nao havia rodado, a conta voltaria do disco com **`reservado = 0`** e sem nenhum registro
     em `estado.participacoes`.
  3. Um saque concorrente de um cliente naquela conta veria `saldo_disponivel` cheio e
     **gastaria o dinheiro** que deveria estar reservado para o 2PC (ou o proprio `decidir` do
     coordenador falharia com 409 *"Transação desconhecida por este participante"*).

Por isso o `estado.salvar()` (com `fsync` + `os.replace`) acontece obrigatoriamente **antes** do
`return {"voto": "SIM"}` (e o ponto de falha `falhar("participante-apos-votar")` fica justamente
entre o `salvar()` e o `return` para provar que a promessa ja esta segura no disco).

### Pergunta 2
**O que significa a operacao ser idempotente aqui? Por que a rede torna isso obrigatorio, e nao opcional?**

Uma operacao e **idempotente** quando aplica-la 1 vez, 2 vezes ou $N$ vezes com os mesmos
parametros produz exatamente o mesmo estado final no sistema e devolve uma resposta coerente,
sem duplicar efeitos colaterais (nao reserva duas vezes nem debita/credita duas vezes).

No nosso `participante.py`, tanto `preparar` quanto `decidir` sao idempotentes:
  - Em `preparar`: se `estado.participacoes.get(f"{tx_id}:{tipo}")` ja existe, ele nao soma
    `valor` em `conta["reservado"]` novamente — apenas devolve o voto ja registrado (`SIM` ou
    `NAO`).
  - Em `decidir`: no laco sobre `minhas`, a linha `if p["estado"] != "PREPARADO": continue`
    garante que, se a participacao ja passou para `COMMITADO` ou `ABORTADO` na primeira chamada,
    chamadas repetidas ignoram a movimentacao de saldo e respondem `{"ok": True}` (como vimos no
    teste da secao 6.5 ao enviar `COMMIT` duas vezes seguidas para `teste-1`, mantendo o saldo
    em `1900.0`).

**Por que a rede torna isso obrigatorio:** em sistemas distribuidos sobre rede IP/HTTP, uma
falha de comunicacao e ambigua — quando o coordenador envia `POST /2pc/decidir` e sofre timeout
(ou queda de conexao), ele **nao tem como saber** se o pacote se perdeu na ida (antes de o
participante aplicar) ou se o participante aplicou o débito, salvou em disco e caiu/perdeu a
conexao na volta da resposta HTTP. Como a unica forma de garantir entrega e a **reentrega
periodica (`reentregar_pendentes`)**, o protocolo *at-least-once* inevitavelmente entregara a
mesma decisao mais de uma vez em cenarios de falha, tornando a idempotencia obrigatoria.

### Pergunta 3
**Por que o participante, depois de votar SIM, nao pode decidir sozinho abortar (por exemplo, por timeout), mesmo que o coordenador esteja demorando?**

Porque, a partir do momento em que o participante enviou `SIM`, ele entrou na **janela de
incerteza (em duvida / `PREPARADO`)**: ele nao sabe o que aconteceu do outro lado da rede.
Existem dois mundos possiveis e indistinguiveis do ponto de vista local daquele participante:
  - **Mundo A:** o coordenador caiu antes de decidir (ou o outro participante votou `NAO`), e a
    decisao final sera `ABORT`.
  - **Mundo B:** o outro participante tambem votou `SIM`, o coordenador **ja decidiu `COMMIT`**,
    ja gravou `COMMIT` em disco e **ja entregou `COMMIT` para o outro participante** (que ja
    creditou o dinheiro na conta de destino!), tendo caido logo antes de enviar a mensagem para
    este participante.

Se o participante em duvida abortasse unilateralmente por timeout e liberasse a reserva no
Mundo B, a conta de destino teria recebido o credito e a conta de origem nao seria debitada —
criando dinheiro do nada e destruindo a consistencia global. Por isso o 2PC e um **protocolo
bloqueante**: apos votar `SIM`, o participante e obrigado a manter `estado = 'PREPARADO'` e o
saldo reservado indefinidamente, rodando `resolver_em_duvida()` (`GET /2pc/status/{txId}`) ate o
coordenador responder.

### Pergunta 4
**Por que o debito reserva o valor na fase 1 em vez de simplesmente debitar? O que poderia acontecer com duas transferencias simultaneas da mesma conta sem a reserva?**

**1. Por que reservar na Fase 1 em vez de debitar direto:**
Na Fase 1 a transacao ainda **nao foi confirmada** (o participante de credito pode votar `NAO`
porque a conta de destino nao existe, como no teste `idDestino = 99`, ou o coordenador pode
abortar por timeout). Se a Fase 1 ja subtraisse `conta["saldo"]`:
  - Leituras de `GET /contas/{id}` mostrariam um saldo menor que o real para uma transacao que
    ainda nem comitou (*dirty read* / leitura suja);
  - Um `ABORT` exigiria re-somar dinheiro ao saldo (compensacao), dificultando distinguir o que
    e dinheiro efetivamente na conta do que esta apenas bloqueado aguardando confirmacao.
Separar `saldo` (dinheiro real na conta), `reservado` (comprometido em 2PC em aberto) e
`disponivel = saldo - reservado` torna o estado transparente e o `ABORT` trivial (`reservado -= valor`).

**2. O que aconteceria com duas transferencias simultaneas sem a reserva (*double spending*):**
Suponha que a Conta 0 tenha `saldo = R$ 100,00` e o cliente dispare duas transferencias de
`R$ 80,00` quase ao mesmo tempo (`T1` e `T2`):
  - **Sem reserva na Fase 1:** o `preparar` de `T1` olha `saldo (100) >= 80` e vota `SIM`. Antes
    que a Fase 2 de `T1` chegue, o `preparar` de `T2` tambem olha `saldo (100) >= 80` e tambem
    vota `SIM`! Ambas recebem `COMMIT` na Fase 2 e debitam `80 + 80 = 160`, deixando a conta
    com **saldo negativo (`-R$ 60,00`)** — gasto duplo.
  - **Com a reserva + `estado.lock`:** o `preparar` de `T1` reserva `80` (`saldo = 100`,
    `reservado = 80`, `disponivel = 20`). Quando o `preparar` de `T2` chega milissegundos
    depois, ele verifica `saldo_disponivel(conta) (20) < 80`, vota **`NAO ("Saldo insuficiente.")`**
    e `T2` e abortada com seguranca.

---

## Secao 7.4 - Perguntas sobre o Coordenador, Recuperacao e Transferencia via 2PC

### Pergunta 1
**O coordenador grava a decisao em disco antes de comunica-la aos participantes. Por que? O que poderia acontecer se a ordem fosse inversa e ele caisse entre as duas etapas?**

No `coordenador.py`, a linha `self.estado.salvar()` logo apos definir `coord["decisao"] = "COMMIT" | "ABORT"`
e `coord["estado"] = "DECIDIDA"` e o **ponto de efetivacao (*commit point* / ponto sem volta)**
de toda a transacao distribuida:
  - Antes desse `salvar()`, a transacao esta em `PREPARANDO` e ainda pode (e deve) ser abortada
    se o coordenador cair.
  - Depois desse `salvar()`, a decisao e **imutavel e eterna**: mesmo que o coordenador caia no
    milissegundo seguinte (`falhar("coordenador-apos-decidir")`), ao voltar ele lera
    `estado == 'DECIDIDA'` do disco e a thread `reentregar_pendentes()` (ou o endpoint
    `/2pc/status/{txId}`) entregara exatamente a mesma decisao a todos os participantes.

**Se a ordem fosse inversa** (enviar `POST /2pc/decidir` com `COMMIT` aos participantes *antes*
de gravar a decisao em disco) e o coordenador caisse apos enviar o `COMMIT` para a Agencia 0
mas antes de gravar no proprio disco:
  1. A Agencia 0 ja teria recebido `COMMIT` e debitado os R$ 100 definitivamente (`COMMITADO`).
  2. A Agencia 1 ainda estaria em `PREPARADO` (nao recebeu a mensagem).
  3. Ao reiniciar, o coordenador leria seu disco onde a transacao ainda constava como
     `PREPARANDO` (sem decisao gravada). O `coordenador.recuperar()` executaria o **aborto
     presumido**, gravando `decisao = "ABORT"` e enviando `ABORT` para a Agencia 1!
  4. Resultado catastrofico: a Agencia 0 comitou (debitou) e a Agencia 1 abortou (nao creditou)
     — o dinheiro desapareceu, violando a propriedade central do 2PC.

### Pergunta 2
**Explique por que o aborto presumido e seguro para transacoes que ficaram na fase 1, mas nao seria seguro presumir COMMIT para elas.**

Quando o coordenador reinicia e encontra no disco uma coordenacao com `estado == "PREPARANDO"`
(ou quando um participante consulta `/2pc/status/{txId}` sobre um `txId` que nem existe no disco
do coordenador), sabemos com **100% de certeza** que o coordenador caiu **antes** do ponto de
decisao da Fase 1.

**Por que presumir `ABORT` e totalmente seguro:**
  1. Como o coordenador nunca chegou a gravar `DECIDIDA` (e so envia mensagens da Fase 2 *apos*
     gravar), **nenhum participante jamais recebeu uma ordem de `COMMIT`** para essa transacao.
  2. Na Fase 1, qualquer participante no maximo votou `NAO` (ja esta `ABORTADO`) ou votou `SIM`
     (esta `PREPARADO` aguardando a decisao). Nenhum dos dois impede um `ABORT`: quem estava
     `PREPARADO` apenas libera a reserva (`reservado -= valor`) e volta ao estado original.

**Por que presumir `COMMIT` seria inseguro e incorreto:**
  1. Enquanto estava em `PREPARANDO`, **algum participante pode ter votado `NAO`** (por falta de
     saldo ou porque a conta de destino nao existia, ex.: `idDestino = 99`), ou pode nem ter
     recebido o `/2pc/preparar` antes da queda do coordenador.
  2. Um participante que votou `NAO` ja encerrou sua participacao como `ABORTADO` e nao reservou
     fundos; se o coordenador presumisse `COMMIT` na recuperacao, tentaria forcar a aplicacao de
     uma transferencia sem saldo ou para uma conta inexistente, quebrando a regra fundamental do
     2PC de que `COMMIT` exige unanimidade de votos `SIM`.

### Pergunta 3
**A mesma agencia pode ser coordenadora e participante da mesma transacao (ex.: a lider e a agencia 2 e a conta de destino esta nela). Isso causa algum problema para o protocolo? Como o codigo lida com isso?**

Do ponto de vista do protocolo 2PC, **nao causa nenhum problema**: "Coordenador" e "Participante"
sao **papeis logicos independentes**. Quando a Agencia 2 e a lider e coordena uma transferencia
envolvendo a Conta 2 (que pertence a `2 % 3 == 2`), ou mesmo uma transferencia local entre duas
contas da Agencia 0 coordenada pela Agencia 2, a agencia acumula os dois papeis mantendo os
estados completamente separados no mesmo `EstadoDuravel`:
  - O papel de coordenador grava em `estado.coordenacoes[txId]`;
  - O papel de participante grava em `estado.participacoes[f"{txId}:{tipo}"]` (inclusive, a
    chave inclui `:DEBITO` ou `:CREDITO` justamente para que, quando origem e destino estao na
    **mesma** agencia, ela possa participar duas vezes da mesma transacao sem sobrescrever a
    propria entrada!).

**Como o nosso codigo Python/FastAPI lida com isso sem travar (deadlock):**
  1. **Chamada HTTP para si mesma sem bloquear o event loop:** o coordenador faz
     `POST http://agencia-2:4048/2pc/preparar` (e `/2pc/decidir`) via `httpx.AsyncClient` +
     `asyncio.gather` dentro de uma rota `async def`. Durante o `await`, o event loop do Uvicorn
     fica livre para receber e despachar a requisicao de entrada para o handler `preparar` /
     `decidir` no pool de threads.
  2. **Lock liberado antes da chamada de rede:** no `coordenador.py`, o `with self.estado.lock:`
     e usado apenas no instante de gravar `PREPARANDO` ou `DECIDIDA` e **liberado imediatamente
     antes do `await client.post(...)`**. Se o coordenador segurasse `estado.lock` durante a
     chamada HTTP para si mesmo, o handler `participante.preparar()` na mesma agencia ficaria
     bloqueado esperando o mesmo `estado.lock` em outra thread, causando *deadlock* e timeout.

### Pergunta 4
**Compare com o Sprint 2 (debita e depois publica no RabbitMQ). Que garantia o 2PC da e a abordagem anterior nao dava? Que custo o 2PC introduz (latencia, disponibilidade)?**

**Garantia que o 2PC da e o Sprint 2 nao dava — Atomicidade Distribuida (*All-or-Nothing*):**
  - **No Sprint 2 (mensageria assincrona sem coordenacao):** a agencia de origem debitava o
    saldo imediatamente e publicava uma mensagem `agencia.X.creditar` no RabbitMQ. Como vimos no
    Sprint 2, se a conta de destino nao existisse na outra agencia (ou se a outra agencia tivesse
    perdido o estado), o consumidor registrava `CREDITO_REMOTO_FALHOU`, mas **o dinheiro ja havia
    saido da conta de origem e nunca era estornado** — o banco ficava permanentemente
    inconsistente.
  - **No Sprint 4 (Two-Phase Commit):** nenhuma conta tem o saldo alterado antes que **ambas** as
    agencias validem a operacao, reservem os fundos e gravem o compromisso em disco na Fase 1.
    Como comprovamos no Teste 2 (`2pc-abort.png`) ao tentar transferir R$ 50 da Conta 0 para a
    conta inexistente `idDestino = 99`: a Agencia 0 votou `SIM` (reservando R$ 50), a validacao
    da Conta 99 votou `NAO ("Conta não encontrada nesta agência.")`, a coordenadora decidiu
    `ABORT` e a reserva na Conta 0 foi desfeita imediatamente, mantendo o saldo intacto em
    `R$ 1800,00`. Ou ambas as pontas aplicam, ou nenhuma aplica.

**Custos que o 2PC introduz em troca dessa garantia:**
  1. **Maior latencia por transferencia:** no Sprint 2, a transferencia fazia 1 escrita em RAM e
     1 publish no broker. No 2PC, cada transferencia exige encaminhamento a lider + **2 fases de
     chamadas HTTP sincronas em rede** (`/2pc/preparar` e `/2pc/decidir` para todos os
     participantes) + **multiplos `os.fsync` em disco** (no inicio, em cada voto `SIM`, na
     decisao do coordenador e na aplicacao final).
  2. **Menor disponibilidade e acoplamento temporal:** no Sprint 2, se a Agencia 1 estivesse
     fora do ar, a Agencia 0 publicava na fila duravel do RabbitMQ e respondia 200 na hora. No
     2PC, **todos os participantes e a coordenadora precisam estar online e respondendo dentro
     do timeout (2s) no momento da transferencia**; se qualquer um estiver fora do ar, o voto
     vira `NAO` por timeout e a transferencia e abortada (422) ou recusada (503).
  3. **Risco de bloqueio (*blocking protocol*):** se o coordenador cair apos os participantes
     votarem `SIM` e antes de divulgar a decisao, o dinheiro reservado (`conta["reservado"]`)
     fica bloqueado e indisponivel para o cliente ate que o coordenador se recupere.

---

## Secao 8.6 - Registro dos 5 Cenarios de Falha do 2PC (Parte D)

Em todos os 5 cenarios abaixo, verificamos o **invariante do sistema**: a soma dos saldos das
contas (`Conta 0 + Conta 1`) nao sofreu criacao nem destruicao de dinheiro e, apos a
convergencia/recuperacao, `reservado = 0` em todas as contas.

### Cenario 1 (Secao 8.1) - Participante fora do ar na Fase 1
- **O que foi feito:** com `Conta 0 = 1800.0` e `Conta 1 = 100.0` (soma = `1900.0`), paramos a
  Agencia 1 (`docker compose stop agencia-1`) e enviamos `POST /transferencias` de R$ 100 da
  Conta 0 para a Conta 1. Depois religamos a Agencia 1 (`docker compose start agencia-1`).
- **O que era esperado:** a Agencia 0 vota `SIM` (reserva R$ 100), a chamada a Agencia 1 sofre
  timeout de 2s (tratado como voto `NAO`), a coordenadora decide `ABORT`, libera a reserva na
  Agencia 0 imediatamente e reentrega `ABORT` a Agencia 1 quando ela volta.
- **O que foi observado (logs e resposta):**
  - Resposta HTTP 422:
    `{"txId":"bde3e886-f921-4e82-9f3f-b1669a311cd5","resultado":"ABORT","motivos":["Agência não respondeu a tempo."],"pendentesDeConfirmacao":[1]}`
  - Apos religar a Agencia 1, a reentrega concluiu a coordenacao (`estado=CONCLUIDA decisao=ABORT`).
- **Invariante:** respeitado (`Conta 0 = 1800.0`, `Conta 1 = 100.0`, **Soma = 1900.0**, **Reservado = 0**).

### Cenario 2 (Secao 8.2) - Participante cai depois de votar SIM (`participante-apos-votar`)
- **O que foi feito:** definimos `$env:FALHA_2PC_0 = "participante-apos-votar"`, recriamos os
  containers e transferimos R$ 100 da Conta 0 para a Conta 1.
- **O que era esperado:** a Agencia 0 reserva R$ 100, grava `PREPARADO` em disco e morre com
  `os._exit(1)` antes de responder HTTP. A coordenadora sofre timeout, decide `ABORT`. O Docker
  reinicia a Agencia 0 (`restart: on-failure`), que acorda em duvida (`PREPARADO`), consulta
  `/2pc/status/{txId}` na coordenadora, descobre `ABORT`, registra `2PC_RESOLVIDA_POR_CONSULTA`
  e libera os R$ 100 reservados.
- **O que foi observado (trecho real do log da `agencia-0`):**
  ```
  agencia-0-1 | [Vetor [9, 8, 24]] 2PC_VOTO_SIM {'txId': '7b1a206d-b6f2-439e-8b25-0c7d9362a52f', 'operacao': {'tipo': 'DEBITO', 'idConta': 0, 'valor': 100.0}}
  agencia-0-1 | [FALHA INJETADA] participante-apos-votar: derrubando a agência 0 agora
  agencia-0-1 | [Vetor [1, 0, 0]] 2PC_RESOLVIDA_POR_CONSULTA {'txId': '7b1a206d-b6f2-439e-8b25-0c7d9362a52f', 'decisao': 'ABORT'}
  agencia-0-1 | [Vetor [2, 0, 0]] 2PC_ABORT_APLICADO {'txId': '7b1a206d-b6f2-439e-8b25-0c7d9362a52f', 'tipo': 'DEBITO', 'valor': 100.0}
  ```
- **Invariante:** respeitado (`Conta 0 = 1800.0`, `Conta 1 = 100.0`, **Soma = 1900.0**, **Reservado = 0**).
  Evidencia: `evidencias/sprint4/falha-participante.png`.

### Cenario 3 (Secao 8.3) - Coordenador cai antes de decidir (`coordenador-antes-de-decidir`)
- **O que foi feito:** definimos `$env:FALHA_2PC_2 = "coordenador-antes-de-decidir"` na lider
  Agencia 2 e transferimos R$ 100 da Conta 0 para a Conta 1.
- **O que era esperado:** os participantes votam `SIM` e reservam R$ 100; a Agencia 2 cai antes
  de gravar a decisao (cliente recebe HTTP 503). Ao reiniciar pelo Docker, a Agencia 2 executa
  `coordenador.recuperar()` antes de aceitar requisicoes, registra `2PC_ABORTO_PRESUMIDO` e
  comunica `ABORT` aos participantes, que liberam a reserva.
- **O que foi observado (trecho real dos logs da `agencia-2` e `agencia-0`):**
  ```
  agencia-2-1 | [Vetor [4, 9, 23]] 2PC_INICIO {'txId': '6a768db6-5d38-45e1-bfed-01dcd5123924', 'idOrigem': 0, 'idDestino': 1, 'valor': 100.0}
  agencia-2-1 | [FALHA INJETADA] coordenador-antes-de-decidir: derrubando a agência 2 agora
  agencia-2-1 | [Vetor [0, 0, 1]] 2PC_ABORTO_PRESUMIDO {'txId': '6a768db6-5d38-45e1-bfed-01dcd5123924'}
  agencia-2-1 | [Vetor [16, 19, 28]] 2PC_CONCLUIDA {'txId': '6a768db6-5d38-45e1-bfed-01dcd5123924', 'decisao': 'ABORT'}
  agencia-0-1 | [Vetor [11, 9, 24]] 2PC_RESOLVIDA_POR_CONSULTA {'txId': '6a768db6-5d38-45e1-bfed-01dcd5123924', 'decisao': 'ABORT'}
  agencia-0-1 | [Vetor [12, 9, 24]] 2PC_ABORT_APLICADO {'txId': '6a768db6-5d38-45e1-bfed-01dcd5123924', 'tipo': 'DEBITO', 'valor': 100.0}
  ```
- **Invariante:** respeitado (`Conta 0 = 1800.0`, `Conta 1 = 100.0`, **Soma = 1900.0**, **Reservado = 0**).
  Evidencia: `evidencias/sprint4/falha-coordenador.png`.

### Cenario 4 (Secao 8.4) - Coordenador cai depois de decidir COMMIT (`coordenador-apos-decidir`)
- **O que foi feito:** definimos `$env:FALHA_2PC_2 = "coordenador-apos-decidir"` na lider
  Agencia 2 e transferimos R$ 100 da Conta 0 para a Conta 1.
- **O que era esperado:** ambos votam `SIM`; a coordenadora grava `COMMIT` (`estado = 'DECIDIDA'`)
  em disco e cai imediatamente antes da Fase 2. O cliente recebe HTTP 503, mas, ao reiniciar, a
  coordenadora ve `DECIDIDA = COMMIT` no disco, reentrega o `COMMIT` e a transferencia se
  completa.
- **O que foi observado (trecho real do log da `agencia-2`):**
  ```
  agencia-2-1 | [Vetor [9, 12, 24]] 2PC_DECISAO_COMMIT {'txId': '72245233-a5f3-40a3-a36b-e4cf42e9f1b1'}
  agencia-2-1 | [FALHA INJETADA] coordenador-apos-decidir: derrubando a agência 2 agora
  agencia-2-1 | [Vetor [0, 0, 5]] 2PC_DECISAO_ENVIADA {'txId': '72245233-a5f3-40a3-a36b-e4cf42e9f1b1', 'para': 0, 'decisao': 'COMMIT'}
  agencia-2-1 | [Vetor [15, 8, 22]] 2PC_DECISAO_ENVIADA {'txId': '72245233-a5f3-40a3-a36b-e4cf42e9f1b1', 'para': 1, 'decisao': 'COMMIT'}
  agencia-2-1 | [Vetor [15, 18, 24]] 2PC_CONCLUIDA {'txId': '72245233-a5f3-40a3-a36b-e4cf42e9f1b1', 'decisao': 'COMMIT'}
  ```
  O cliente recebeu HTTP 503, mas a transferencia completou sozinha: `Conta 0` passou de
  `1800.0` para `1700.0` e `Conta 1` passou de `100.0` para `200.0`.
- **Invariante:** respeitado (`Conta 0 = 1700.0`, `Conta 1 = 200.0`, **Soma = 1900.0**, **Reservado = 0**).

### Cenario 5 (Secao 8.5) - O Bloqueio do 2PC
- **O que foi feito:** com `FALHA_2PC_2 = "coordenador-antes-de-decidir"` e a coordenadora
  Agencia 2 mantida parada apos a queda, transferimos da Conta 0 para a Conta 1.
- **O que era esperado:** os participantes votam `SIM`, reservam o valor na Conta 0 e ficam
  bloqueados em `estado = PREPARADO` registrando `2PC_BLOQUEADA_AGUARDANDO_COORDENADOR`. Um
  saque que dependa do valor reservado e recusado com HTTP 422 (`Saldo insuficiente.`). Ao
  religar a Agencia 2, ela executa `2PC_ABORTO_PRESUMIDO` e desbloqueia a reserva.
- **O que foi observado:**
  - Durante o bloqueio: `reservado > 0`, `disponivel = 200.0 < saldo`, tentativa de saque de
    R$ 500 recusada com **HTTP 422** (`{"detail":"Saldo insuficiente."}`), log
    `2PC_BLOQUEADA_AGUARDANDO_COORDENADOR` na Agencia 0 e `transacoes.py` exibindo os
    participantes em `estado=PREPARADO` com a Agencia 2 `fora do ar`.
  - Apos religar a Agencia 2: o bloqueio terminou automaticamente com `2PC_ABORTO_PRESUMIDO` e
    `reservado` voltou a `0`.
- **Invariante:** respeitado (nenhum dinheiro criado ou destruido; reserva liberada apos a volta
  da coordenadora). Evidencias: `evidencias/sprint4/bloqueio.png` e
  `evidencias/sprint4/transacoes-js.png`.

---

## Secao 8.7 - Perguntas sobre os Testes de Falha (Parte D)

### Pergunta 1
**No cenario 2, o coordenador decidiu ABORT por timeout, mas o participante tinha votado SIM em disco. Por que isso nao gera inconsistencia? Quem "vence" e como o participante fica sabendo?**

Nao gera inconsistencia porque **vota `SIM` nao e uma decisao final — e apenas uma promessa
condicional** de que o participante *pode* tanto comitar quanto abortar, dependendo do que o
coordenador decidir. No 2PC, **quem sempre "vence" e a decisao unilateral do coordenador**:
para decidir `COMMIT` o coordenador precisa receber `SIM` de todos; como a resposta da Agencia 0
nao chegou (ela caiu apos `estado.salvar()`), o coordenador tratou o timeout como voto `NAO` e
gravou `DECIDIDA = ABORT`.

Enquanto estava em `PREPARADO`, a Agencia 0 apenas **reservou** os R$ 100 (`reservado += 100`),
sem alterar `saldo`. Quando o Docker reiniciou a Agencia 0, a thread `resolver_em_duvida()`
viu a participacao em `PREPARADO` e consultou `GET /2pc/status/{txId}` na coordenadora Agencia 2.
A Agencia 2 respondeu `{"decisao": "ABORT"}`, e a Agencia 0 registrou
`2PC_RESOLVIDA_POR_CONSULTA` seguido de `2PC_ABORT_APLICADO`, subtraindo os R$ 100 de `reservado`
e alinhando seu estado local com a decisao do coordenador.

### Pergunta 2
**No cenario 5, o dinheiro fica preso enquanto o coordenador esta fora. Isso e uma falha de seguranca (safety) ou de disponibilidade (liveness) do protocolo? Justifique.**

E uma falha de **disponibilidade / progresso (*liveness*)**, justamente para **preservar a
seguranca (*safety*)** a qualquer custo.
  - ***Safety* ("nada de ruim acontece"):** o invariante de atomicidade e conservacao de
    dinheiro nunca e violado — o dinheiro reservado nao pode ser gasto duas vezes (o saque de
    R$ 500 foi recusado com HTTP 422) nem desaparece.
  - ***Liveness* ("algo de bom eventualmente acontece"):** a transacao e os R$ 1000 reservados
    nao conseguem progredir (nem para `COMMIT` nem para `ABORT`) enquanto o processo coordenador
    da Agencia 2 estiver desligado.

O 2PC faz uma escolha explicita no espectro *Safety vs. Liveness*: como o participante que votou
`SIM` nao sabe se o coordenador chegou a decidir `COMMIT` antes de cair, a unica maneira de
garantir *safety* sem consenso replicado e **bloquear (*sacrificar liveness*)** ate o
coordenador voltar.

### Pergunta 3
**No cenario 4, o cliente recebeu um erro, mas a transferencia se completou depois. Isso e aceitavel para um banco? O que a API poderia oferecer para que o cliente descubra o resultado real? (Dica: na Parte F voce cria justamente um comprovante consultavel por txId.)**

Devolver um erro generico HTTP 503 sem identificador quando a operacao na verdade sera efetivada
em background e **muito problematico para a experiencia bancaria**: o cliente (ou o app mobile),
achando que a transferencia falhou ("Nada foi aplicado; tente novamente"), pode clicar em
*Transferir* de novo e **duplicar a transferencia**.

O que a API bancária deveria oferecer para resolver isso:
  1. **Gerar ou aceitar um `txId` (chave de idempotencia) logo na entrada e devolve-lo mesmo em
     respostas 202/503:** assim o cliente sabe qual `txId` ficou "em processamento".
  2. **Endpoint de consulta de status/comprovante por `txId`:** como o `GET /2pc/status/{txId}`
     (interno) ou, para o cliente final, a API serverless de **consulta de comprovante por
     `txId`** implementada na **Parte F** (que consulta o DynamoDB/S3 e informa se aquela
     transacao especifica terminou em `COMMIT` ou `ABORT`).

### Pergunta 4
**Se a lider cair e o Bully eleger outra agencia, quem resolve as transacoes em andamento da lider antiga? O codigo deste roteiro cobre esse caso? Explique o que acontece e o que faltaria.**

No codigo deste roteiro, **apenas a coordenadora original (a lider antiga, quando voltar ao ar)
pode resolver as transacoes que ela mesma iniciou** — a nova lider eleita pelo Bully **nao**
assume as transacoes em andamento da lider antiga!

**Por que isso acontece no codigo:**
  1. Quando um participante vota `SIM` em `participante.preparar()`, ele grava no seu disco
     `"coordenador": coordenador` (o ID fixo da agencia que iniciou aquela transacao, ex.: `2`).
  2. Na funcao `resolver_em_duvida()`, o participante consulta sempre
     `GET {url_de(p.coordenador)}/2pc/status/{p.txId}` (ou seja, pergunta especificamente para a
     **Agencia 2**, e nao para `bully.obter_lider_atual()`).
  3. Mesmo que o participante perguntasse para a nova lider (Agencia 1), o registro daquela
     coordenacao (`estado.coordenacoes[txId]`) esta gravado apenas no volume local `/dados` da
     **Agencia 2**. Se a Agencia 1 fosse consultada, ela nao teria o `txId` em
     `estado.coordenacoes` e seu `status_de(txId)` responderia **aborto presumido (`ABORT`)** —
     o que seria um **bug catastrofico** caso a Agencia 2 ja tivesse decidido `COMMIT` antes de
     cair!

**O que faltaria para a nova lider assumir as transacoes da antiga sem esperar ela voltar:**
  - **Estado de coordenacao replicado por consenso (Paxos/Raft)** entre as agencias, para que a
    nova lider enxergasse exatamente se a antiga gravou `PREPARANDO` ou `DECIDIDA = COMMIT`; ou
  - Um **protocolo de terminacao cooperativa (como no 3PC)** em que a nova lider consulta todos
    os participantes para descobrir se algum ja recebeu `COMMIT` ou se todos ainda estao em
    `PREPARADO`, usando numeros de epoca (*epochs/terms*) para impedir que a lider antiga tome
    decisoes conflitantes ao voltar.

---

## Secao 9.3 - Perguntas sobre Observabilidade das Transacoes (`transacoes.py`)

### Pergunta 1
**O estado das transacoes so cresce: nada e removido. Num sistema real, isso e um problema? Que politica de limpeza (e que cuidado com o aborto presumido) voce proporia?**

Sim, em um sistema real de producao isso e um problema serio: como `estado.coordenacoes` e
`estado.participacoes` nunca removem entradas e `estado.salvar()` reescreve o arquivo JSON
inteiro a cada mudanca, o consumo de memoria RAM, o tamanho do arquivo em disco e o tempo de
serializacao/`fsync` cresceriam indefinidamente ($O(N)$ por operacao), degradando o throughput
ate esgotar o disco ou a memoria.

**Politica de limpeza (*garbage collection* de transacoes) e o cuidado com o aborto presumido:**
  1. **No coordenador:** uma coordenacao so pode ser removida do mapa ativo **depois que atingir
     `estado == "CONCLUIDA"`** (isto e, quando `all(p["confirmou"] for p in coord["participantes"])`
     for verdadeiro — todos os participantes ja confirmaram que aplicaram o `COMMIT` ou `ABORT`
     da Fase 2).
  2. **Armadilha critica com o aborto presumido (`status_de`):** se o coordenador apagar um
     `txId` que decidiu **`COMMIT`** antes que todos os participantes tenham confirmado (ou se
     uma resposta `ok: true` da Fase 2 for processada mas um participante tardio ainda perguntar
     `GET /2pc/status/{txId}`), o `status_de(txId)` nao encontrara o `txId` e devolvera
     **`ABORT` ("transação desconhecida - aborto presumido")** para uma transacao que na verdade
     havia sido **`COMMIT`**!
     - **Por que apagar um `ABORT` concluido e imediato:** sob a regra de *Presumed Abort*,
       "nao existir no coordenador" equivale a `ABORT`; logo, esquecer uma transacao abortada
       nunca muda a resposta de `status_de`.
     - **Cuidado para apagar um `COMMIT`:** o coordenador so pode remover da memoria/disco uma
       transacao `COMMIT` quando **100% dos participantes tiverem confirmado a Fase 2** (`CONCLUIDA`)
       e, opcionalmente, arquivar um log historico/TTL em armazenamento frio (como o DynamoDB/S3
       da Parte F) antes de expurgar do `estado-agencia-{id}.json`.
  3. **Nos participantes:** uma participacao em `COMMITADO` ou `ABORTADO` pode ser expurgada
     apos um **TTL (ex.: 24h)** muito maior que a janela maxima de reentrega do coordenador (ou
     apos confirmacao explicita de fim de protocolo na terceira mensagem *ACK*).

### Pergunta 2
**Os logs de eventos usam o relogio vetorial do Sprint 2. Em que situacao o vetor ajuda a entender uma falha do 2PC que o horario de parede nao ajudaria?**

Quando as 3 agencias rodam em maquinas/VMs diferentes, seus **relogios fisicos de parede
(`horaParede`) podem ter *clock skew* (desvio de dezenas de milissegundos ou segundos via NTP)**.
Em uma transacao 2PC onde as fases duram apenas ~5 a 20 ms na rede local, o `horaParede` pode
mostrar absurdos aparentes como:
  - O participante registrando `2PC_VOTO_SIM` com `horaParede` **maior** do que o
    `2PC_DECISAO_ABORT` do coordenador; ou
  - Uma duvida real de auditoria na Parte D: *"no Cenario 2, o coordenador decidiu `ABORT`
    **antes** de receber o voto do participante (por timeout), ou recebeu a mensagem do
    participante e mesmo assim abortou?"*

Com o **`timestampVetorial`**, essa ambiguidade desaparece matematicamente, sem depender de NTP:
  - Quando o participante envia a resposta de `/2pc/preparar` (ou quando o coordenador envia
    `/2pc/decidir`), o `vetorEnvio` viaja no JSON e o receptor faz `relogio.ao_receber(vetorEnvio)`.
  - Olhando os vetores nos nossos logs do Cenario 2: a Agencia 0 gravou `2PC_VOTO_SIM` com vetor
    `[9, 8, 24]` e caiu antes de responder; a coordenadora Agencia 2 gravou `2PC_DECISAO_ABORT`
    com a posicao 0 do seu vetor **menor que 9** (ela nao absorveu o `9` da Agencia 0!). Isso
    prova com certeza causal que a decisao da coordenadora foi tomada **sem jamais ter recebido**
    a resposta do voto da Agencia 0.

---

## Funcionalidade Adicional Sprint 4 - Endpoint de Saude (`GET /saude`) com Healthcheck no Docker Compose

**O que faz:** expoe o endpoint publico `GET /saude` (sem exigir JWT nem `x-token-interno`) em
todas as 3 agencias (`agencia/src/controllers/status_controller.py`), retornando:
```json
{"status": "ok", "idAgencia": 0, "liderAtual": 2}
```
E configura a diretiva `healthcheck` em cada servico (`agencia-0`, `agencia-1` e `agencia-2`) no
`docker-compose.yml`:
```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:4046/saude', timeout=2)"]
  interval: 10s
  timeout: 3s
  retries: 3
  start_period: 5s
```

**Por que foi escolhida:** sem `healthcheck`, o `docker compose ps` mostra apenas `Up X minutes`
(indicando que o processo PID 1 existe), mesmo que o servidor HTTP Uvicorn esteja travado em
deadlock. Com o `healthcheck` batendo em `GET /saude`, o Docker valida ativamente a pilha HTTP da
agencia a cada 10 segundos e exibe o status **`Up X minutes (healthy)`** no `docker compose ps`.
Usamos `urllib.request` da biblioteca padrao do Python para funcionar na imagem enxuta
`python:3.11-slim` sem precisar instalar `curl` ou `wget` via `apt`.

**Evidencia:** `evidencias/sprint4/funcionalidade-adicional.png`

---

## Secao 10.7 - Perguntas sobre Nuvem Local com LocalStack (Containers + Serverless)

### Pergunta 1
**A Lambda `gerar-comprovante` e idempotente. Mostre no codigo onde isso e garantido e descreva um cenario concreto em que a mesma mensagem chega duas vezes.**

No codigo de `serverless/gerar-comprovante/index.py`, a idempotencia e garantida em duas camadas:
  1. **No DynamoDB (escrita condicional atomica):**
     ```python
     try:
         tabela.put_item(
             Item={
                 "txId": ev["txId"],
                 "resultado": ev["resultado"],
                 "valor": Decimal(str(ev["valor"])),
                 "idOrigem": int(ev["idOrigem"]),
                 "idDestino": int(ev["idDestino"]),
                 "emitidoEm": emitido_em,
             },
             ConditionExpression="attribute_not_exists(txId)",
         )
     except ClientError as erro:
         codigo = erro.response.get("Error", {}).get("Code")
         if codigo != "ConditionalCheckFailedException":
             raise
     ```
     Quando a mesma mensagem chega pela segunda vez com o mesmo `txId`, o DynamoDB recusa a
     sobrescrita levantando `ConditionalCheckFailedException`, que a Lambda captura e ignora
     como "ja processado com sucesso" (nao adiciona em `batchItemFailures`, permitindo ao SQS
     remover a duplicata da fila).
  2. **No S3 (chave deterministica por `txId`):** `Key=f"comprovantes/{ev['txId']}.json"` usa o
     proprio UUID da transacao como nome do objeto (`put_object` sobre a mesma chave apenas
     mantem um unico arquivo para aquele `txId`, sem criar arquivos duplicados).

**Cenario concreto em que a mesma mensagem chega duas vezes:**
  - As filas SQS padrao (*Standard Queues*) garantem entrega ***at-least-once*** (pelo menos uma
    vez): o proprio broker distribuido do SQS pode entregar duas copias da mesma mensagem em um
    mesmo lote ou em lotes seguidos.
  - Alem disso, se a Lambda receber um lote com 2 mensagens (`M1` e `M2`), gravar `M1` no S3 e
    no DynamoDB com sucesso, mas o container da Lambda sofrer *timeout* (ou queda de rede) no
    meio de `M2` antes de devolver a resposta ao *event source mapping* do SQS, o
    *Visibility Timeout* de ambas expira na fila e o SQS **reentrega `M1` e `M2` novamente** na
    proxima invocacao.

### Pergunta 2
**Por que usar `batchItemFailures` em vez de simplesmente lancar uma excecao quando uma mensagem do lote falha? O que aconteceria com as outras mensagens do lote?**

O *event source mapping* entre SQS e Lambda entrega mensagens em **lotes** (`--batch-size 5` no
nosso `init.sh`).
  - **Se a Lambda lancar uma excecao nao tratada** quando a 3ª mensagem do lote falha: a AWS
    Lambda considera que **o lote inteiro de 5 mensagens falhou**. Nenhuma das 5 mensagens e
    removida da fila SQS; apos o *visibility timeout*, todas as 5 (inclusive as 4 que ja tinham
    sido processadas com sucesso!) voltam para a fila e sao reprocessadas repetidamente,
    desperdicando invocacoes e podendo bloquear mensagens saudaveis atras de uma unica mensagem
    defeituosa (*poison pill*).
  - **Usando `ReportBatchItemFailures` e retornando `{"batchItemFailures": [{"itemIdentifier": msg_id}]}`:**
    o SQS apaga imediatamente da fila todas as mensagens do lote que deram certo e **recoloca na
    fila apenas a mensagem especifica cujo `messageId` foi listado em `batchItemFailures`**.

### Pergunta 3
**Se a coordenadora cair depois de gravar a decisao e antes de publicar o evento, esse comprovante nunca sera gerado (a recuperacao da Parte C nao republica). Isso e aceitavel? Pesquise o padrao outbox e descreva como o aplicaria aqui.**

No teste da secao 10.6 item 8 (quando paramos o LocalStack, fizemos a transferencia `dff8b5b4-...`
e religamos o LocalStack depois), observamos exatamente isso: a transferencia concluiu com
`COMMIT`, a coordenadora registrou `NUVEM_PUBLICACAO_FALHOU`, e quando o LocalStack voltou **o
comprovante daquela transferencia nao existia** (porque a publicacao "melhor esforco" em
memoria na thread não é reexecutada). Da mesma forma, no Cenario 4 da Parte D
(`coordenador-apos-decidir`), a coordenadora cai na linha anterior a `eventos_nuvem.publicar_decisao(coord)`,
entao na recuperacao a Fase 2 e reentregue aos participantes, mas o evento SNS nunca e enviado.

Para um banco real, perder comprovantes/eventos de auditoria de transferencias que comitaram
**nao e aceitavel**. A solucao classica de arquitetura e o **Transactional Outbox Pattern**:
  1. **Gravacao atomica junto com a decisao:** no momento em que o coordenador decide `COMMIT`
     ou `ABORT` e chama `estado.salvar()`, ele inclui o evento pendente de nuvem dentro do
     **mesmo arquivo/transacao duravel** (por exemplo, um campo `"nuvemPublicada": False` dentro
     de `estado.coordenacoes[txId]`, ou uma lista `estado.outbox = [...]` gravada no mesmo
     `os.replace` atomico de `estado-agencia-{id}.json`).
  2. **Publicador assincrono com retentativa (*Outbox Relay*):** uma tarefa periodica (como a
     `reentregar_pendentes()` que ja temos a cada 3s) varre todas as coordenacoes com
     `estado in ("DECIDIDA", "CONCLUIDA")` e `nuvemPublicada == False`, tenta publicar no topico
     SNS e so marca `nuvemPublicada = True` + `estado.salvar()` **depois** que o `sns.publish`
     confirmar HTTP 200.
  3. **Idempotencia na ponta consumidora:** como o *Outbox Relay* pode publicar duas vezes se
     cair logo apos o `sns.publish` e antes de salvar `nuvemPublicada = True`, a Lambda
     `gerar-comprovante` absorve a duplicata sem efeito colateral gracas ao
     `ConditionExpression="attribute_not_exists(txId)"` que ja implementamos.

### Pergunta 4
**Compare, para o ICEIBank, rodar a coordenacao em containers e rodar o comprovante em serverless. O que cada modelo facilita ou dificulta (escala, custo, estado, latencia de partida)? Por que o 2PC seria uma ma ideia dentro de uma funcao serverless?**

| Dimensao | Agencias / Coordenacao 2PC em Containers (CaaS) | Emissao e Consulta de Comprovantes em Serverless (FaaS / Lambda) |
|---|---|---|
| **Estado e Persistencia** | **Facilita:** processo de longa duracao com volume local (`/dados`) anexado, locks em memoria (`RLock`), relogio vetorial em RAM e threads periodicas de heartbeat/reentrega. | **Dificulta:** funcoes sao *stateless* e efemeras; qualquer estado exige chamadas de rede para servicos externos (S3, DynamoDB). |
| **Latencia de Partida** | **Zero *cold start* por requisicao:** o Uvicorn ja esta de pe ouvindo na porta `4046..4048`, respondendo votos do 2PC em poucos milissegundos. | **Sofre de *cold start*:** como vimos na primeira execucao da Lambda no LocalStack (~8-10s para subir o container do runtime Python), a partida a frio adiciona latencia. |
| **Escala e Custo** | **Custo continuo:** os 3 containers precisam ficar ligados 24/7 por causa do heartbeat do Bully e da coordenacao, mesmo sem clientes transferindo. | **Escala a zero (*pay-per-use*):** so roda e so cobra nos milissegundos em que uma transferencia termina (via SQS) ou alguem consulta um comprovante (via API Gateway). |

**Por que rodar o protocolo 2PC (coordenador e participantes) dentro de funcoes serverless (Lambda) seria uma ma ideia:**
  1. **Ausencia de identidade fixa e enderecamento direto entre pares:** o Bully e o 2PC exigem
     $N$ nos com IDs fixos (`0, 1, 2`) que se conhecem, mantêm heartbeat continuo e fazem
     chamadas diretas aos pares específicos; instâncias Lambda sao anonimas, criadas e destruidas
     sob demanda pelo provedor.
  2. ***Cold start* vs. Timeouts curtos de votacao e bloqueio de recursos:** o 2PC mantem fundos
     reservados (`conta["reservado"]`) e locks enquanto aguarda votos com timeout de 2s. Um
     *cold start* de Lambda na Fase 1 estouraria o timeout de voto, abortando transferencias
     validas; e esperar timers de reentrega/resolucao dentro de uma Lambda cobraria tempo de
     execucao ocioso (anti-padrao de FaaS).
  3. **Recuperacao pos-queda (`recuperar()` e `resolver_em_duvida()`):** no 2PC, o processo que
     caiu precisa **voltar ao ar sozinho** (`restart: on-failure`) e varrer seu disco local para
     destravar transacoes em duvida. Uma funcao Lambda nao "volta ao ar sozinha" nem tem disco
     persistente proprio entre invocacoes se nenhum evento externo a invocar.

### Pergunta 5
**O LocalStack e um emulador. Cite um aspecto em que a AWS real pode se comportar de forma diferente e que voce so descobriria ao implantar de verdade (pense em permissoes, limites, latencia e custos).**

Tres diferencas criticas que so aparecem na AWS real:
  1. **Rigidez do IAM (Permissoes de menor privilegio):** no `init.sh` do LocalStack, criamos a
     `lambda-role` apenas com a *trust policy* `sts:AssumeRole` e **sem anexar nenhuma *permission
     policy* de `s3:PutObject`, `s3:GetObject`, `dynamodb:PutItem`, `dynamodb:GetItem` ou
     `sqs:ReceiveMessage`**, e o LocalStack permitiu tudo por padrao. Na AWS real, a Lambda
     falharia imediatamente com `AccessDeniedException` ate anexarmos politicas IAM explicitas
     para o ARN do bucket S3, da tabela DynamoDB, da fila SQS e do CloudWatch Logs.
  2. **Rede e VPC entre Containers e Servicos AWS:** no Docker Compose, as agencias e o
     LocalStack estao na mesma bridge Docker (`http://localstack:4566`). Na AWS real, containers
     em subnets privadas (ECS/EKS) precisariam de **NAT Gateway** ou **VPC Endpoints
     (PrivateLink)** para alcancar o SNS, alem de Security Groups e rotas configuradas.
  3. **Nomes globais do S3, propagacao eventual e custos:** na AWS real, o nome do bucket
     `iceibank-comprovantes` precisa ser **globalmente unico em toda a AWS** (provavelmente ja
     existiria e falharia com `BucketAlreadyExists`), mudancas de IAM/API Gateway levam segundos
     para propagar, e loops de reentrega mal configurados sem *Dead-Letter Queue (DLQ)* geram
     cobranca real de invocacoes Lambda e requisicoes SQS/DynamoDB.

---

## Declaracao de Uso Responsavel de IA (Nota de Transparencia)

Em conformidade com a Nota de Transparencia do roteiro da disciplina, declaro que ferramentas de
Inteligencia Artificial (assistente de codigo no ambiente Antigravity / Claude) foram utilizadas
como apoio para traducao da referencia Node.js/Express do roteiro para Python/FastAPI, revisao
de concorrencia (`threading.RLock` e `asyncio`), estruturacao da interface mobile em Flutter e
organizacao da documentacao. Todos os modulos, containers Docker, cenarios de injecao de falhas
do 2PC e recursos serverless no LocalStack foram executados, testados localmente e validados por
mim, estando apto a explicar e defender integralmente o funcionamento de cada trecho entregue.
