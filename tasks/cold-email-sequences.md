# Cold-Email Sequences — AskQL

**Produto:** AskQL — Assistente SQL com IA para marketing
**Proposta de valor:** Converte perguntas em português natural para SQL BigQuery em segundos
**Público-alvo:** Marketing managers, growth analysts, coordenadores de marketing digital, data analysts em times de marketing
**Dor principal:** Horas perdidas escrevendo ou pedindo SQL para relatórios — dependência do time de dados para consultas simples
**Tom:** Profissional e direto. Sem jargão corporativo. Parece email de gente, não de ferramenta.

---

## Sequência de envio

| Email | Dia | Objetivo |
|-------|-----|----------|
| Email 1 | Dia 1 | Primeiro contato — chamar atenção, nomear a dor |
| Email 2 | Dia 4 | Follow-up — prova de valor, caso de uso concreto |
| Email 3 | Dia 8 | Último toque — curto, CTA direto |

---

## Email 1 — Primeiro contato (Dia 1)

> **Objetivo:** Nomear uma dor que o prospect reconhece no próprio dia a dia. Não vender ainda — gerar curiosidade.

---

### Variação A

**Assunto:** Você ainda pede SQL pro time de dados para tirar relatório?

---

Oi [Nome],

Sei que você provavelmente tem um backlog enorme de coisas mais importantes para fazer do que ficar esperando uma query.

Mas é isso que acontece: você quer saber quantas conversões vieram do Google Ads na última quinzena, abre um ticket pro time de dados, espera um dia ou dois, recebe o SQL — e quando vai rodar, os dados já mudaram um pouco.

Criei o AskQL pra resolver exatamente isso.

Você digita a pergunta em português mesmo — "quantas vendas vieram do Google Ads em janeiro?" — e recebe o SQL pronto pra rodar no BigQuery. Em segundos. Sem depender de ninguém.

Funciona com as fontes que times de marketing mais usam: Google Ads, Meta Ads, Google Analytics, CRM, e-commerce.

Se fizer sentido, posso te mandar um exemplo com uma pergunta parecida com o que você usa no dia a dia.

Abraços,
[Seu nome]

**CTA:** Resposta simples pedindo um exemplo personalizado — sem link, sem formulário, sem fricção.

---

### Variação B

**Assunto:** Relatório de marketing sem abrir ticket pro time de dados

---

Oi [Nome],

Quantas horas por semana seu time gasta esperando dados?

Pergunto porque esse é o gargalo invisível de quase todo time de marketing que conheço: a análise está na cabeça, mas o SQL trava tudo.

Desenvolvi o AskQL pra fechar esse gap. A ideia é simples: você faz a pergunta em português, ele gera o SQL para o BigQuery na hora. Sem escrever uma linha de código.

Tipo: "qual campanha teve o melhor CPA em fevereiro?" vira uma query completa, pronta para rodar.

Funciona com Google Ads, Meta, Analytics, e-commerce e CRM — as fontes que times de marketing de verdade usam.

Posso te mostrar um exemplo com um caso de uso do seu segmento?

[Seu nome]

**CTA:** Convite informal para ver um exemplo — abre conversa sem pressão de venda.

---

## Email 2 — Follow-up com prova de valor (Dia 4)

> **Objetivo:** Tornar concreto o benefício. Mostrar que funciona com um mini-caso de uso. Ainda sem pitch agressivo — provar antes de pedir.

---

### Variação A

**Assunto:** Re: pergunta rápida — exemplo do AskQL em ação

---

Oi [Nome],

Mandei um email na semana passada sobre o AskQL. Entendo se você está no meio de outras coisas — queria só deixar um exemplo concreto caso faça sentido depois.

Esse foi um caso real de uso:

---

**Pergunta feita no AskQL:**
> "Quais campanhas do Meta Ads tiveram CPA acima de R$ 80 em janeiro, segmentado por objetivo?"

**SQL gerado em menos de 5 segundos:**
```sql
SELECT
  campaign_name,
  objective,
  SUM(spend) AS total_spend,
  SUM(conversions) AS total_conversions,
  SAFE_DIVIDE(SUM(spend), SUM(conversions)) AS cpa
FROM `projeto.meta_ads.campanhas`
WHERE DATE(date) BETWEEN '2024-01-01' AND '2024-01-31'
GROUP BY campaign_name, objective
HAVING cpa > 80
ORDER BY cpa DESC
```

