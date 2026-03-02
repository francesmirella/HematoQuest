const FALLBACK_QUESTION_BANK = [
  {
    tema: "Ferropriva",
    tipo: "Diagnóstico + conduta",
    enunciado: "Mulher de 34 anos com menorragia e fadiga progressiva. Hb 8,2 g/dL, VCM 69 fL, ferritina 9 ng/mL, TIBC elevado. Qual a melhor hipótese e conduta inicial?",
    opcoes: [
      "Anemia ferropriva; reposição de ferro oral e investigação de perda crônica",
      "Anemia da inflamação; corticoide e suspensão de ferro",
      "Talassemia minor; transfusão imediata",
      "Anemia megaloblástica; iniciar B12 intramuscular",
    ],
    correta: 0,
    explicacao: "O perfil microcítico com ferritina baixa e TIBC alto é compatível com ferropenia. A conduta inicial é repor ferro e investigar sangramento.",
  },
  {
    tema: "Ferropriva",
    tipo: "Interpretação laboratorial",
    enunciado: "Homem de 58 anos com astenia e epigastralgia crônica. Hb 9,1 g/dL, VCM 72 fL, saturação de transferrina 8%. Qual achado reforça ferropenia verdadeira?",
    opcoes: [
      "Ferritina elevada > 200 ng/mL",
      "Ferritina baixa < 30 ng/mL",
      "Reticulocitose importante",
      "Coombs direto positivo",
    ],
    correta: 1,
    explicacao: "Ferritina baixa confirma depleção de estoques. Ferritina alta sugere inflamação ou sobrecarga de ferro.",
  },
  {
    tema: "Megaloblástica",
    tipo: "Diagnóstico diferencial",
    enunciado: "Paciente de 62 anos com parestesias e marcha instável. Hb 7,8 g/dL, VCM 114 fL, neutrófilos hipersegmentados. Qual diagnóstico é mais provável?",
    opcoes: [
      "Anemia ferropriva",
      "Anemia megaloblástica por deficiência de B12",
      "Anemia aplásica",
      "Anemia da inflamação",
    ],
    correta: 1,
    explicacao: "Macrocitose acentuada, hipersegmentação e sintomas neurológicos apontam para deficiência de B12.",
  },
  {
    tema: "Megaloblástica",
    tipo: "Exame confirmatório",
    enunciado: "Na suspeita de deficiência de B12 versus deficiência de folato, qual combinação é mais útil?",
    opcoes: [
      "LDH e bilirrubina indireta",
      "Haptoglobina e Coombs",
      "Ácido metilmalônico e homocisteína",
      "Ferritina e TIBC",
    ],
    correta: 2,
    explicacao: "Ambos elevam homocisteína, mas ácido metilmalônico se eleva principalmente na deficiência de B12.",
  },
  {
    tema: "Doença crônica",
    tipo: "Interpretação laboratorial",
    enunciado: "Paciente com artrite reumatoide ativa, Hb 10,1 g/dL, VCM 84 fL, ferro sérico baixo e ferritina 230 ng/mL. Melhor interpretação?",
    opcoes: [
      "Anemia da doença crônica",
      "Anemia ferropriva isolada",
      "Deficiência de B12",
      "Hemólise intravascular aguda",
    ],
    correta: 0,
    explicacao: "Ferro baixo com ferritina normal/alta em contexto inflamatório favorece anemia da inflamação.",
  },
  {
    tema: "Doença crônica",
    tipo: "Diagnóstico diferencial",
    enunciado: "Qual exame ajuda a diferenciar anemia da inflamação de anemia mista com ferropenia?",
    opcoes: [
      "Coombs direto",
      "Receptor solúvel de transferrina (sTfR)",
      "Eletroforese de hemoglobina",
      "Dosagem de G6PD",
    ],
    correta: 1,
    explicacao: "sTfR tende a aumentar na ferropenia e costuma permanecer normal na inflamação pura.",
  },
  {
    tema: "Hemolítica",
    tipo: "Padrão laboratorial",
    enunciado: "Paciente com icterícia, colúria e queda de Hb. Qual padrão laboratorial sustenta hemólise?",
    opcoes: [
      "LDH alta, bilirrubina indireta alta e haptoglobina baixa",
      "Ferritina baixa e TIBC alto",
      "Reticulócitos baixos e medula hipocelular",
      "VCM alto e neutrófilos hipersegmentados",
    ],
    correta: 0,
    explicacao: "Esse é o perfil clássico de hemólise periférica.",
  },
  {
    tema: "Hemolítica",
    tipo: "Diferencial AHAI x PTT",
    enunciado: "No diferencial entre AHAI e PTT, qual achado favorece PTT?",
    opcoes: [
      "Coombs direto fortemente positivo com plaquetas normais",
      "Esquizócitos com plaquetopenia importante",
      "Ferritina < 10 ng/mL",
      "Ácido metilmalônico elevado",
    ],
    correta: 1,
    explicacao: "PTT cursa com microangiopatia (esquizócitos) e plaquetopenia marcada.",
  },
  {
    tema: "Aplásica",
    tipo: "Diagnóstico",
    enunciado: "Jovem com sangramento gengival, infecções recorrentes e fadiga. Hemograma: pancitopenia, reticulócitos 0,2%. Melhor hipótese?",
    opcoes: [
      "Anemia aplásica",
      "Anemia hemolítica autoimune",
      "Ferropenia",
      "Talassemia minor",
    ],
    correta: 0,
    explicacao: "Pancitopenia com reticulocitopenia é fortemente sugestiva de falência medular.",
  },
  {
    tema: "Aplásica",
    tipo: "Exame confirmatório",
    enunciado: "Qual exame confirma anemia aplásica e afasta infiltração medular?",
    opcoes: [
      "Eletroforese de hemoglobina",
      "Biópsia de medula óssea",
      "Coombs direto",
      "ADAMTS13",
    ],
    correta: 1,
    explicacao: "A biópsia demonstra hipocelularidade medular sem infiltrado neoplásico difuso.",
  },
];

