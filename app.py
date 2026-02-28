import os

import streamlit as st

from src.db import get_recent, get_stats, init_db, save_attempt
from src.question_engine import generate_question, load_blocks
from src.reference_engine import (
    auto_ingest_local_references,
    build_explanation_context,
    build_style_context,
    get_default_reference_files,
    get_reference_labels,
    ingest_pdf_file,
)

st.set_page_config(page_title="HematoQuest", page_icon="🩸", layout="wide")

init_db()
blocks = load_blocks()
temas = ["Todos"] + sorted({item["tema"] for item in blocks})

auto_ingest_local_references()

st.title("🩸 HematoQuest")
st.caption("Gerador de questões sobre anemias para prática rápida com correção e histórico local.")


def _get_admin_password() -> str:
    secret_password = ""
    try:
        if "HEMATOQUEST_ADMIN_PASSWORD" in st.secrets:
            secret_password = str(st.secrets["HEMATOQUEST_ADMIN_PASSWORD"]).strip()
    except Exception:
        secret_password = ""

    if secret_password:
        return secret_password

    return os.getenv("HEMATOQUEST_ADMIN_PASSWORD", "").strip()


def _show_admin_panel() -> None:
    query_value = str(st.query_params.get("admin", "0")).lower().strip()
    admin_requested = query_value in {"1", "true", "yes"}
    admin_password = _get_admin_password()

    if not admin_requested or not admin_password:
        return

    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False

    with st.sidebar.expander("Admin", expanded=not st.session_state.admin_authenticated):
        if not st.session_state.admin_authenticated:
            typed_password = st.text_input("Senha admin", type="password", key="admin_password_input")
            if st.button("Entrar", key="admin_login_btn", width="stretch"):
                if typed_password == admin_password:
                    st.session_state.admin_authenticated = True
                    st.success("Acesso liberado")
                    st.rerun()
                else:
                    st.error("Senha inválida")
            return

        category_option = st.selectbox(
            "Tipo",
            [
                ("", "Auto (inferir pelo nome)"),
                ("fisiologia", "Fisiologia"),
                ("questoes", "Questões/Provas"),
                ("diretriz", "Diretriz"),
                ("geral", "Geral"),
            ],
            format_func=lambda item: item[1],
            key="admin_category",
        )
        version_label = st.text_input(
            "Versão/Edição (opcional)",
            placeholder="Ex.: Guyton 14ª edição",
            key="admin_version",
        )
        uploaded = st.file_uploader(
            "Enviar PDFs",
            type=["pdf"],
            accept_multiple_files=True,
            key="admin_uploader",
        )

        if st.button("Processar PDFs", key="admin_process_btn", width="stretch"):
            if not uploaded:
                st.warning("Selecione ao menos um PDF")
            else:
                processed = 0
                for pdf in uploaded:
                    ingest_pdf_file(
                        uploaded_file=pdf,
                        category=category_option[0],
                        version_label=version_label,
                    )
                    processed += 1

                auto_ingest_local_references()
                style_files, explanation_files = get_default_reference_files()
                st.session_state.selected_style_files = style_files
                st.session_state.selected_explanation_files = explanation_files
                st.success(f"{processed} arquivo(s) processado(s)")


def _generate_new_question(selected_tema: str) -> None:
    auto_ingest_local_references()

    style_files = st.session_state.get("selected_style_files", [])
    explanation_files = st.session_state.get("selected_explanation_files", [])

    style_context = build_style_context(selected_tema, selected_text_files=style_files)
    explanation_context = build_explanation_context(
        selected_tema,
        selected_text_files=explanation_files,
    )

    st.session_state.question = generate_question(
        selected_tema,
        style_context=style_context,
        explanation_context=explanation_context,
    )
    st.session_state.style_active = bool(style_context)
    st.session_state.explanation_active = bool(explanation_context)
    st.session_state.explanation_sources = get_reference_labels(explanation_files)
    st.session_state.answered = False
    st.session_state.selected_option = None
    if "resposta_radio" in st.session_state:
        del st.session_state["resposta_radio"]

control_col1, control_col2 = st.columns([3, 1])
with control_col1:
    tema = st.selectbox("Tema", temas, key="tema_main")
with control_col2:
    st.write("")
    gerar = st.button("Gerar nova questão", width="stretch", key="gerar_main")

_show_admin_panel()

if "question" not in st.session_state:
    st.session_state.question = None
if "answered" not in st.session_state:
    st.session_state.answered = False
if "selected_option" not in st.session_state:
    st.session_state.selected_option = None
if "style_active" not in st.session_state:
    st.session_state.style_active = False
if "explanation_active" not in st.session_state:
    st.session_state.explanation_active = False
if "explanation_sources" not in st.session_state:
    st.session_state.explanation_sources = []

style_files, explanation_files = get_default_reference_files()
st.session_state.selected_style_files = style_files
st.session_state.selected_explanation_files = explanation_files

if gerar:
    _generate_new_question(tema)

if st.session_state.question is None:
    _generate_new_question(tema)

col1, col2 = st.columns([2, 1])

with col1:
    if st.session_state.question is None:
        st.info("Clique em **Gerar nova questão** para começar.")
    else:
        q = st.session_state.question
        st.subheader("Questão")
        st.write(q.pergunta)

        escolha = st.radio(
            "Selecione sua resposta",
            q.alternativas,
            index=None,
            key="resposta_radio",
        )

        if st.button("Corrigir", type="primary"):
            if escolha is None:
                st.warning("Escolha uma alternativa antes de corrigir.")
            else:
                acertou = escolha == q.resposta_correta
                st.session_state.answered = True
                st.session_state.selected_option = escolha

                save_attempt(
                    {
                        "tema": q.tema,
                        "dificuldade": q.dificuldade,
                        "tipo": q.tipo,
                        "pergunta": q.pergunta,
                        "resposta_usuario": escolha,
                        "resposta_correta": q.resposta_correta,
                        "acertou": acertou,
                        "fonte": q.fonte,
                    }
                )

        if st.session_state.answered:
            acertou = st.session_state.selected_option == q.resposta_correta
            if acertou:
                st.success("✅ Correto!")
            else:
                st.error(f"❌ Incorreto. Resposta correta: **{q.resposta_correta}**")

            st.markdown("**Explicação:**")
            st.write(q.explicacao)
            if st.session_state.explanation_active:
                st.caption("Base teórica: referências selecionadas aplicadas na explicação")
            if st.session_state.explanation_sources:
                preview = st.session_state.explanation_sources[:2]
                extra = len(st.session_state.explanation_sources) - len(preview)
                suffix = f" (+{extra} referência(s))" if extra > 0 else ""
                st.caption(f"Referência bibliográfica: {'; '.join(preview)}{suffix}")
            st.caption(f"Formato: {q.tipo}")
            st.caption(f"Dificuldade estimada: {q.dificuldade}")
            st.caption(f"Fonte: {q.fonte}")

            if st.button("Próxima questão", width="stretch"):
                _generate_new_question(tema)
                st.rerun()

with col2:
    st.subheader("Desempenho")
    stats = get_stats()
    total = stats["total"]
    acertos = stats["acertos"]
    taxa = (acertos / total * 100) if total > 0 else 0

    st.metric("Tentativas", total)
    st.metric("Acertos", acertos)
    st.metric("Taxa de acerto", f"{taxa:.1f}%")

    st.subheader("Últimas tentativas")
    recent = get_recent(limit=8)
    if recent:
        st.dataframe(recent, width="stretch", hide_index=True)
    else:
        st.caption("Sem tentativas ainda.")