---

A query roda direto no BigQuery. Sem ajuste, sem revisão.

Para um analista que não sabe SQL — ou para um manager que não quer depender do time de dados — isso muda bastante o ritmo de trabalho.

Se quiser, consigo gerar um exemplo com uma pergunta que você usa de verdade no dia a dia. Me manda qualquer uma que vier na cabeça.

[Seu nome]

**CTA:** Convite para mandar uma pergunta real — ativa engajamento e já demonstra o produto ao vivo.

---

### Variação B

**Assunto:** O que acontece quando você digita isso no AskQL

---

Oi [Nome],

Só passando para deixar um caso concreto, já que não tenho certeza se o email anterior chegou na hora certa.

Imagina o cenário: você precisa comparar o ROAS de Google Ads e Meta Ads por canal no último trimestre. Normalmente isso vira um ticket pro time de dados, ou você abre as duas plataformas e exporta manualmente pra cruzar no Excel.

Com o AskQL, você escreve:

> "Compare o ROAS do Google Ads e do Meta Ads por mês no Q4 2024"

E recebe a query cross-source pronta — já com o JOIN entre as duas fontes, agrupamento por mês, cálculo do ROAS. Em segundos.

É isso que a ferramenta faz: elimina o passo de traduzir a pergunta de negócio em SQL.

Se você trabalha com BigQuery e tem essa dor de precisar de dados rápidos sem travar no código, vale ver funcionando ao vivo.

Quer que eu marque 20 minutos para te mostrar?

[Seu nome]

**CTA:** Proposta de demo curta (20 min) — compromisso baixo, valor claro.

---

## Email 3 — Último toque (Dia 8)

> **Objetivo:** Email curto, direto. Não insistir — apenas abrir uma última janela. Quem leu os dois primeiros e não respondeu provavelmente precisa de um empurrão simples.

---

### Variação A

**Assunto:** Última mensagem sobre o AskQL

---

Oi [Nome],

Última vez que entro em contato sobre isso — prometo.

Se SQL ainda é um gargalo no seu time de marketing, o AskQL provavelmente resolve. Se não for uma prioridade agora, tudo bem.

Caso queira ver funcionando em algum momento: [link para demo / site]

Abraço,
[Seu nome]

**CTA:** Link direto para demo ou site — sem texto extra, sem pressão.

---

### Variação B

**Assunto:** Antes de encerrar — uma pergunta

---

Oi [Nome],

Mandei dois emails nos últimos dias e não quero encher sua caixa de entrada.

Só uma pergunta antes de parar: o gargalo de dados para relatórios de marketing é real no seu time hoje?

Se for, vale uma conversa de 15 minutos. Se não for — tudo certo, fica o contato.

[Seu nome]
[link para agendar]

**CTA:** Pergunta direta de qualificação + link para agendar — funciona bem para prospects que leram mas não responderam.

---

## Notas de uso

### Personalização obrigatória antes de enviar

- `[Nome]` — primeiro nome do prospect
- `[Seu nome]` — remetente
- `[link para demo / site]` — URL do AskQL ou Calendly
- Ajuste o segmento/vertical no Email 1 se possível (e-commerce, SaaS, varejo, etc.)

### Dicas de envio

- **Horários:** Terça a quinta, entre 8h e 10h ou 14h e 16h
- **Sender name:** Use nome pessoal, não nome da empresa ("Marina B." converte mais que "AskQL Team")
- **Reply-to:** Mesma caixa que envia — facilita resposta
- **Não adicione anexos** nos primeiros emails — aumenta chance de cair em spam
- **A/B test:** Testar variação A vs B em lotes de 50 por sequência antes de escalar

### Métricas de referência (cold outreach B2B SaaS)

| Métrica | Benchmark | Meta inicial |
|---------|-----------|-------------|
| Open rate | 30–45% | > 35% |
| Reply rate | 5–10% | > 7% |
| Meeting booked | 1–3% | > 2% |

---

*Gerado em: 2026-02-23*
*Revisitar após primeiros 100 envios para ajustar mensagens com base em dados reais de open/reply.*
