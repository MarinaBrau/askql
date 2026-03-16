# PRP: AskQL — Fase 1: UX/UI para Usuario Leigo

## Introduction

A Fase 0 validou que o pipeline NL → SQL funciona bem tecnicamente (28 perguntas, 100% quality checks). Porem, a interface foi construida por e para desenvolvedores. Um profissional de marketing — o usuario-alvo — se depara com jargao tecnico (Project ID, Dataset, Schema, _TABLE_SUFFIX), hierarquia de informacao invertida (SQL antes da explicacao) e zero onboarding.

A Fase 1 foca exclusivamente em tornar o AskQL usavel por alguem que nunca viu o BigQuery. Nenhuma mudanca no core engine — apenas UI, UX e copy.

## Goals

- Eliminar jargao tecnico da interface (0 termos que um marketeiro nao entenderia)
- Inverter hierarquia: explicacao primeiro, SQL como detalhe expandivel
- Criar fluxo de onboarding que funciona sem manual
- Melhorar exemplos e templates para serem acionaveis com 1 clique
- Interface 100% PT-BR (exceto nome do produto)

## Decisoes (Fase 1)

| Decisao | Escolha | Motivo |
|---|---|---|
| Core engine | NAO modificar | Pipeline funciona, foco so em UI |
| Schemas/gotchas | NAO modificar | Conteudo validado |
| Layout Streamlit | Manter `wide` mas com max-width via CSS | Evita linhas de SQL longas demais |
| Idioma | PT-BR completo | Publico brasileiro |
| Modo demo | Sim, com dados de exemplo | Usuario experimenta sem configurar |

---

## User Stories

### US-101: Linguagem amigavel na sidebar
**Descricao:** Como marketeiro, quero entender todos os campos da sidebar sem precisar saber o que e GCP ou BigQuery.

**Acceptance Criteria:**
- [ ] "Project ID (GCP)" → "Projeto Google Cloud" com help: "O nome do seu projeto no Google Cloud. Pergunte ao seu time de dados se nao souber."
- [ ] "Dataset (BigQuery)" → "Base de dados" com help contextual por fonte (ex: "Para GA4, costuma comecar com analytics_")
- [ ] "Estimar custo no BigQuery" → "Verificar custo antes de rodar" com help: "Estima quanto custaria rodar esta consulta no Google"
- [ ] "Fonte de dados" → "De onde vem seus dados?" com descricoes curtas abaixo de cada opcao
- [ ] SOURCE_DISPLAY simplificado: "Google Analytics", "Google Ads", "Meta Ads (Facebook/Instagram)"
- [ ] Subtitulo: "AI SQL Assistant for Marketers" → "Assistente de dados para marketing"
- [ ] Expander "Como encontrar?" reescrito com linguagem simples e screenshots (texto por ora, screenshots futuro)

### US-102: Explicacao primeiro, SQL depois
**Descricao:** Como marketeiro, quero ver a explicacao do que a query faz ANTES do codigo SQL, e o SQL deve ser secundario/colapsavel.

**Acceptance Criteria:**
- [ ] Apos gerar query, exibir PRIMEIRO a explicacao em card destacado (st.success ou container com background)
- [ ] SQL exibido ABAIXO da explicacao dentro de um expander "Ver codigo SQL" (fechado por padrao)
- [ ] Dentro do expander SQL: botao "Copiar SQL" explicito (st.button que copia via JS/pyperclip)
- [ ] Se dry-run ativo: metricas de custo aparecem entre explicacao e SQL
- [ ] Ordem visual: Explicacao → Custo (opcional) → SQL (colapsado)

### US-103: Exemplos clicaveis que geram automaticamente
**Descricao:** Como marketeiro, quero clicar em um exemplo e ver o resultado imediatamente, sem etapa extra.

**Acceptance Criteria:**
- [ ] Botoes de exemplo em grid 2x2 (nao 4 colunas estreitas) com texto completo visivel
- [ ] Clicar no exemplo preenche o campo E dispara a geracao automaticamente (sem precisar clicar "Gerar")
- [ ] Botoes estilizados como cards clicaveis (nao botoes cinza padrao)
- [ ] Placeholder do text_area muda conforme a fonte selecionada
- [ ] Label acima dos exemplos: "Experimente uma pergunta:" (nao "Exemplos de perguntas:")

### US-104: Onboarding e estado vazio
**Descricao:** Como usuario novo, quero entender o que o AskQL faz e como usar quando abro pela primeira vez.

**Acceptance Criteria:**
- [ ] Estado vazio (sem resultado gerado) mostra mensagem de boas-vindas com 3 passos: 1) Escolha a fonte de dados, 2) Faca uma pergunta ou clique em um exemplo, 3) Receba a consulta pronta
- [ ] Se project_id e dataset estao nos valores padrao, mostrar banner discreto (info, nao warning): "Voce esta no modo demonstracao. Para usar com seus dados reais, configure o projeto na barra lateral."
- [ ] Remover o warning agressivo atual quando gera query com valores padrao — a query funciona como demo, nao e um erro
- [ ] Primeira visita: sidebar aberta. Apos gerar primeira query: sidebar pode ser minimizada

### US-105: Tab Templates repensada
**Descricao:** Como marketeiro, quero usar templates prontos de forma simples, com datas legíveis e acao direta.