let QUESTION_BANK = [];

const state = {
  currentQuestion: null,
  stats: loadStats(),
};

const themeSelect = document.getElementById("themeSelect");
const newQuestionBtn = document.getElementById("newQuestionBtn");
const resetStatsBtn = document.getElementById("resetStatsBtn");
const questionType = document.getElementById("questionType");
const questionStem = document.getElementById("questionStem");
const optionsWrap = document.getElementById("options");
const checkBtn = document.getElementById("checkBtn");
const feedback = document.getElementById("feedback");
const explanation = document.getElementById("explanation");
const scoreLine = document.getElementById("scoreLine");

function loadStats() {
  const raw = localStorage.getItem("hematoquest_stats_v1");
  if (!raw) return { correct: 0, wrong: 0 };
  try {
    return JSON.parse(raw);
  } catch {
    return { correct: 0, wrong: 0 };
  }
}

function saveStats() {
  localStorage.setItem("hematoquest_stats_v1", JSON.stringify(state.stats));
}

function updateScoreLine() {
  const total = state.stats.correct + state.stats.wrong;
  const rate = total === 0 ? 0 : Math.round((state.stats.correct / total) * 100);
  scoreLine.textContent = `Acertos: ${state.stats.correct} | Erros: ${state.stats.wrong} | Taxa: ${rate}%`;
}

function pickQuestion() {
  const theme = themeSelect.value;
  const pool = theme === "Todos" ? QUESTION_BANK : QUESTION_BANK.filter(q => q.tema === theme);
  if (!pool.length) return null;
  return pool[Math.floor(Math.random() * pool.length)];
}

async function loadQuestionBank() {
  try {
    const response = await fetch("./questions.json", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Falha ao carregar questions.json: ${response.status}`);
    }
    const payload = await response.json();
    if (!Array.isArray(payload) || payload.length === 0) {
      throw new Error("questions.json vazio ou inválido");
    }
    QUESTION_BANK = payload;
    newQuestionBtn.disabled = false;
    questionStem.textContent = `Banco carregado com ${QUESTION_BANK.length} questões. Clique em Nova questão.`;
  } catch {
    QUESTION_BANK = FALLBACK_QUESTION_BANK;
    newQuestionBtn.disabled = false;
    questionStem.textContent = "Não foi possível carregar o banco completo. Usando banco local reduzido.";
  }
}

function renderQuestion(question) {
  state.currentQuestion = question;
  questionType.textContent = `${question.tipo} · ${question.tema}`;
  questionStem.textContent = question.enunciado;
  feedback.textContent = "";
  feedback.className = "feedback";
  explanation.textContent = "";

  optionsWrap.innerHTML = "";
  question.opcoes.forEach((opt, idx) => {
    const label = document.createElement("label");
    label.className = "option";
    label.innerHTML = `
      <input type="radio" name="answer" value="${idx}" />
      <span>${opt}</span>
    `;
    optionsWrap.appendChild(label);
  });
}

function getSelectedIndex() {
  const checked = document.querySelector("input[name='answer']:checked");
  return checked ? Number(checked.value) : null;
}

function checkAnswer() {
  if (!state.currentQuestion) return;
  const selected = getSelectedIndex();
  if (selected === null) {
    feedback.textContent = "Selecione uma alternativa antes de corrigir.";
    feedback.className = "feedback err";
    return;
  }

  const isCorrect = selected === state.currentQuestion.correta;
  if (isCorrect) {
    state.stats.correct += 1;
    feedback.textContent = "✅ Correto";
    feedback.className = "feedback ok";
  } else {
    state.stats.wrong += 1;
    feedback.textContent = `❌ Incorreto. Resposta correta: ${state.currentQuestion.opcoes[state.currentQuestion.correta]}`;
    feedback.className = "feedback err";
  }

  explanation.textContent = state.currentQuestion.explicacao;
  updateScoreLine();
  saveStats();
}

newQuestionBtn.addEventListener("click", () => {
  const question = pickQuestion();
  if (!question) {
    questionStem.textContent = "Sem questões para este tema.";
    return;
  }
  renderQuestion(question);
});

checkBtn.addEventListener("click", checkAnswer);

resetStatsBtn.addEventListener("click", () => {
  state.stats = { correct: 0, wrong: 0 };
  saveStats();
  updateScoreLine();
});

updateScoreLine();
newQuestionBtn.disabled = true;
loadQuestionBank();
