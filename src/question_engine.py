import json
import os
import random
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

FORMAT_LABELS = {
    "1": "Diagnóstico + Conduta + Complicação",
    "2": "Diagnóstico + Tratamento de primeira linha",
    "3": "Caso clínico + Classificação",
    "4": "Nível de atenção + Prevenção",
    "5": "Interpretação laboratorial + Conduta",
}

FORMAT_DIFFICULTY = {
    "1": "difícil",
    "2": "difícil",
    "3": "média",
    "4": "média",
    "5": "difícil",
}

FORMAT_WEIGHTS = ["1", "1", "1", "2", "2", "5", "5", "3", "4"]

DIAG_PROFILE = {
    "Anemia ferropriva": {
        "conduta": "iniciar reposição de ferro e investigar perda crônica de sangue",
        "tratamento": "ferro oral com reavaliação hematimétrica em 4 a 8 semanas",
        "complicacao": "descompensação hemodinâmica em perda sanguínea persistente",
        "classificacao": "anemia microcítica e hipocrômica hipoproliferativa",
        "lab_table": [
            ("Hemoglobina", "8,4 g/dL", "12-16 g/dL"),
            ("VCM", "71 fL", "80-100 fL"),
            ("Ferritina", "8 ng/mL", "30-300 ng/mL"),
            ("Saturação de transferrina", "9%", "20-50%"),
        ],
    },
    "Anemia megaloblástica por deficiência de vitamina B12": {
        "conduta": "repor vitamina B12 e investigar etiologia da deficiência",
        "tratamento": "cianocobalamina parenteral com acompanhamento neurológico",
        "complicacao": "progressão de déficit neurológico por atraso terapêutico",
        "classificacao": "anemia macrocítica megaloblástica",
        "lab_table": [
            ("Hemoglobina", "7,9 g/dL", "12-16 g/dL"),
            ("VCM", "114 fL", "80-100 fL"),
            ("Vitamina B12", "112 pg/mL", "200-900 pg/mL"),
            ("Neutrófilos", "hipersegmentados", "ausentes"),
        ],
    },
    "Anemia da doença crônica": {
        "conduta": "otimizar controle da doença de base e tratar fatores associados",
        "tratamento": "manejo da inflamação subjacente e estratégia individualizada para ferro/EPO",
        "complicacao": "piora funcional com fadiga persistente e baixa reserva fisiológica",
        "classificacao": "anemia da inflamação normocítica ou discretamente microcítica",
        "lab_table": [
            ("Hemoglobina", "9,6 g/dL", "12-16 g/dL"),
            ("VCM", "83 fL", "80-100 fL"),
            ("Ferro sérico", "38 µg/dL", "60-170 µg/dL"),
            ("Ferritina", "260 ng/mL", "30-300 ng/mL"),
        ],
    },
    "Anemia hemolítica": {
        "conduta": "confirmar hemólise, estratificar gravidade e tratar causa específica",
        "tratamento": "suporte clínico e terapia etiológica conforme mecanismo hemolítico",
        "complicacao": "hiperbilirrubinemia com sobrecarga metabólica e piora clínica",
        "classificacao": "anemia regenerativa por destruição periférica de hemácias",
        "lab_table": [
            ("Hemoglobina", "8,1 g/dL", "12-16 g/dL"),
            ("Reticulócitos", "6,8%", "0,5-2,0%"),
            ("LDH", "620 U/L", "135-225 U/L"),
            ("Haptoglobina", "12 mg/dL", "30-200 mg/dL"),
        ],
    },
    "Anemia aplásica": {
        "conduta": "encaminhar com prioridade para hematologia e suporte transfusional/infeccioso",
        "tratamento": "suporte intensivo e avaliação para terapia imunossupressora ou transplante",
        "complicacao": "sepse grave e sangramento por pancitopenia",
        "classificacao": "anemia hipoproliferativa por falência medular",
        "lab_table": [
            ("Hemoglobina", "7,2 g/dL", "12-16 g/dL"),
            ("Leucócitos", "1.900/mm³", "4.000-11.000/mm³"),
            ("Plaquetas", "32.000/mm³", "150.000-450.000/mm³"),
            ("Reticulócitos", "0,2%", "0,5-2,0%"),
        ],
    },
}


@dataclass
class Question:
    tema: str
    dificuldade: str
    tipo: str
    pergunta: str
    alternativas: list[str]
    resposta_correta: str
    explicacao: str
    fonte: str


def load_blocks() -> list[dict]:
    data_path = Path(__file__).resolve().parent.parent / "data" / "knowledge_blocks.json"
    with open(data_path, "r", encoding="utf-8") as file:
        return json.load(file)


def _format_alternatives(options: list[str]) -> list[str]:
    letters = ["A", "B", "C", "D"]
    return [f"({letter}) {text}" for letter, text in zip(letters, options)]


