import streamlit as st
st.set_page_config(page_title="Teste", page_icon="🧪")
st.title("Teste HematoQuest")

st.write("Importando módulos...")

from src.db import init_db
from src.question_engine import generate_question, load_blocks
from src.reference_engine import auto_ingest_local_references

st.write("Inicializando DB...")
init_db()

st.write("Carregando blocos...")
blocks = load_blocks()
st.write(f"✅ {len(blocks)} blocos carregados")

st.write("Auto-ingestão de referências...")
auto_ingest_local_references()
st.write("✅ Referências carregadas")

st.write("Gerando questão de teste...")
q = generate_question("Todos")
st.write(f"✅ Questão gerada: {q.tema}")
st.subheader(q.pergunta[:200] + "...")
