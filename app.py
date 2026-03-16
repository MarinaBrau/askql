"""AskQL — Assistente de dados para marketing (Fase 1)"""

import os
from datetime import date, timedelta

import streamlit as st
from dotenv import load_dotenv

load_dotenv()


def _validate_config():
    """Valida configurações obrigatórias no startup."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.error(
            "ANTHROPIC_API_KEY não configurada. "
            "Adicione ao arquivo .env ou exporte como variável de ambiente."
        )
        st.stop()


_validate_config()

from core.query_engine import generate_query
from core.bigquery_runner import dry_run_query, run_query, _format_bytes
from schemas.loader import list_sources
from templates.template_library import TemplateLibrary

# --- Page Config ---
st.set_page_config(
    page_title="AskQL",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom CSS (US-107) ---
st.markdown(
    """
    <style>
    .block-container { max-width: 1200px; }
    footer { visibility: hidden; }
    .askql-footer {
        text-align: center;
        color: #888;
        font-size: 0.85em;
        padding: 2rem 0 1rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Constants ---
DEFAULT_VALUES = {"meu-projeto", "analytics_123456789", "google_ads_transfer"}

# US-101: friendly display names
SOURCE_DISPLAY = {
    "ga4_bigquery": "📊 Google Analytics",
    "google_ads": "📢 Google Ads",
    "meta_ads": "📱 Meta Ads (Facebook/Instagram)",
    "vtex": "🛒 VTEX (E-commerce)",
    "shopify": "🛍️ Shopify (E-commerce)",
}

SOURCE_DESCRIPTION = {
    "ga4_bigquery": "Dados de navegação e conversões do seu site",
    "google_ads": "Campanhas, cliques e conversões do Google Ads",
    "meta_ads": "Campanhas e resultados do Facebook e Instagram",
    "vtex": "Pedidos, produtos, estoque e logística do seu e-commerce VTEX",
    "shopify": "Pedidos, clientes, produtos e marketing do seu e-commerce Shopify",
}

EXAMPLE_QUESTIONS = {
    "ga4_bigquery": [
        "Quais são as 10 páginas mais acessadas?",
        "Quais fontes de tráfego geram mais sessões?",
        "Como está meu funil de conversão?",
        "Qual o tempo médio de engajamento por página?",
    ],
    "google_ads": [
        "Qual o CPA de cada campanha?",
        "Como está a tendência de gasto diário?",
        "Quais keywords geram mais conversões?",
        "Qual o ROAS por campanha?",
    ],
    "meta_ads": [
        "Qual o CPA de cada campanha no Meta?",
        "Qual o ROAS por campanha?",
        "Quais campanhas têm maior alcance?",
        "Quais tipos de conversão estão acontecendo?",
    ],
    "vtex": [
        "Qual foi a receita por dia este mês?",
        "Quais são os 10 produtos mais vendidos?",
        "Quais canais de marketing geram mais receita?",
        "Qual o ticket médio por status de pedido?",
    ],
    "shopify": [
        "Qual foi a receita por dia este mês?",
        "Quais são os 10 produtos mais vendidos?",
        "Como está a distribuição de clientes por segmento?",
        "Quais canais de marketing geram mais receita?",
    ],
}

# US-103: contextual placeholders
PLACEHOLDERS = {
    "ga4_bigquery": "Ex: Quais são as 10 páginas mais acessadas no último mês?",
    "google_ads": "Ex: Qual o CPA de cada campanha nos últimos 30 dias?",
    "meta_ads": "Ex: Qual campanha teve o melhor ROAS este mês?",
    "vtex": "Ex: Quais produtos mais vendidos este mês?",
    "shopify": "Ex: Quais produtos mais vendidos este mês?",
}

# US-105: friendly category labels
CATEGORY_ICONS = {
    "aquisicao": "🎯 Aquisição",
    "engajamento": "💡 Engajamento",
    "conversao": "🛒 Conversão",
    "conversoes": "🛒 Conversões",
    "performance": "📈 Performance",
    "custo": "💰 Custo",
    "audiencia": "👥 Audiência",
    "alcance": "📡 Alcance",
    "keywords": "🔑 Keywords",
    "combinando_fontes": "🔗 Combinando fontes",
}

CATEGORY_DESCRIPTION = {
    "performance": "Entenda o retorno das suas campanhas",
    "custo": "Acompanhe quanto está sendo investido",
    "aquisicao": "Descubra de onde vem seus visitantes",
    "engajamento": "Veja como os usuários interagem com seu site",
    "conversao": "Analise vendas e conversões",
    "conversoes": "Analise os tipos de conversão",
    "audiencia": "Conheça o perfil dos seus usuários",
    "alcance": "Veja quantas pessoas suas campanhas atingem",
    "keywords": "Descubra quais palavras-chave performam melhor",
    "combinando_fontes": "Combine dados de fontes diferentes para uma visão completa",
}

CROSS_SOURCE_DISPLAY = {
    frozenset({"ga4_bigquery", "google_ads"}): "📊 GA4 + 📢 Google Ads",
    frozenset({"ga4_bigquery", "meta_ads"}): "📊 GA4 + 📱 Meta Ads",
    frozenset({"google_ads", "meta_ads"}): "📢 Google Ads + 📱 Meta Ads",
    frozenset({"vtex", "google_ads"}): "🛒 VTEX + 📢 Google Ads",
    frozenset({"vtex", "meta_ads"}): "🛒 VTEX + 📱 Meta Ads",
    frozenset({"shopify", "google_ads"}): "🛍️ Shopify + 📢 Google Ads",
    frozenset({"shopify", "meta_ads"}): "🛍️ Shopify + 📱 Meta Ads",
    frozenset({"ga4_bigquery", "vtex"}): "📊 GA4 + 🛒 VTEX",
    frozenset({"ga4_bigquery", "shopify"}): "📊 GA4 + 🛍️ Shopify",
    frozenset({"vtex", "shopify"}): "🛒 VTEX + 🛍️ Shopify",
}


@st.cache_resource
def _get_template_library():
    return TemplateLibrary()


# --- Sidebar (US-101) ---
DATASET_HELP = {
    "ga4_bigquery": "O dataset do GA4 tem o formato analytics_ seguido de 9 dígitos. Você encontra esse nome no BigQuery ou em GA4 > Admin > BigQuery Links.",
    "google_ads": "O dataset do Google Ads costuma se chamar google_ads_transfer. Você encontra no BigQuery, dentro do seu projeto.",
    "meta_ads": "Procure o dataset com tabelas do Meta Ads no BigQuery. O nome depende de como os dados foram importados.",
    "vtex": "O dataset da VTEX é vtex_treated (pipeline padrão Métricas Boss). Você encontra no BigQuery, dentro do seu projeto.",
    "shopify": "O dataset do Shopify é shopify_treated (pipeline padrão Métricas Boss). Você encontra no BigQuery, dentro do seu projeto.",
}

DATASET_DEFAULTS = {
    "ga4_bigquery": "analytics_123456789",
    "google_ads": "google_ads_transfer",
    "meta_ads": "meta_ads",
    "vtex": "vtex_treated",
    "shopify": "shopify_treated",
}


def render_sidebar():
    st.sidebar.title("AskQL")
    st.sidebar.caption("Assistente de dados para marketing")
    st.sidebar.divider()

    sources = list_sources()
    source_labels = [SOURCE_DISPLAY.get(s, s) for s in sources]
    selected_label = st.sidebar.selectbox("De onde vem seus dados?", source_labels)
    selected_source = sources[source_labels.index(selected_label)]

    # Source description
    desc = SOURCE_DESCRIPTION.get(selected_source, "")
    if desc:
        st.sidebar.caption(desc)

    st.sidebar.divider()

    project_id = st.sidebar.text_input(
        "Projeto Google Cloud",
        value="meu-projeto",
        help="O identificador do seu projeto. Aparece no topo do console.cloud.google.com — ex: meu-projeto-prod",
    )
    dataset = st.sidebar.text_input(
        "Base de dados",
        value=DATASET_DEFAULTS.get(selected_source, "my_dataset"),
        help=DATASET_HELP.get(selected_source, "Nome da base de dados no BigQuery"),
    )

    # --- Help expander (US-101) ---
    with st.sidebar.expander("Não sei essas informações"):
        st.markdown(
            "**Projeto Google Cloud:**\n"
            "1. Acesse [console.cloud.google.com](https://console.cloud.google.com)\n"
            "2. O nome do projeto aparece no seletor no topo da página\n"
            "3. Copie o **ID** (não o nome) — ex: `meu-projeto-prod`"
        )
        st.markdown("---")
        if selected_source == "ga4_bigquery":
            st.markdown(
                "**Base de dados (GA4):**\n"
                "1. No BigQuery, expanda seu projeto na barra lateral\n"
                "2. Procure a base que começa com `analytics_`\n"
                "3. O número após `analytics_` é o Stream ID do GA4\n"
                "4. Você também encontra em **GA4 > Admin > BigQuery Links**"
            )
        elif selected_source == "google_ads":
            st.markdown(
                "**Base de dados (Google Ads):**\n"
                "1. No BigQuery, expanda seu projeto na barra lateral\n"
                "2. Procure a base com tabelas `ads_CampaignStats_*`\n"
                "3. O nome padrão é `google_ads_transfer`\n"
                "4. Você também encontra em **BigQuery > Data Transfers**"
            )
        elif selected_source == "vtex":
            st.markdown(
                "**Base de dados (VTEX):**\n"
                "1. No BigQuery, expanda seu projeto na barra lateral\n"
                "2. Procure a base chamada `vtex_treated`\n"
                "3. Ela contém as tabelas `orders_treated`, `order_items_treated`, etc.\n"
                "4. Criada pelo pipeline Métricas Boss para VTEX"
            )
        elif selected_source == "shopify":
            st.markdown(
                "**Base de dados (Shopify):**\n"
                "1. No BigQuery, expanda seu projeto na barra lateral\n"
                "2. Procure a base chamada `shopify_treated`\n"
                "3. Ela contém as tabelas `orders_treated`, `customers_treated`, etc.\n"
                "4. Criada pelo pipeline Métricas Boss para Shopify"
            )
        else:
            st.markdown(
                "**Base de dados (Meta Ads):**\n"
                "1. No BigQuery, expanda seu projeto\n"
                "2. Localize a base onde os dados do Meta foram carregados"
            )

    # --- Cross-source toggle ---
    st.sidebar.divider()
    enable_cross = st.sidebar.toggle(
        "Combinar com outra fonte",
        value=False,
        help="Permite fazer perguntas que combinam dados de duas fontes diferentes (ex: sessões do GA4 vs gastos do Google Ads)",
    )

    secondary_source = None
    secondary_dataset = None
    if enable_cross:
        other_sources = [s for s in sources if s != selected_source]
        other_labels = [SOURCE_DISPLAY.get(s, s) for s in other_sources]
        selected_secondary_label = st.sidebar.selectbox("Segunda fonte", other_labels)
        secondary_source = other_sources[other_labels.index(selected_secondary_label)]
        secondary_dataset = st.sidebar.text_input(
            "Base de dados (segunda fonte)",
            value=DATASET_DEFAULTS.get(secondary_source, "my_dataset"),
            help=DATASET_HELP.get(secondary_source, "Nome da base de dados no BigQuery"),
        )
        st.sidebar.caption(f"Combinando **{SOURCE_DISPLAY.get(selected_source, selected_source)}** + **{SOURCE_DISPLAY.get(secondary_source, secondary_source)}**")

    st.sidebar.divider()
    enable_dryrun = st.sidebar.toggle(
        "Verificar custo antes de rodar",
        value=False,
        help="Verifica quantos dados serão processados e o custo estimado antes de executar a consulta",
    )

    return selected_source, project_id, dataset, enable_dryrun, secondary_source, secondary_dataset


# --- Tab: Perguntar (US-102, US-103, US-104) ---
def render_tab_perguntar(source_name, project_id, dataset, enable_dryrun, secondary_source=None, secondary_dataset=None):
    # US-103: auto-submit from example click
    auto_q = st.session_state.pop("example_clicked", None)

    st.header("Pergunte sobre seus dados")
    if secondary_source:
        st.caption(f"Fontes: **{SOURCE_DISPLAY.get(source_name, source_name)}** + **{SOURCE_DISPLAY.get(secondary_source, secondary_source)}** · Projeto: `{project_id}`")
    else:
        st.caption(f"Fonte: **{SOURCE_DISPLAY.get(source_name, source_name)}** · Projeto: `{project_id}` · Base: `{dataset}`")

    # Example questions — grid 2x2 (US-103)
    examples = EXAMPLE_QUESTIONS.get(source_name, [])
    if examples:
        st.markdown("**Experimente uma pergunta:**")
        row1_cols = st.columns(2)
        row2_cols = st.columns(2)
        grid = [row1_cols[0], row1_cols[1], row2_cols[0], row2_cols[1]]
        for i, example in enumerate(examples[:4]):
            if grid[i].button(example, key=f"example_{i}", use_container_width=True):
                st.session_state["example_clicked"] = example
                st.rerun()

    # Question input
    question_value = auto_q or st.session_state.get("question", "")
    question = st.text_area(
        "Sua pergunta",
        value=question_value,
        height=100,
        placeholder=PLACEHOLDERS.get(source_name, "Digite sua pergunta sobre os dados..."),
        key="question_input",
    )

    # Sync from session state
    if "question" in st.session_state and st.session_state.get("question") != question:
        question = st.session_state["question"]

    col1, col2 = st.columns([1, 5])
    generate_clicked = col1.button("Gerar consulta", type="primary", use_container_width=True)

    # Auto-submit when example was clicked
    if auto_q:
        _generate_and_display(source_name, project_id, dataset, auto_q, enable_dryrun, secondary_source, secondary_dataset)
    elif generate_clicked and question.strip():
        _generate_and_display(source_name, project_id, dataset, question, enable_dryrun, secondary_source, secondary_dataset)
    elif generate_clicked and not question.strip():
        st.warning("Digite uma pergunta antes de gerar a consulta.")
    elif "last_result" in st.session_state:
        # Show previous result
        _display_result(st.session_state["last_result"], enable_dryrun, project_id)
    else:
        # US-104: onboarding — empty state
        _display_onboarding()

    # US-104: demo mode info
    if project_id in DEFAULT_VALUES or dataset in DEFAULT_VALUES:
        st.info(
            "Você está usando valores de demonstração. A consulta será gerada normalmente — "
            "para executar no BigQuery, preencha seus dados reais na barra lateral."
        )


def _display_onboarding():
    """US-104: Welcome card for first-time users."""
    with st.container(border=True):
        st.markdown("### Bem-vindo ao AskQL!")
        st.markdown(
            "Faça perguntas sobre seus dados de marketing em português e receba "
            "consultas prontas para rodar no BigQuery."
        )
        st.markdown(
            "**Como usar:**\n"
            "1. Escolha a fonte de dados na barra lateral\n"
            "2. Preencha o projeto e a base de dados\n"
            "3. Digite sua pergunta ou clique em um exemplo acima"
        )


def _generate_and_display(source_name, project_id, dataset, question, enable_dryrun, secondary_source=None, secondary_dataset=None):
    # Limpa resultado de execução anterior ao gerar nova query
    st.session_state.pop("last_execution", None)

    with st.spinner("Analisando sua pergunta..."):
        try:
            result = generate_query(
                source_name=source_name,
                project_id=project_id,
                dataset=dataset,
                question=question,
                secondary_source=secondary_source,
                secondary_dataset=secondary_dataset,
            )
            st.session_state["last_result"] = {
                "sql": result.sql,
                "explanation": result.explanation,
                "is_safe": result.is_safe,
                "validation_message": result.validation_message,
                "is_cross_source": secondary_source is not None,
            }
            _display_result(st.session_state["last_result"], enable_dryrun, project_id)
        except EnvironmentError as e:
            st.error(f"Erro de configuração: {e}")
        except Exception as e:
            st.error(f"Erro ao gerar consulta: {e}")


def _display_result(result, enable_dryrun, project_id):
    """US-102: Explanation first, SQL in collapsed expander."""
    if not result["is_safe"]:
        st.error(f"Consulta bloqueada: {result['validation_message']}")
        st.code(result["sql"], language="sql")
        return

    # 1. Explanation first (green box)
    if result["explanation"]:
        st.success(result["explanation"])

    # Cross-source warning
    if result.get("is_cross_source"):
        st.warning(
            "**Consulta cross-source (experimental)** — Esta consulta combina dados de fontes diferentes. "
            "Os resultados dependem do alinhamento de datas entre as fontes e, para queries baseadas em campanha, "
            "de UTMs estarem configurados corretamente."
        )

    # 2. Cost metrics (if dry-run enabled)
    if enable_dryrun and result["sql"]:
        with st.spinner("Verificando custo..."):
            dryrun = dry_run_query(result["sql"], project_id=project_id)
        if dryrun["success"]:
            col1, col2 = st.columns(2)
            col1.metric("Dados processados", dryrun["bytes_display"])
            col2.metric("Custo estimado", dryrun["estimated_cost_display"])
        else:
            st.warning(f"Não foi possível verificar o custo: {dryrun['error']}")

    # 3. SQL in collapsed expander
    with st.expander("Ver código da consulta"):
        st.code(result["sql"], language="sql")

    # 4. Execute button (outside expander)
    if st.button("Executar no BigQuery", type="secondary", key="btn_execute"):
        with st.spinner("Executando consulta..."):
            exec_result = run_query(result["sql"], project_id=project_id)
        st.session_state["last_execution"] = exec_result

    # 5. Execution result (outside expander, always visible)
    exec_result = st.session_state.get("last_execution")
    if exec_result is not None:
        if exec_result["success"]:
            cost_str = f"US$ {exec_result['cost_usd']:.4f}" if exec_result["cost_usd"] < 0.01 else f"US$ {exec_result['cost_usd']:.2f}"
            if exec_result["rows_returned"] == 0:
                st.info("Nenhum resultado encontrado para esta consulta.")
            else:
                st.dataframe(exec_result["dataframe"], use_container_width=True)
            st.caption(f"{exec_result['rows_returned']} linha(s) · {_format_bytes(exec_result['bytes_processed'])} processados · {cost_str}")
        elif exec_result["cost_usd"] > 0:
            st.warning(exec_result["error"])
        else:
            st.error(exec_result["error"])


# --- Tab: Templates (US-105) ---
def render_tab_templates(source_name, project_id, dataset):
    st.header("Consultas prontas para usar")
    st.caption(f"Consultas prontas para **{SOURCE_DISPLAY.get(source_name, source_name)}**")

    lib = _get_template_library()
    templates = lib.get_templates(source_name)

    if not templates:
        st.info("Nenhuma consulta pronta disponível para esta fonte de dados.")
        return

    # Category filter with friendly labels
    categories = lib.get_categories(source_name)
    category_labels = ["Todas"] + [CATEGORY_ICONS.get(cat, cat.capitalize()) for cat in categories]
    selected_cat_label = st.selectbox("Filtrar por categoria", category_labels)

    if selected_cat_label == "Todas":
        filtered = templates
    else:
        # Reverse-lookup the original category key
        selected_cat = None
        for cat in categories:
            if CATEGORY_ICONS.get(cat, cat.capitalize()) == selected_cat_label:
                selected_cat = cat
                break
        filtered = lib.filter_by_category(source_name, selected_cat) if selected_cat else templates

    st.caption(f"{len(filtered)} consulta(s)")

    # Date inputs with st.date_input (US-105)
    col1, col2 = st.columns(2)
    default_start = date(2026, 1, 1)
    default_end = date.today()
    date_start = col1.date_input("Data início", value=default_start, key="tmpl_date_start")
    date_end = col2.date_input("Data fim", value=default_end, key="tmpl_date_end")

    # Display templates
    for i, tmpl in enumerate(filtered):
        cat_label = CATEGORY_ICONS.get(tmpl.get("category", ""), tmpl.get("category", "").capitalize())
        with st.expander(f"**{tmpl['title']}** — _{cat_label}_", expanded=(i == 0)):
            # Explanation BEFORE SQL (US-105)
            if tmpl.get("explanation"):
                st.info(tmpl["explanation"])

            st.markdown(f"**Pergunta:** {tmpl.get('natural_language', '')}")

            # Replace placeholders in SQL
            sql = tmpl.get("sql", "")
            sql = sql.replace("{project_id}", project_id)
            sql = sql.replace("{dataset}", dataset)
            sql = sql.replace("{date_start}", date_start.strftime("%Y%m%d"))
            sql = sql.replace("{date_end}", date_end.strftime("%Y%m%d"))

            st.code(sql, language="sql")


# --- Tab: Capabilities ---
def render_tab_capabilities():
    st.header("O que posso perguntar?")
    st.caption("Veja exemplos de perguntas para cada fonte de dados")

    lib = _get_template_library()
    sources = list_sources()

    for source in sources:
        categories = lib.get_categories(source)
        if not categories:
            continue

        display = SOURCE_DISPLAY.get(source, source)
        st.subheader(display)

        for cat in categories:
            templates = lib.filter_by_category(source, cat)
            if not templates:
                continue

            icon_label = CATEGORY_ICONS.get(cat, cat.capitalize())
            description = CATEGORY_DESCRIPTION.get(cat, "")

            with st.container(border=True):
                st.markdown(f"### {icon_label}")
                if description:
                    st.caption(description)

                for j, tmpl in enumerate(templates):
                    question = tmpl.get("natural_language", tmpl.get("title", ""))
                    explanation = tmpl.get("explanation", "")

                    col_q, col_btn = st.columns([5, 1])
                    col_q.markdown(f"**{question}**")
                    if explanation:
                        col_q.caption(explanation[:120])
                    if col_btn.button("Perguntar →", key=f"cap_{source}_{cat}_{j}", use_container_width=True):
                        st.session_state["example_clicked"] = question
                        st.rerun()

        st.divider()

    # --- Cross-source section ---
    cross_templates = lib.get_templates("cross_source")
    if cross_templates:
        st.subheader("🔗 Combinando fontes")
        st.caption("Perguntas que cruzam dados de fontes diferentes — ative 'Combinar com outra fonte' na barra lateral")

        # Group by source pair
        grouped = {}
        for tmpl in cross_templates:
            pair = frozenset(tmpl.get("sources", []))
            grouped.setdefault(pair, []).append(tmpl)

        for pair, tmpls in grouped.items():
            pair_label = CROSS_SOURCE_DISPLAY.get(pair, " + ".join(pair))

            with st.container(border=True):
                st.markdown(f"### {pair_label}")

                for j, tmpl in enumerate(tmpls):
                    question = tmpl.get("natural_language", tmpl.get("title", ""))
                    explanation = tmpl.get("explanation", "")

                    col_q, col_btn = st.columns([5, 1])
                    col_q.markdown(f"**{question}**")
                    if explanation:
                        col_q.caption(explanation[:120])
                    if col_btn.button("Perguntar →", key=f"cap_cross_{hash(pair)}_{j}", use_container_width=True):
                        st.session_state["example_clicked"] = question
                        st.rerun()


# --- Main ---
TAB_OPTIONS = ["Perguntar", "Consultas prontas", "O que posso perguntar?"]


def main():
    source_name, project_id, dataset, enable_dryrun, secondary_source, secondary_dataset = render_sidebar()

    # Se example_clicked veio da tab capabilities, forçar aba Perguntar
    if "example_clicked" in st.session_state:
        st.session_state["active_tab"] = "Perguntar"

    active_tab = st.segmented_control(
        "Navegação",
        TAB_OPTIONS,
        default=st.session_state.get("active_tab", "Perguntar"),
        key="active_tab",
        label_visibility="collapsed",
    )

    if active_tab == "Perguntar":
        render_tab_perguntar(source_name, project_id, dataset, enable_dryrun, secondary_source, secondary_dataset)
    elif active_tab == "Consultas prontas":
        render_tab_templates(source_name, project_id, dataset)
    elif active_tab == "O que posso perguntar?":
        render_tab_capabilities()

    # US-107: footer
    st.markdown(
        '<div class="askql-footer">AskQL by Marina Braune · v0.2</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