**Acceptance Criteria:**
- [ ] Substituir inputs de data YYYYMMDD por `st.date_input` (date picker visual)
- [ ] Conversao automatica date picker → YYYYMMDD para _TABLE_SUFFIX nos bastidores
- [ ] Primeiro template da categoria ja vem aberto (nao todos fechados)
- [ ] Cada template tem botao "Usar esta consulta" que copia o SQL com placeholders substituidos
- [ ] Renomear tab: "Templates" → "Consultas prontas"
- [ ] Header: "Templates de Queries" → "Consultas prontas para usar"
- [ ] Categorias com icones: Performance 📊, Budget 💰, Keywords 🔑, Acquisition 📥, etc.

### US-106: Tab Schema repensada
**Descricao:** Como marketeiro, quero entender meus dados sem ver jargao tecnico de banco de dados.

**Acceptance Criteria:**
- [ ] Renomear tab: "Explorar Schema" → "Seus dados"
- [ ] Header: "Explorar Schema" → "Entenda seus dados"
- [ ] Gotchas reescritos como "Dicas de uso" em linguagem simples (ex: "No Meta Ads, o valor gasto ja vem em reais — nao precisa converter")
- [ ] Tabelas mostradas com nomes amigaveis (ex: "Metricas por campanha (diarias)" em vez de `meta_ads_insights_campaign_*`)
- [ ] Campos com descricoes curtas e sem jargao (ex: "Quanto foi gasto" em vez de "Valor gasto em moeda real (NAO esta em micros — usar diretamente)")
- [ ] Separar visualmente campos simples de campos complexos (ARRAY) com label "Dados avancados (requerem tratamento especial)"

### US-107: Estilo visual e polish
**Descricao:** Como usuario, quero uma interface limpa, com boa hierarquia visual e espacamento.

**Acceptance Criteria:**
- [ ] CSS custom via st.markdown para: max-width 1200px no conteudo principal, padding adequado
- [ ] Resultado da query em container com borda/background sutil (st.container com border=True)
- [ ] Spinner melhorado: "Analisando sua pergunta..." (nao "Gerando query com IA...")
- [ ] Botao principal: "Gerar consulta" (nao "Gerar Query")
- [ ] Fonte de dados na sidebar com icones: 📊 Google Analytics, 📢 Google Ads, 📱 Meta Ads
- [ ] Footer discreto: "AskQL by Metricas Boss" com versao
- [ ] Remover emojis dos nomes das tabs (ficam poluidos em telas pequenas) — usar texto limpo

---

## Functional Requirements

- FR-101: Toda a interface deve estar em PT-BR (exceto nome "AskQL")
- FR-102: Nenhum termo tecnico de banco de dados deve aparecer na UI principal (Project ID, Dataset, Schema, SQL, Query, UNNEST, _TABLE_SUFFIX)
- FR-103: A explicacao deve sempre ser exibida antes do codigo SQL
- FR-104: Clicar em exemplo deve gerar resultado automaticamente (max 1 clique)
- FR-105: Datas devem usar date picker, nunca input de texto YYYYMMDD
- FR-106: O app deve funcionar em modo demo sem nenhuma configuracao
- FR-107: Nenhuma mudanca no core engine (query_engine, context_builder, claude_client, sql_validator, schemas, gotchas)

## Non-Goals (Out of Scope — Fase 1)

- Historico de perguntas (sera Fase 2)
- Execucao real de queries no BigQuery
- Exibicao de resultados em tabela/grafico
- Autenticacao de usuarios
- Deploy em cloud
- Mudancas nos schemas ou gotchas
- Mudancas no prompt engineering
- Temas claro/escuro
- Responsividade mobile (foco desktop)

## Technical Considerations

- **Escopo:** Apenas `app.py` e possivelmente 1 arquivo CSS/helper. ZERO mudancas em `core/`, `schemas/`, `templates/`, `validation/`
- **Date picker:** `st.date_input` retorna `datetime.date`, converter para string YYYYMMDD com `.strftime('%Y%m%d')`
- **CSS custom:** Injetar via `st.markdown('<style>...</style>', unsafe_allow_html=True)` no inicio do app
- **Auto-submit exemplos:** Usar `st.session_state` + `st.rerun()` para disparar geracao apos clique
- **Copiar SQL:** `st.code` ja tem botao copiar nativo no Streamlit ≥1.28. Verificar versao
- **Container com borda:** `st.container(border=True)` disponivel no Streamlit ≥1.29

## Success Metrics

- Um marketeiro consegue gerar sua primeira query em < 30 segundos (tempo do onboarding ao resultado)
- 0 termos tecnicos visiveis na tela principal (Project ID, Dataset, Schema, Query, SQL nao aparecem em labels/headers)
- Explicacao aparece antes do SQL em 100% dos resultados
- Exemplos geram resultado com 1 clique (nao 2)
- Date pickers usados em 100% dos inputs de data

## Open Questions

- Adicionar logo/branding da Metricas Boss? (depende de ter o asset)
- Oferecer opcao de "modo avancado" que mostra a interface tecnica atual? Ou apenas simplificar para todos?
- O nome "AskQL" e bom para o publico leigo ou soa tecnico demais? (QL = Query Language)