def _patient_vignette(block: dict) -> str:
    age = random.randint(22, 78)
    sex = random.choice(["feminino", "masculino"])
    symptom = random.choice(block["pistas"])
    duration = random.choice(["duas semanas", "um mês", "três meses", "seis meses"])
    risk = random.choice(
        [
            "uso crônico de anti-inflamatório",
            "sangramento menstrual aumentado",
            "doença inflamatória crônica",
            "internação recente por infecção",
            "perda ponderal não intencional",
        ]
    )
    physical = random.choice(
        [
            "palidez cutaneomucosa ++/4",
            "taquicardia discreta ao esforço",
            "sopro sistólico funcional em foco mitral",
            "icterícia leve de escleras",
        ]
    )
    return (
        f"Paciente de {age} anos, sexo {sex}, procura atendimento com queixa de {symptom} há {duration}. "
        f"Relata piora progressiva da tolerância ao esforço e refere {risk}. "
        f"Ao exame físico, apresenta {physical}, sem sinais de choque e sem instabilidade respiratória."
    )


def _pick_theme_candidates(blocks: list[dict], current_diag: str, n: int = 3) -> list[dict]:
    candidates = [item for item in blocks if item["diagnostico"] != current_diag]
    random.shuffle(candidates)
    return candidates[:n]


def _style_tail(prompt: str, style_context: str) -> str:
    if style_context:
        return (
            f"{prompt} "
            "Considerando os dados clínicos e laboratoriais, assinale a alternativa mais adequada."
        )
    return f"{prompt} Assinale a alternativa correta."


def _build_format_1(block: dict, blocks: list[dict], style_context: str) -> tuple[str, list[str], str]:
    diag = block["diagnostico"]
    profile = DIAG_PROFILE[diag]
    labs = random.sample(block["laboratorio"], k=min(3, len(block["laboratorio"])))

    stem = (
        f"QUESTÃO X\n\n"
        f"{_patient_vignette(block)} "
        f"Exames iniciais evidenciam {labs[0]}, {labs[1] if len(labs) > 1 else labs[0]} "
        f"e {labs[2] if len(labs) > 2 else labs[0]}. "
        f"O diagnóstico, a conduta adequada e uma complicação possível são, respectivamente,"
    )

    correct = f"{diag}; {profile['conduta']}; {profile['complicacao']}"
    options = [correct]

    for item in _pick_theme_candidates(blocks, diag, n=3):
        item_diag = item["diagnostico"]
        item_profile = DIAG_PROFILE[item_diag]
        options.append(f"{item_diag}; {item_profile['conduta']}; {item_profile['complicacao']}")

    random.shuffle(options)
    return _style_tail(stem, style_context), options, correct


def _build_format_2(block: dict, blocks: list[dict], style_context: str) -> tuple[str, list[str], str]:
    diag = block["diagnostico"]
    profile = DIAG_PROFILE[diag]
    labs = random.sample(block["laboratorio"], k=min(2, len(block["laboratorio"])))

    stem = (
        f"QUESTÃO X\n\n"
        f"{_patient_vignette(block)} "
        f"No complemento diagnóstico, observam-se {labs[0]} e {labs[1] if len(labs) > 1 else labs[0]}. "
        f"A hipótese diagnóstica e o tratamento de primeira linha são, respectivamente,"
    )

    correct = f"{diag}; {profile['tratamento']}"
    options = [correct]

    for item in _pick_theme_candidates(blocks, diag, n=3):
        item_diag = item["diagnostico"]
        item_profile = DIAG_PROFILE[item_diag]
        options.append(f"{item_diag}; {item_profile['tratamento']}")

    random.shuffle(options)
    return _style_tail(stem, style_context), options, correct


def _build_format_3(block: dict, blocks: list[dict], style_context: str) -> tuple[str, list[str], str]:
    diag = block["diagnostico"]
    profile = DIAG_PROFILE[diag]
    lab = random.choice(block["laboratorio"])

    stem = (
        f"QUESTÃO X\n\n"
        f"{_patient_vignette(block)} "
        f"Exame complementar principal: {lab}. "
        f"Com base nos achados, esse quadro é classificado como"
    )

    correct = profile["classificacao"]
    options = [correct]

    other_classes = [
        DIAG_PROFILE[item["diagnostico"]]["classificacao"]
        for item in _pick_theme_candidates(blocks, diag, n=3)
    ]
    options.extend(other_classes)
    random.shuffle(options)

    return _style_tail(stem, style_context), options, correct


def _build_format_4(block: dict, blocks: list[dict], style_context: str) -> tuple[str, list[str], str]:
    stem = (
        f"QUESTÃO X\n\n"
        f"{_patient_vignette(block)} "
        "Após avaliação inicial na atenção primária, o caso é encaminhado para hematologia pela persistência dos sintomas e alterações laboratoriais. "
        "Ao ser assistido pelo especialista, estará em qual nível de atenção e receberá que tipo de prevenção, respectivamente?"
    )

    options = [
        "atenção primária; prevenção primária",
        "atenção secundária; prevenção terciária",
        "atenção terciária; prevenção primária",
        "atenção primária; prevenção quaternária",
    ]
    correct = "atenção secundária; prevenção terciária"

    return _style_tail(stem, style_context), options, correct


