# PRP: Fase B — Cross-Source JOINs (Backend)

## Introduction

A Fase A documentou relacionamentos intra-source (dentro de cada fonte) e já injeta essa informação no prompt do LLM. A Fase B estende isso para **cross-source** — permitir queries que combinam dados de fontes diferentes (ex: sessões do GA4 vs gasto do Google Ads por dia).

Cross-source queries não têm foreign keys diretas entre fontes. A ligação é feita via **agregação por data** (mais confiável) ou via **UTM parameters** (requer configuração do cliente). O sistema deve ser genérico: qualquer par de fontes que tenha relationships documentado deve funcionar.

Escopo: **backend only** — sem mudanças na UI (sidebar, tabs). A UI será planejada numa fase futura após validar que o backend gera queries cross-source corretas.

## Goals

- Documentar relacionamentos cross-source em formato YAML padronizado (mesmo estilo da Fase A)
- Permitir que `build_context()` e `generate_query()` recebam duas fontes simultâneas
- Injetar schemas de ambas as fontes + regras de alinhamento no prompt do LLM
- Adicionar quality checks específicos para cross-source (date format, currency)
- Manter 100% de compatibilidade com single-source (zero regressão)

## User Stories

### US-001: Criar relationships cross-source
**Description:** Como desenvolvedor, preciso documentar como tabelas de fontes diferentes podem ser combinadas para que o LLM saiba gerar JOINs cross-source.

**Acceptance Criteria:**
- [ ] Criar `schemas/cross_source/relationships.yaml` com relacionamentos entre pares de fontes
- [ ] Documentar GA4 ↔ Google Ads (via data agregada e via UTM params)
- [ ] Documentar GA4 ↔ Meta Ads (via data agregada e via UTM params)
- [ ] Documentar Google Ads ↔ Meta Ads (via data agregada apenas)
- [ ] Cada relacionamento documenta: fontes envolvidas, estratégia de JOIN (date-based vs UTM-based), confiabilidade (alta/média/baixa), conversões necessárias (formato de data, micros vs reais), e exemplo SQL
- [ ] YAML válido e carregável pelo loader

### US-002: Carregar relationships cross-source no loader
**Description:** Como desenvolvedor, preciso que o loader carregue relationships cross-source e os disponibilize para o context_builder.

**Acceptance Criteria:**
- [ ] Nova função `load_cross_source_relationships()` em `schemas/loader.py`
- [ ] Retorna lista de relacionamentos cross-source filtrados por par de fontes
- [ ] Aceita parâmetro `source_a` e `source_b` para filtrar apenas relacionamentos relevantes
- [ ] Funciona mesmo se arquivo não existir (retorna lista vazia)
- [ ] Typecheck passa (mypy/pyright se configurado)

### US-003: Suporte multi-source no context_builder
**Description:** Como desenvolvedor, preciso que `build_context()` aceite uma segunda fonte e monte o prompt com schemas de ambas + regras de alinhamento.

**Acceptance Criteria:**
- [ ] `build_context()` aceita parâmetro opcional `secondary_source`, `secondary_dataset`
- [ ] Quando secondary_source é fornecido, inclui schema de ambas as fontes no prompt
- [ ] Inclui seção `## Cross-Source Relationships` com estratégias de JOIN, conversões necessárias, e exemplos
- [ ] Inclui regras de alinhamento: formatos de data (YYYYMMDD vs YYYY-MM-DD), unidades monetárias (micros vs reais)
- [ ] Quando secondary_source é None, comportamento idêntico ao atual (zero regressão)
- [ ] Prompt total não excede ~10k tokens (manter conciso, não duplicar gotchas inteiras)

### US-004: Suporte multi-source no query_engine
**Description:** Como desenvolvedor, preciso que `generate_query()` aceite uma segunda fonte e passe isso para o context_builder.

**Acceptance Criteria:**
- [ ] `generate_query()` aceita parâmetros opcionais `secondary_source` e `secondary_dataset`
- [ ] Passa parâmetros para `build_context()`
- [ ] `QueryResult` funciona normalmente (sql, explanation, is_safe)
- [ ] Quando parâmetros opcionais não fornecidos, comportamento idêntico ao atual

### US-005: Quality checks cross-source
**Description:** Como desenvolvedor, preciso de quality checks que validem queries cross-source.

