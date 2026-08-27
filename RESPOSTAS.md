# RESPOSTAS.md — ICEIBank Sprint 1

## Parte B — Seção 6.4: Perguntas sobre o Relógio de Lamport

---

### Pergunta 1
**Por que `max(contador_local, timestamp_recebido) + 1` ao invés de adotar o timestamp recebido diretamente?**

**Resposta:**

Adotar o timestamp recebido diretamente (`contador = timestamp_recebido`) seria incorreto por dois motivos:

1. **Preservar eventos locais:** Se a agência local já está em um contador maior que o timestamp recebido, descartar o valor local apagaria a memória dos eventos que já aconteceram neste processo. Por isso usamos `max(local, recebido)` — garantimos que o novo contador seja pelo menos tão grande quanto o maior evento já observado, seja local ou remoto.

2. **O recebimento é um evento:** O `+1` é obrigatório porque o próprio ato de receber a mensagem é um evento que deve ter um timestamp **estritamente maior** do que todos os eventos que causaram o envio da mensagem. Se simplesmente adotarmos `max(local, recebido)` sem o `+1`, o recebimento poderia ter o mesmo timestamp que o envio — e não haveria como distinguir qual aconteceu "depois". O `+1` garante a propriedade fundamental do Lamport: se o evento A causou o evento B, então `ts(A) < ts(B)`.

Em resumo: `max` garante que nenhum evento passado seja esquecido; `+1` garante que o recebimento seja logicamente posterior ao envio.

---

### Pergunta 2
**Se a Agência 0 está no contador 10 e recebe uma mensagem com timestamp 3, qual o novo valor? O que isso implica sobre agências rápidas vs. agências lentas?**

**Resposta:**

Novo valor: `max(10, 3) + 1 = 11`

A Agência 0 estava "na frente" (contador 10) enquanto a mensagem vinha de uma agência que estava "atrás" (timestamp 3). O resultado é que o contador local apenas avança em 1 — a mensagem antiga não "atrasa" a agência rápida.

**Implicação sobre agências rápidas vs. lentas:**

- **Uma agência lenta** (com poucos eventos) pode ter um timestamp muito baixo quando envia uma mensagem. Ao receber essa mensagem, uma **agência rápida** (com muitos eventos) simplesmente ignora o timestamp antigo e continua contando a partir do seu próprio estado — exatamente o que aconteceu no exemplo acima.

- O inverso é diferente: se a Agência 0 estivesse no contador 3 e recebesse uma mensagem com timestamp 10, o novo valor seria `max(3, 10) + 1 = 11`. A agência lenta "salta" o seu contador para refletir que ela passou a conhecer eventos mais avançados.

- **Conclusão:** O Relógio de Lamport não mede tempo real — ele mede **causalidade**. Um contador baixo não significa que a agência é "lenta" no sentido real; significa apenas que ela participou de menos eventos até aquele momento. A regra `max + 1` garante que, após a comunicação, ambas as agências têm um contador que reflete o conhecimento combinado dos eventos de ambas, preservando a relação causal: eventos futuros em qualquer das duas agências terão timestamps maiores que todos os eventos passados conhecidos.