def _build_format_5(block: dict, blocks: list[dict], style_context: str) -> tuple[str, list[str], str]:
    diag = block["diagnostico"]
    profile = DIAG_PROFILE[diag]
    lab_table = profile["lab_table"]

    table_lines = "\n".join(
        [f"{exam} | {result} | {reference}" for exam, result, reference in lab_table]
    )

    stem = (
        f"QUESTÃO X\n\n"
        f"{_patient_vignette(block)}\n\n"
        f"Resultados laboratoriais:\n"
        f"Exame | Resultado | Valor de referência\n"
        f"{table_lines}\n\n"
        f"O diagnóstico e a conduta inicial indicada são, respectivamente,"
    )

    correct = f"{diag}; {profile['conduta']}"
    options = [correct]

    for item in _pick_theme_candidates(blocks, diag, n=3):
        item_diag = item["diagnostico"]
        item_profile = DIAG_PROFILE[item_diag]
        options.append(f"{item_diag}; {item_profile['conduta']}")

    random.shuffle(options)
    return _style_tail(stem, style_context), options, correct


BUILDERS = {
    "1": _build_format_1,
    "2": _build_format_2,
    "3": _build_format_3,
    "4": _build_format_4,
    "5": _build_format_5,
}


def generate_template_question(
    tema: str,
    style_context: str = "",
    explanation_context: str = "",
) -> Question:
    blocks = load_blocks()
    filtered = blocks if tema == "Todos" else [item for item in blocks if item["tema"] == tema]
    selected = random.choice(filtered)

    format_code = random.choice(FORMAT_WEIGHTS)
    prompt, options, correct = BUILDERS[format_code](selected, filtered, style_context)

    formatted_options = _format_alternatives(options)
    correct_tagged = formatted_options[options.index(correct)]

    explanation = selected["explicacao"]
    if explanation_context:
        explanation = (
            f"{explanation} "
            "Fundamento fisiopatológico: correlacionar produção, destruição e reserva funcional eritrocitária no contexto clínico apresentado."
        )

    return Question(
        tema=selected["tema"],
        dificuldade=FORMAT_DIFFICULTY[format_code],
        tipo=FORMAT_LABELS[format_code],
        pergunta=prompt,
        alternativas=formatted_options,
        resposta_correta=correct_tagged,
        explicacao=explanation,
        fonte=selected["fonte"],
    )


def generate_question(
    tema: str,
    style_context: str = "",
    explanation_context: str = "",
) -> Question:
    mode = os.getenv("HEMATOQUEST_MODE", "template").lower().strip()
    if mode != "llm":
        return generate_template_question(
            tema,
            style_context=style_context,
            explanation_context=explanation_context,
        )

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return generate_template_question(
            tema,
            style_context=style_context,
            explanation_context=explanation_context,
        )

    try:
        from openai import OpenAI

        blocks = load_blocks()
        filtered = blocks if tema == "Todos" else [item for item in blocks if item["tema"] == tema]
        block = random.choice(filtered)
        format_code = random.choice(FORMAT_WEIGHTS)
        format_label = FORMAT_LABELS[format_code]

        schema_hint = {
            "tema": "string",
            "dificuldade": "fácil|média|difícil",
            "tipo": "string",
            "pergunta": "string longo em estilo ENAMED",
            "alternativas": ["(A) string", "(B) string", "(C) string", "(D) string"],
            "resposta_correta": "string",
            "explicacao": "string",
            "fonte": "string",
        }

        instruction = f"""
        Gere uma questão de anemias em português brasileiro com JSON válido no formato: {schema_hint}
        Regras obrigatórias:
        - estilo ENAMED: enunciado clínico longo, linguagem objetiva, alto realismo
        - usar formato: {format_label}
        - alternativas longas e paralelas, com distratores plausíveis
        - evitar alternativas obviamente erradas
        - exatamente 4 alternativas: (A), (B), (C), (D)
        - apenas 1 correta
        - sem markdown, sem texto fora do JSON
        - usar como base clínica: {json.dumps(block, ensure_ascii=False)}
        - usar contexto de estilo dos PDFs (sem copiar literal): {style_context[:2000] if style_context else 'sem contexto adicional'}
        - usar contexto teórico para a explicação (sem copiar literal): {explanation_context[:2000] if explanation_context else 'sem contexto adicional'}
        """

        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=instruction,
            temperature=0.8,
        )

        payload = json.loads(response.output_text)
        return Question(
            tema=payload["tema"],
            dificuldade=payload["dificuldade"],
            tipo=payload["tipo"],
            pergunta=payload["pergunta"],
            alternativas=payload["alternativas"],
            resposta_correta=payload["resposta_correta"],
            explicacao=payload["explicacao"],
            fonte=payload.get("fonte", block.get("fonte", "")),
        )
    except Exception:
        return generate_template_question(
            tema,
            style_context=style_context,
            explanation_context=explanation_context,
        )
