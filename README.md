# HematoQuest

App simples para gerar e praticar questões de anemias com correção automática e histórico local.

## O que já está pronto
- Geração de questões por tema, com formato e dificuldade definidos automaticamente.
- Correção automática com explicação.
- Registro de tentativas em SQLite.
- Conteúdo inicial em JSON para edição rápida.
- Modo offline (`template`) e modo com IA (`llm`, opcional).
- Upload local de PDFs de referência para aproximar linguagem do estilo ENAMED.

## Requisitos
- Python 3.11+

## Rodar localmente
1. Instale dependências:

```bash
pip install -r requirements.txt
```

2. (Opcional) Copie o arquivo de ambiente:

```bash
copy .env.example .env
```

3. Inicie o app:

```bash
streamlit run app.py
```

## Configuração de modo
No `.env`:

- `HEMATOQUEST_MODE=template` → gera questões sem API (recomendado para começar).
- `HEMATOQUEST_MODE=llm` + `OPENAI_API_KEY=...` → tenta gerar com LLM, com fallback automático para template.

## Onde editar conteúdo
- Banco de conhecimento: `data/knowledge_blocks.json`

## Formatos disponíveis no app
- Formato 1 - Vinheta + Diagnóstico + Conduta
- Formato 2 - Diagnóstico + Tratamento
- Formato 3 - Caso curto + Classificação
- Formato 4 - Nível de Atenção / SUS
- Formato 5 - Interpretação de Exames
- Formato 7 - Situação ética / legal
- Formato 8 - Rastreamento / Preventiva
- Formato 9 - Expectante vs intervenção
- Formato 10 - Epidemiológica

## Fluxo de uso
- Escolher apenas o tema.
- (Opcional) Enviar e processar PDFs de referência no menu lateral.
- Gerar nova questão.
- Responder e corrigir.
- Ver, ao final, o formato sorteado e a dificuldade estimada.

## Usar PDF do ENAMED
- No menu lateral, seção **Base ENAMED (PDF)**, envie um ou mais PDFs.
- Clique em **Processar PDFs**.
- Ao gerar questões depois disso, o app usa trechos relevantes para imitar estrutura e linguagem de prova.
- Os arquivos são processados localmente em `data/references/`.

## Observação importante
- Use os PDFs como referência de estilo e conteúdo, evitando reprodução literal de questões protegidas.

Cada bloco possui:
- `tema`
- `diagnostico`
- `pistas`
- `laboratorio`
- `explicacao`
- `fonte`

## Estrutura
- `app.py`: interface Streamlit
- `src/question_engine.py`: geração de questões
- `src/db.py`: persistência SQLite
- `hematoquest.db`: criado automaticamente no primeiro uso

## Publicar para acessar do celular (com PC desligado)
### Streamlit Community Cloud (recomendado)
1. Confirme que o repositório está no GitHub (branch `main`).
2. Acesse https://share.streamlit.io e faça login com GitHub.
3. Clique em **Create app** e preencha:
	- Repository: `francesmirella/HematoQuest`
	- Branch: `main`
	- Main file path: `app.py`
4. Clique em **Deploy**.

O link público ficará no formato:
- `https://hematoquest-xxxx.streamlit.app`

### Secrets (somente se usar modo LLM)
No app publicado, abra **Settings → Secrets** e adicione:

```toml
HEMATOQUEST_MODE = "llm"
OPENAI_API_KEY = "sua_chave_aqui"
```

Se não configurar secrets, o app roda em modo `template` automaticamente.

### Observação importante
- O Streamlit Community Cloud pode entrar em modo de suspensão após período sem uso.
- Ao abrir o link novamente, ele acorda em alguns segundos.

## HematoQuest Web no GitHub Pages (sem Streamlit)

Também há uma versão web estática do HematoQuest em `pages/`, com deploy automático via GitHub Actions.

### Como ativar
1. No GitHub, abra o repositório `francesmirella/HematoQuest`.
2. Vá em **Settings → Pages**.
3. Em **Build and deployment**, selecione **Source: GitHub Actions**.
4. Faça push para `main` (ou execute manualmente o workflow **Deploy GitHub Pages**).

### Link esperado
- `https://francesmirella.github.io/HematoQuest/`

Arquivos da versão web:
- `pages/index.html`
- `pages/styles.css`
- `pages/app.js`

### Opção 2: rodar local em qualquer notebook
- Clonar projeto, instalar `requirements.txt`, executar `streamlit run app.py`.

## Próximo passo recomendado
- Adicionar mais blocos em `data/knowledge_blocks.json` (10–30 por tema) para melhorar variedade e qualidade.
