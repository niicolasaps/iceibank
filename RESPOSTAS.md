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
