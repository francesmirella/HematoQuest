import os
import re

import streamlit as st

from src.db import clear_history, get_recent, get_stats, init_db, save_attempt
from src.question_engine import SUPPORTED_THEMES, generate_question_pool, load_blocks
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
available_themes = {item["tema"] for item in blocks}
temas = ["Todos"] + [theme for theme in SUPPORTED_THEMES if theme in available_themes]

auto_ingest_local_references()

st.title("🩸 HematoQuest")
st.caption("Gerador de questões sobre anemias para prática rápida com correção e histórico local.")


def _parse_box_table_rows(table_text: str) -> list[dict[str, str]]:
    lines = [line.rstrip() for line in table_text.splitlines() if line.strip()]
    content_lines = [line for line in lines if "│" in line and "Exame" not in line]

    rows: list[dict[str, str]] = []
    for line in content_lines:
        parts = [chunk.strip() for chunk in line.strip("│").split("│")]
        if len(parts) >= 3:
            rows.append(
                {
                    "Exame": parts[0],
                    "Resultado": parts[1],
                    "Referência": parts[2],
                }
            )
    return rows


def _parse_pipe_table_rows(table_text: str) -> list[dict[str, str]]:
    lines = [line.strip() for line in table_text.splitlines() if line.strip()]
    rows: list[dict[str, str]] = []

    for line in lines:
        if "|" not in line or line.lower().startswith("exame |"):
            continue
        parts = [chunk.strip() for chunk in line.split("|")]
        if len(parts) >= 3:
            rows.append(
                {
                    "Exame": parts[0],
                    "Resultado": parts[1],
                    "Referência": parts[2],
                }
            )
    return rows


def _extract_table_from_question(question_text: str) -> tuple[str, list[dict[str, str]], str]:
    if "┌" in question_text and "┘" in question_text:
        before, after_start = question_text.split("┌", 1)
        boxed = "┌" + after_start
        boxed_table, after = boxed.rsplit("┘", 1)
        rows = _parse_box_table_rows(boxed_table + "┘")
        return before.strip(), rows, after.strip()

    marker = "Exames laboratoriais:"
    if marker in question_text:
        before, after_start = question_text.split(marker, 1)
        after_start = after_start.lstrip("\n")
        chunks = after_start.split("\n\n", 1)
        maybe_table = chunks[0]
        after = chunks[1] if len(chunks) > 1 else ""
        rows = _parse_pipe_table_rows(maybe_table)
        if rows:
            return before.strip(), rows, after.strip()

    return question_text.strip(), [], ""


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

        st.divider()
        st.markdown("**Resumo interno do banco de questões (oculto do aluno)**")

        pools = st.session_state.get("question_pools", {})
        if pools:
            rows = []
            for pool_theme, questions in pools.items():
                unique_types = sorted({q.tipo for q in questions}) if questions else []
                unique_objectives = sorted({q.objetivo for q in questions}) if questions else []
                avg_stem_size = (
                    int(sum(len(q.pergunta) for q in questions) / len(questions))
                    if questions
                    else 0
                )
                rows.append(
                    {
                        "Tema": pool_theme,
                        "Questões restantes": len(questions),
                        "Tipos únicos": len(unique_types),
                        "Objetivos únicos": len(unique_objectives),
                        "Tam. médio enunciado (chars)": avg_stem_size,
                    }
                )

            st.dataframe(rows, hide_index=True, width="stretch")
        else:
            st.caption("Nenhum pool gerado nesta sessão ainda.")


