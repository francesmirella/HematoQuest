import streamlit as st

from src.db import get_recent, get_stats, init_db, save_attempt
from src.question_engine import generate_question, load_blocks
from src.reference_engine import build_style_context, get_reference_catalog, ingest_pdf_file

st.set_page_config(page_title="HematoQuest", page_icon="🩸", layout="wide")

init_db()
blocks = load_blocks()
temas = ["Todos"] + sorted({item["tema"] for item in blocks})

st.title("🩸 HematoQuest")
st.caption("Gerador de questões sobre anemias para prática rápida com correção e histórico local.")


def _generate_new_question(selected_tema: str) -> None:
    style_context = build_style_context(selected_tema)
    st.session_state.question = generate_question(selected_tema, style_context=style_context)
    st.session_state.style_active = bool(style_context)
    st.session_state.answered = False
    st.session_state.selected_option = None
    if "resposta_radio" in st.session_state:
        del st.session_state["resposta_radio"]

with st.sidebar:
    st.subheader("Configuração da questão")
    tema = st.selectbox("Tema", temas)
    gerar = st.button("Gerar nova questão", width="stretch")

    st.divider()
    st.subheader("Base de referência (PDF)")
    uploaded_pdfs = st.file_uploader(
        "Enviar PDFs (provas, diretrizes, livros)",
        type=["pdf"],
        accept_multiple_files=True,
        help="Os PDFs são processados localmente para extrair linguagem clínica e melhorar a qualidade das explicações.",
    )
    if st.button("Processar PDFs", width="stretch"):
        if uploaded_pdfs:
            processed = 0
            total_pages = 0
            for pdf in uploaded_pdfs:
                result = ingest_pdf_file(pdf)
                processed += 1
                total_pages += result["pages"]
            st.success(f"{processed} PDF(s) processado(s), {total_pages} páginas lidas.")
        else:
            st.warning("Envie ao menos 1 PDF para processar.")

    catalog = get_reference_catalog()
    st.caption(f"Referências ativas: {len(catalog)} arquivo(s)")
    st.caption("Você pode incluir livro de fisiologia para reforçar as explicações da correção.")

if "question" not in st.session_state:
    st.session_state.question = None
if "answered" not in st.session_state:
    st.session_state.answered = False
if "selected_option" not in st.session_state:
    st.session_state.selected_option = None
if "style_active" not in st.session_state:
    st.session_state.style_active = False

if gerar:
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