**Acceptance Criteria:**
- [ ] Check `cross_source_date_alignment`: se query combina fontes, verifica se há conversão/alinhamento de formato de data (ex: FORMAT_DATE, PARSE_DATE, ou ambos usando mesmo formato)
- [ ] Check `cross_source_currency`: se query combina Google Ads + Meta Ads (ou qualquer fonte com micros + fonte sem micros), verifica se custo foi normalizado
- [ ] Checks registrados em ALL_CHECKS com `applies_to` = ["cross_source"]
- [ ] `run_checks()` aceita parâmetro opcional `is_cross_source` para ativar esses checks
- [ ] Checks existentes (13 da Fase A) continuam passando sem regressão

### US-006: Testes de integração cross-source
**Description:** Como desenvolvedor, preciso validar que o pipeline completo funciona para queries cross-source.

**Acceptance Criteria:**
- [ ] Adicionar 3+ test questions cross-source em `validation/test_questions.py`
- [ ] Perguntas cobrem: GA4+Google Ads (date-based), GA4+Meta Ads (date-based), Google Ads+Meta Ads (date-based)
- [ ] Dry-run validation roda sem erros para todas as perguntas (single + cross-source)
- [ ] Documentar no diário de bordo os resultados

## Functional Requirements

- FR-1: Cross-source relationships documentados em YAML com estratégia de JOIN, confiabilidade, e conversões necessárias
- FR-2: O loader carrega relationships cross-source e filtra por par de fontes
- FR-3: O context_builder monta prompt com schemas de duas fontes quando secondary_source fornecido
- FR-4: O prompt cross-source inclui regras explícitas de alinhamento de data e normalização de moeda
- FR-5: O query_engine aceita secondary_source/dataset sem quebrar interface existente
- FR-6: Quality checks detectam erros comuns em cross-source: datas desalinhadas e moeda sem normalizar
- FR-7: Todos os 13 checks existentes (Fase A) continuam funcionando sem regressão
- FR-8: Queries cross-source complexas incluem aviso na explanation ("resultado pode variar dependendo da configuração de UTMs")

## Non-Goals

- Não haverá mudanças na UI (sidebar, tabs, seletor de fontes) — isso será Fase C
- Não suportaremos JOINs entre 3+ fontes simultaneamente (apenas 2 por vez)
- Não criaremos views materializadas no BigQuery
- Não faremos auto-discovery de relacionamentos
- Não suportaremos fontes não cadastradas no AskQL (CRM, ERP, etc.)
- Não adicionaremos templates cross-source em common_queries.yaml (será Fase C junto com UI)

## Technical Considerations

- **Formato de data difere entre fontes:**
  - GA4: `event_date` = `YYYYMMDD` (string sem hífens)
  - Google Ads: `segments_date` = `YYYY-MM-DD` (string com hífens)
  - Meta Ads: `date_start` = `YYYY-MM-DD` (string com hífens)
  - Alinhamento: converter tudo para `DATE` tipo nativo ou para mesmo formato string

- **Unidades monetárias diferem:**
  - Google Ads: `metrics_cost_micros` (dividir por 1.000.000)
  - Meta Ads: `spend` (já em reais)
  - Cross-source query DEVE normalizar antes de comparar/somar

- **Prompt size:** Incluir schemas de duas fontes dobra o tamanho. Estratégia: incluir schema resumido da secondary_source (apenas tabelas e campos-chave, sem sub_fields detalhados)

- **`_TABLE_SUFFIX` funciona em ambas as fontes**, mas o range precisa ser especificado para cada tabela separadamente

- **Sem foreign key direta:** Cross-source JOINs são sempre via agregação (date-based) ou via campos que dependem de configuração do cliente (UTM params). O LLM deve ser instruído a preferir date-based por ser mais confiável

- **Backward compatibility:** Todos os parâmetros novos são opcionais com default None. Single-source continua funcionando exatamente igual

## Success Metrics

- Zero regressão nos 13 checks existentes (Fase A)
- Cross-source queries geram SQL válido (sem erros de sintaxe) em 90%+ dos dry-run tests
- Quality checks cross-source detectam corretamente: data desalinhada e moeda sem normalizar
- `build_context()` com secondary_source retorna prompt < 10k tokens

## Open Questions

1. GA4 e Google Ads podem estar em projetos GCP diferentes? Se sim, precisa suportar dois project_ids no futuro
2. Para cross-source, as datas devem ser alinhadas automaticamente (interseção dos períodos) ou o LLM decide?
3. Devemos mostrar aviso "experimental" na explanation de queries cross-source?
4. UTM-based JOINs dependem de o cliente ter UTMs configurados corretamente — como comunicar essa limitação?