def _generate_new_question(selected_tema: str, regenerate_pool: bool = False) -> None:
    auto_ingest_local_references()

    style_files = st.session_state.get("selected_style_files", [])
    explanation_files = st.session_state.get("selected_explanation_files", [])

    style_context = build_style_context(selected_tema, selected_text_files=style_files)
    explanation_context = build_explanation_context(
        selected_tema,
        selected_text_files=explanation_files,
    )

    question_number = st.session_state.get("question_number", 0) + 1
    st.session_state.question_number = question_number

    if "question_pools" not in st.session_state:
        st.session_state.question_pools = {}

    if (
        regenerate_pool
        or selected_tema not in st.session_state.question_pools
        or not st.session_state.question_pools[selected_tema]
    ):
        hemolitica_profile = "advanced" if selected_tema == "Hemolítica" else "standard"
        st.session_state.question_pools[selected_tema] = generate_question_pool(
            selected_tema,
            style_context=style_context,
            explanation_context=explanation_context,
            count_per_theme=25,
            hemolitica_profile=hemolitica_profile,
        )

    generated_question = st.session_state.question_pools[selected_tema].pop(0)
    generated_question.pergunta = generated_question.pergunta.replace(
        "QUESTÃO X",
        f"QUESTÃO {question_number}",
    )

    st.session_state.question = generated_question
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
if "question_number" not in st.session_state:
    st.session_state.question_number = 0
if "question_pools" not in st.session_state:
    st.session_state.question_pools = {}

style_files, explanation_files = get_default_reference_files()
st.session_state.selected_style_files = style_files
st.session_state.selected_explanation_files = explanation_files

if gerar:
    _generate_new_question(tema, regenerate_pool=True)

if st.session_state.question is None:
    _generate_new_question(tema)

col1, col2 = st.columns([2, 1])

with col1:
    if st.session_state.question is None:
        st.info("Clique em **Gerar nova questão** para começar.")
    else:
        q = st.session_state.question
        st.subheader("Questão")

        pergunta = q.pergunta
        texto_antes, exam_rows, texto_depois = _extract_table_from_question(pergunta)

        if texto_antes:
            st.write(texto_antes)
        if exam_rows:
            st.table(exam_rows)
        if texto_depois:
            st.write(texto_depois)

        escolha = st.radio(
            "Selecione sua resposta",
            q.alternativas,
            index=None,
            key="resposta_radio",
            disabled=st.session_state.answered,
        )

        if st.button(
            "Corrigir",
            type="primary",
            disabled=st.session_state.answered,
        ):
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
                st.rerun()

        if st.session_state.answered:
            acertou = st.session_state.selected_option == q.resposta_correta
            if acertou:
                st.success("✅ Correto!")
            else:
                st.error(f"❌ Incorreto. Resposta correta: **{q.resposta_correta}**")

            st.divider()

            with st.container():
                st.markdown("### 📚 Explicação")
                
                # Formata a explicação em seções visuais (removendo ** do markdown)
                explicacao = q.explicacao.strip()
                # Remove marcações de bold (**texto**) para texto limpo
                explicacao_limpa = re.sub(r'\*\*([^*]+)\*\*', r'\1', explicacao)
                
                explicacao_lines = explicacao_limpa.split("\n\n")
                for paragraph in explicacao_lines:
                    paragraph = paragraph.strip()
                    if not paragraph:
                        continue
                    
                    # Detecta subtítulos (ex: "Fisiopatologia:", "Diagnóstico:")
                    if ":" in paragraph and len(paragraph.split(":")[0]) < 50 and not paragraph.startswith("-"):
                        parts = paragraph.split(":", 1)
                        subtitle = parts[0].strip()
                        content = parts[1].strip() if len(parts) > 1 else ""
                        st.markdown(f'<span style="font-weight: 600; color: #1f4e79;">{subtitle}:</span>', unsafe_allow_html=True)
                        if content:
                            st.write(content)
                    elif paragraph.startswith("-"):
                        # Lista de itens
                        st.write(paragraph)
                    else:
                        st.write(paragraph)
                    
                    st.write("")  # Espaçamento entre parágrafos

            st.divider()
            
            col_info, col_btn = st.columns([2, 1])
            with col_info:
                st.caption(f"📊 Dificuldade: {q.dificuldade}")
                st.caption(f"🎯 Objetivo pedagógico: {q.objetivo}")
            with col_btn:
                if st.button("Próxima questão →", type="primary", use_container_width=True):
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
    
    st.divider()
    with st.expander("⚙️ Opções"):
        if st.button("🗑️ Limpar histórico", use_container_width=True):
            removed = clear_history()
            st.session_state.question_number = 0
            st.success(f"{removed} registro(s) removido(s)")
            st.rerun()
