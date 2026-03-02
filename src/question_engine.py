import json
import os
import random
import re
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
QUESTIONS_PER_THEME = 25

SUPPORTED_THEMES = ["Ferropriva", "Megaloblástica", "Doença crônica", "Aplásica", "Hemolítica"]

QUESTION_OBJECTIVES = [
    "Fisiopatologia",
    "Manejo",
    "Tratamento farmacológico",
    "Tratamento não farmacológico",
    "Etiologia",
    "Epidemiologia",
    "Padrão laboratorial",
]

FORMAT_OBJECTIVE_MAP = {
    "1": ["Manejo", "Tratamento não farmacológico", "Etiologia"],
    "2": ["Padrão laboratorial", "Etiologia", "Fisiopatologia"],
    "3": ["Tratamento farmacológico", "Manejo", "Fisiopatologia"],
    "4": ["Padrão laboratorial", "Fisiopatologia", "Etiologia"],
    "5": ["Manejo", "Epidemiologia", "Tratamento não farmacológico"],
}

_FORCED_CASE_VARIANT_BY_DIAG: dict[str, int | None] = {}

HEMOLYTIC_SUBTYPE_BLOCKS = [
    {
        "tema": "Hemolítica",
        "diagnostico": "Anemia hemolítica autoimune",
        "explicacao": "Hemólise imune mediada por autoanticorpos, usualmente com Coombs direto positivo.",
        "fonte": "Harrison + Hematologia clínica",
    },
    {
        "tema": "Hemolítica",
        "diagnostico": "Doença da aglutinina fria",
        "explicacao": "Hemólise por IgM com ativação de complemento, piora ao frio e acrocianose.",
        "fonte": "Harrison + Hematologia clínica",
    },
    {
        "tema": "Hemolítica",
        "diagnostico": "Deficiência de G6PD",
        "explicacao": "Hemólise oxidativa desencadeada por infecção/fármacos/alimentos, com corpos de Heinz e bite cells.",
        "fonte": "Harrison + Hematologia clínica",
    },
    {
        "tema": "Hemolítica",
        "diagnostico": "Esferocitose hereditária",
        "explicacao": "Defeito de proteínas de membrana eritrocitária com hemólise extravascular crônica.",
        "fonte": "Harrison + Hematologia clínica",
    },
    {
        "tema": "Hemolítica",
        "diagnostico": "Anemia hemolítica microangiopática (PTT)",
        "explicacao": "Hemólise mecânica intravascular por microtrombos, com esquizócitos e plaquetopenia.",
        "fonte": "Harrison + Hematologia clínica",
    },
]

HEMOLYTIC_ADVANCED_DIAG_WEIGHTS = {
    "Anemia hemolítica microangiopática (PTT)": 5,
    "Anemia hemolítica autoimune": 4,
    "Doença da aglutinina fria": 2,
    "Deficiência de G6PD": 2,
    "Esferocitose hereditária": 2,
}

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
    objetivo: str
    pergunta: str
    alternativas: list[str]
    resposta_correta: str
    explicacao: str
    fonte: str


def load_blocks() -> list[dict]:
    data_path = Path(__file__).resolve().parent.parent / "data" / "knowledge_blocks.json"
    with open(data_path, "r", encoding="utf-8") as file:
        return json.load(file)


FISIOPATOLOGIA = {
    "Anemia ferropriva": """
A anemia ferropriva resulta de balanço negativo de ferro, seja por perda aumentada (sangramento crônico gastrointestinal ou ginecológico), má absorção ou demanda elevada. O ferro é essencial para a síntese do grupo heme da hemoglobina. Quando os estoques de ferro se esgotam, a eritropoiese torna-se deficiente, produzindo hemácias microcíticas e hipocrômicas.

Fisiopatologia: A depleção segue estágios — primeiro reduz-se a ferritina (estoque), depois o ferro sérico e a saturação de transferrina caem, e finalmente surge a anemia com VCM baixo. A hepcidina, regulador central do metabolismo do ferro, está suprimida na ferropenia, facilitando absorção intestinal.

Diagnóstico laboratorial: hemoglobina reduzida, VCM < 80 fL, ferritina < 30 ng/mL, saturação de transferrina < 20%, RDW aumentado. O esfregaço pode mostrar microcitose, hipocromia e anisocitose.

Conduta: investigar a causa (endoscopia, colonoscopia em adultos) e repor ferro oral (sulfato ferroso 200mg, 2-3x/dia, longe das refeições). A resposta ao tratamento é evidenciada por reticulocitose em 7-10 dias e normalização da hemoglobina em 6-8 semanas.
""",
    "Anemia megaloblástica por deficiência de vitamina B12": """
A anemia megaloblástica por deficiência de B12 ocorre quando há carência dessa vitamina, essencial para a síntese de DNA. As principais causas incluem anemia perniciosa (autoimune), gastrectomia, doença ileal (Crohn) e dieta vegana estrita.

Fisiopatologia: A B12 é cofator da metionina sintase e da metilmalonil-CoA mutase. Sua deficiência causa acúmulo de homocisteína e ácido metilmalônico, prejudicando a síntese de DNA e causando eritropoiese ineficaz com células megaloblásticas. A medula produz precursores grandes que são destruídos prematuramente (hemólise intramedular).

Manifestações neurológicas: A desmielinização dos cordões posteriores e laterais da medula espinhal causa parestesias simétricas distais, ataxia sensitiva, fraqueza e alterações cognitivas — quadro chamado degeneração combinada subaguda.

Diagnóstico: VCM > 100 fL, B12 sérica < 200 pg/mL, neutrófilos hipersegmentados, LDH e bilirrubina indireta elevadas (hemólise intramedular). Anticorpos anti-fator intrínseco e anti-células parietais confirmam anemia perniciosa.

Tratamento: cianocobalamina 1000 mcg IM diariamente por 7 dias, depois semanal por 4 semanas, depois mensal vitalícia. A resposta hematológica é rápida, mas déficits neurológicos podem ser irreversíveis se houver atraso terapêutico.
""",
    "Anemia da doença crônica": """
A anemia da doença crônica (ou anemia da inflamação) ocorre em contextos de inflamação sistêmica persistente — infecções crônicas, doenças autoimunes, neoplasias e insuficiência cardíaca ou renal.

Fisiopatologia: A inflamação estimula a produção hepática de hepcidina, hormônio que bloqueia a ferroportina nos enterócitos e macrófagos, sequestrando ferro nos estoques e impedindo sua liberação para a eritropoiese. Há também supressão direta da eritropoetina e redução da sobrevida eritrocitária por citocinas inflamatórias (IL-6, TNF-α, IFN-γ).

Resultado: ferro sérico baixo com ferritina normal ou elevada — diferente da ferropenia verdadeira onde a ferritina está baixa. O VCM é geralmente normal, podendo ser discretamente reduzido em casos prolongados.

Diagnóstico diferencial: na ferropenia, ferritina < 30 ng/mL; na anemia da inflamação, ferritina > 100 ng/mL com ferro sérico baixo. A dosagem de receptor solúvel de transferrina (sTfR) ajuda: elevado na ferropenia, normal na inflamação.

Tratamento: tratar a doença de base. Transfusões e eritropoetina recombinante são reservadas para casos sintomáticos ou refratários. A reposição de ferro pode ser ineficaz enquanto a hepcidina estiver elevada.
""",
    "Anemia hemolítica": """
As anemias hemolíticas caracterizam-se pela destruição acelerada de hemácias, com sobrevida eritrocitária reduzida de 120 dias para menos de 20 dias em casos graves.

Fisiopatologia: A hemólise pode ser intravascular (destruição dentro dos vasos, liberando hemoglobina livre) ou extravascular (fagocitose por macrófagos no baço e fígado). Causas incluem defeitos intrínsecos da hemácia (esferocitose, deficiência de G6PD, hemoglobinopatias) ou fatores extrínsecos (autoanticorpos, microangiopatia, infecções).

Compensação medular: A medula óssea responde aumentando a produção eritrocitária em até 8 vezes — evidenciada por reticulocitose. Se a produção compensa a destruição, o paciente pode manter hemoglobina normal (hemólise compensada).

Diagnóstico: anemia com reticulócitos > 2%, LDH elevado, bilirrubina indireta aumentada, haptoglobina reduzida (consumida ao ligar hemoglobina livre). O teste de Coombs direto positivo indica hemólise autoimune.

Tratamento: depende da etiologia — corticoides para hemólise autoimune quente, evitar gatilhos na deficiência de G6PD, esplenectomia para esferocitose grave, suporte transfusional quando indicado.
""",
    "Anemia aplásica": """
A anemia aplásica é uma síndrome de falência medular caracterizada por pancitopenia e medula óssea hipocelular, sem infiltração ou fibrose.

Fisiopatologia: Na maioria dos casos, há destruição imunomediada das células-tronco hematopoéticas por linfócitos T citotóxicos autorreativos. Causas secundárias incluem medicamentos (cloranfenicol, carbamazepina), exposição a benzeno, infecções virais (hepatite, parvovírus B19, HIV) e síndromes hereditárias (anemia de Fanconi).

Apresentação clínica: A pancitopenia causa tríade de anemia (fadiga, dispneia), leucopenia (infecções recorrentes) e plaquetopenia (sangramentos). Não há hepatoesplenomegalia — sua presença sugere outro diagnóstico.

Diagnóstico: hemograma com pancitopenia, reticulócitos baixos (< 1%), biópsia de medula óssea mostrando hipocelularidade < 30% com substituição gordurosa. Exclui-se hemoglobinúria paroxística noturna (citometria de fluxo) e síndrome mielodisplásica.

Tratamento: transplante alogênico de células-tronco (curativo, preferido em jovens com doador compatível) ou imunossupressão com globulina antitimocítica + ciclosporina (resposta em 60-70%). Suporte transfusional, profilaxia antimicrobiana e evitar transfusões múltiplas antes do transplante são essenciais.
""",
}


def _build_question_specific_explanation(
    block: dict,
    format_code: str,
    correct_answer: str,
    wrong_options: list[str],
) -> str:
    """Constrói explicação que responde diretamente à questão."""
    diagnostico = block.get("diagnostico", "")
    scenario = CLINICAL_SCENARIOS.get(diagnostico, {})
    
    # Explicação específica por tipo de questão
    explanations_by_format = {
        "1": _explain_diagnosis_conduct,
        "2": _explain_confirmatory_exam,
        "3": _explain_treatment,
        "4": _explain_differentiation,
        "5": _explain_diagnosis_complication,
    }
    
    builder = explanations_by_format.get(format_code, _explain_diagnosis_conduct)
    explanation = builder(diagnostico, scenario, correct_answer, wrong_options)
    
    # Garantir primeira letra maiúscula
    if explanation:
        explanation = explanation[0].upper() + explanation[1:]
    
    return explanation


def _explain_diagnosis_conduct(diag: str, scenario: dict, correct: str, wrong: list[str]) -> str:
    """Explica por que o diagnóstico e conduta estão corretos com fisiopatologia."""
    confounders = DISTRACTORS_BY_SCENARIO.get(diag, {}).get("confounders", [])
    
    parts = [f"**Resposta correta:** {correct}\n\n"]
    
    # Fisiopatologia específica por diagnóstico
    if diag == "Anemia ferropriva":
        parts.append(
            "**Fundamento fisiopatológico:**\n"
            "A anemia ferropriva resulta de balanço negativo de ferro — seja por perda aumentada "
            "(sangramento crônico), má absorção ou demanda elevada. O ferro é essencial para a síntese "
            "do grupo heme da hemoglobina. A depleção segue estágios: primeiro reduz-se a ferritina "
            "(estoque), depois o ferro sérico e a saturação de transferrina caem, e finalmente surge "
            "a anemia microcítica.\n\n"
            "**Como os achados confirmam o diagnóstico:**\n"
            "O VCM baixo (< 80 fL) indica microcitose. A ferritina reduzida (< 30 ng/mL) confirma "
            "depleção de estoques. A saturação de transferrina baixa (< 20%) mostra ferro insuficiente "
            "para eritropoiese. O RDW elevado reflete anisocitose por produção deficiente.\n\n"
            "**Por que a conduta indicada:**\n"
            "Em adultos, especialmente > 40 anos, a causa mais comum de ferropenia é perda GI oculta "
            "(úlceras, neoplasias). A endoscopia digestiva alta e colonoscopia são mandatórias para "
            "excluir malignidade. O tratamento com sulfato ferroso repõe os estoques."
        )
    elif diag == "Anemia megaloblástica por deficiência de vitamina B12":
        parts.append(
            "**Fundamento fisiopatológico:**\n"
            "A vitamina B12 é cofator da metionina sintase e da metilmalonil-CoA mutase. Sua deficiência "
            "causa acúmulo de homocisteína e ácido metilmalônico, prejudicando a síntese de DNA. A medula "
            "produz precursores megaloblásticos que são destruídos prematuramente (eritropoiese ineficaz), "
            "causando anemia com LDH e bilirrubina indireta elevadas.\n\n"
            "**Como os achados confirmam o diagnóstico:**\n"
            "O VCM muito elevado (> 110 fL) indica macrocitose acentuada. Neutrófilos hipersegmentados "
            "(> 5 lobos) são patognomônicos. A B12 sérica baixa (< 200 pg/mL) confirma a deficiência. "
            "Os sintomas neurológicos (parestesias, ataxia) resultam da desmielinização por acúmulo de "
            "metilmalonato.\n\n"
            "**Por que a conduta indicada:**\n"
            "A cianocobalamina IM garante absorção independente do fator intrínseco. A dose inicial alta "
            "repõe estoques rapidamente. A avaliação neurológica é essencial porque déficits podem ser "
            "irreversíveis se o tratamento atrasar."
        )
    elif diag == "Anemia da doença crônica":
        parts.append(
            "**Fundamento fisiopatológico:**\n"
            "A inflamação crônica estimula a produção hepática de hepcidina, hormônio que bloqueia a "
            "ferroportina nos enterócitos e macrófagos. Isso sequestra ferro nos estoques (ferritina alta) "
            "e impede sua liberação para a eritropoiese (ferro sérico baixo). Há também supressão direta "
            "da eritropoetina e redução da sobrevida eritrocitária por citocinas (IL-6, TNF-α).\n\n"
            "**Como os achados confirmam o diagnóstico:**\n"
            "A ferritina elevada (> 100 ng/mL) com ferro sérico baixo é o achado-chave — diferente da "
            "ferropriva onde ambos estão baixos. O TIBC baixo (< 250 µg/dL) confirma o sequestro de ferro. "
            "PCR/VHS elevados mostram inflamação ativa. O VCM normal ou discretamente baixo é típico.\n\n"
            "**Por que a conduta indicada:**\n"
            "O tratamento principal é controlar a doença de base (no caso, AR). Ferroterapia isolada "
            "é ineficaz porque o problema não é falta de ferro, mas sequestro. A anemia melhora quando "
            "a inflamação é controlada."
        )
    elif diag == "Anemia hemolítica autoimune":
        parts.append(
            "**Fundamento fisiopatológico:**\n"
            "Na AHAI, autoanticorpos (geralmente IgG) ligam-se à membrana eritrocitária, marcando as "
            "hemácias para destruição por macrófagos esplênicos (hemólise extravascular). Pode haver "
            "também fixação de complemento (C3) com hemólise intravascular parcial. A medula compensa "
            "aumentando a produção em até 8 vezes, evidenciada por reticulocitose.\n\n"
            "**Como os achados confirmam o diagnóstico:**\n"
            "A tríade diagnóstica é: anemia + reticulocitose + Coombs direto positivo. O LDH elevado "
            "reflete destruição celular. A haptoglobina baixa (consumida ao ligar hemoglobina livre) é "
            "marcador sensível de hemólise. A bilirrubina indireta elevada resulta do catabolismo do heme. "
            "Esferócitos no esfregaço indicam perda de membrana pelos macrófagos.\n\n"
            "**Por que a conduta indicada:**\n"
            "Os corticoides suprimem a produção de autoanticorpos e reduzem a fagocitose esplênica. "
            "A investigação de doenças linfoproliferativas e autoimunes é necessária porque AHAI pode "
            "ser secundária (lúpus, LLC, linfomas)."
        )
    elif diag == "Anemia aplásica":
        parts.append(
            "**Fundamento fisiopatológico:**\n"
            "Na anemia aplásica, há destruição imunomediada das células-tronco hematopoéticas por "
            "linfócitos T citotóxicos autorreativos. Isso resulta em falência medular com pancitopenia "
            "e medula hipocelular (< 30% de celularidade, substituída por gordura). Diferente de leucemias "
            "e SMD, não há células anormais infiltrando a medula.\n\n"
            "**Como os achados confirmam o diagnóstico:**\n"
            "A pancitopenia (anemia + neutropenia + plaquetopenia) com reticulócitos baixos indica "
            "falência de produção, não destruição periférica. A ausência de hepatoesplenomegalia exclui "
            "doenças infiltrativas. A medula hipocelular na biópsia confirma aplasia. A LDH normal/baixa "
            "diferencia de hemólise.\n\n"
            "**Por que a conduta indicada:**\n"
            "O isolamento protetor previne infecções oportunistas em neutropênicos graves. O suporte "
            "transfusional maneja a anemia e plaquetopenia. Antibioticoterapia de amplo espectro é "
            "necessária pelo risco de sepse. O encaminhamento urgente para hematologia permite avaliar "
            "transplante ou imunossupressão."
        )
    else:
        parts.append(f"O quadro clínico e laboratorial configura {diag}.")
    
    # Explicar por que as alternativas erradas estão incorretas
    parts.append("\n\n**Por que as outras alternativas estão incorretas:**\n")
    for conf in confounders[:3]:
        parts.append(f"- **{conf['diag']}:** {conf['justificativa']}.\n")
    
    return "".join(parts)


def _explain_confirmatory_exam(diag: str, scenario: dict, correct: str, wrong: list[str]) -> str:
    """Explica o exame confirmatório correto com fisiopatologia."""
    parts = [f"**Resposta correta:** {correct}\n\n"]
    
    if diag == "Anemia ferropriva":
        parts.append(
            "**Fundamento fisiopatológico:**\n"
            "O metabolismo do ferro segue uma sequência de depleção: primeiro esgotam-se os estoques "
            "(ferritina cai), depois o ferro circulante diminui (ferro sérico baixo, saturação de "
            "transferrina baixa), e por último surgem alterações eritrocitárias (VCM baixo, hipocromia).\n\n"
            "**Por que este exame confirma o diagnóstico:**\n"
            "A ferritina sérica reflete diretamente os estoques de ferro corporal (1 ng/mL ≈ 8-10 mg de "
            "ferro armazenado). Valores < 30 ng/mL têm especificidade > 95% para ferropenia. Na ADC, a "
            "ferritina está normal/elevada pela resposta de fase aguda, tornando-a o melhor discriminador.\n\n"
            "**Por que os outros exames são insuficientes:**\n"
            "O VCM só se altera após depleção prolongada — a ferropenia pode existir com VCM ainda normal "
            "(estágio 1). O hemograma completo mostra a anemia, mas não diferencia etiologias. "
            "Reticulócitos estão normais/baixos em qualquer anemia hipoproliferativa."
        )
    elif diag == "Anemia megaloblástica por deficiência de vitamina B12":
        parts.append(
            "**Fundamento fisiopatológico:**\n"
            "A vitamina B12 é cofator de duas enzimas: metionina sintase (converte homocisteína em metionina) "
            "e metilmalonil-CoA mutase (converte metilmalonil-CoA em succinil-CoA). A deficiência de B12 "
            "causa acúmulo de AMBOS os substratos, enquanto a deficiência de folato eleva apenas homocisteína.\n\n"
            "**Por que o ácido metilmalônico confirma B12:**\n"
            "A dosagem de ácido metilmalônico (AMM) é específica para deficiência de B12. Valores > 370 nmol/L "
            "com B12 borderline (200-300 pg/mL) confirmam deficiência funcional. Na falta de folato, o AMM "
            "permanece normal porque a metilmalonil-CoA mutase não depende de folato.\n\n"
            "**Por que a B12 sérica isolada pode falhar:**\n"
            "A B12 sérica pode estar falsamente normal em hepatopatias (liberação de estoques) ou falsamente "
            "baixa na gravidez e uso de anticoncepcionais. O AMM e a holotranscobalamina são mais fidedignos "
            "do status funcional de B12."
        )
    elif diag == "Anemia da doença crônica":
        parts.append(
            "**Fundamento fisiopatológico:**\n"
            "Na ADC, a hepcidina elevada bloqueia a ferroportina, impedindo a saída de ferro dos enterócitos "
            "e macrófagos. O ferro fica \"preso\" nos estoques (ferritina alta), mas não chega à medula "
            "(ferro sérico baixo). A TIBC está baixa porque o fígado reduz a produção de transferrina.\n\n"
            "**Por que o sTfR diferencia ADC de ferropriva:**\n"
            "O receptor solúvel de transferrina (sTfR) é liberado pelos eritroblastos proporcionalmente à "
            "demanda de ferro. Na ferropenia verdadeira, a medula \"faminta\" aumenta a expressão de "
            "receptores → sTfR elevado. Na ADC, há ferro suficiente (preso nos estoques), então a medula "
            "não aumenta receptores → sTfR normal.\n\n"
            "**O índice sTfR/log ferritina:**\n"
            "Valores < 1 favorecem ADC pura. Valores > 2 indicam ferropenia coexistente (ADC + ferropriva). "
            "Valores 1-2 são indeterminados e requerem avaliação clínica."
        )
    elif diag == "Anemia hemolítica autoimune":
        parts.append(
            "**Fundamento fisiopatológico:**\n"
            "Na AHAI, autoanticorpos (IgG ou IgM) ligam-se aos antígenos eritrocitários. Os anticorpos \"quentes\" "
            "(IgG, 37°C) causam hemólise extravascular pelo sistema reticuloendotelial (baço, fígado). Os anticorpos "
            "\"frios\" (IgM, 4°C) ativam complemento e causam hemólise intravascular parcial.\n\n"
            "**Por que o Coombs direto confirma o diagnóstico:**\n"
            "O teste de Coombs direto (ou antiglobulina direto - DAT) detecta anticorpos ou complemento "
            "já ligados às hemácias do paciente. Padrões: IgG positivo sugere AHAI quente; C3 positivo isolado "
            "sugere anticorpos frios ou algumas AHAI quentes; IgG + C3 é comum na AHAI quente.\n\n"
            "**Coombs direto negativo não exclui hemólise:**\n"
            "Outras causas de hemólise (esferocitose, G6PD, microangiopatias) têm Coombs negativo. "
            "A positividade do Coombs indica especificamente mecanismo IMUNE, direcionando para "
            "corticoterapia como primeira linha."
        )
    elif diag == "Anemia aplásica":
        parts.append(
            "**Fundamento fisiopatológico:**\n"
            "A anemia aplásica idiopática é mediada por linfócitos T citotóxicos (CD8+) que destroem células-tronco "
            "hematopoéticas via IFN-γ, TNF-α e perforinas. A medula torna-se hipocelular (< 30%), substituída "
            "por tecido adiposo, incapaz de produzir células sanguíneas.\n\n"
            "**Por que a biópsia de medula é essencial:**\n"
            "O aspirado medular pode subestimar a celularidade (diluição com sangue periférico). A biópsia "
            "permite avaliar: 1) celularidade global (< 25-30% na aplasia grave), 2) substituição adiposa, "
            "3) ausência de fibrose (diferencia de mielofibrose), 4) ausência de infiltração (exclui leucemia "
            "e metástases).\n\n"
            "**Diferenciação de outros diagnósticos:**\n"
            "Na SMD, a medula é normo/hipercelular com displasia. Na leucemia aguda, há blastos > 20%. "
            "Na HPN associada, a citometria de fluxo mostra deficiência de GPI. A biópsia é o padrão-ouro "
            "para caracterizar a síndrome de falência medular."
        )
    else:
        parts.append(f"Este exame é o mais específico para confirmar {diag}.")
    
    return "".join(parts)


def _explain_treatment(diag: str, scenario: dict, correct: str, wrong: list[str]) -> str:
    """Explica o tratamento correto com fisiopatologia."""
    parts = [f"**Resposta correta:** {correct}\n\n"]
    
    if diag == "Anemia ferropriva":
        parts.append(
            "**Fundamento fisiopatológico do tratamento:**\n"
            "O ferro oral é absorvido no duodeno pela proteína DMT-1, transportado pela ferroportina e "
            "carreado pela transferrina até a medula. O sulfato ferroso contém 20% de ferro elementar "
            "(200 mg comprimido = 40 mg Fe elementar). A absorção é melhor em jejum, mas pode ser feita "
            "com vitamina C para melhorar tolerância.\n\n"
            "**Por que monitorar com reticulócitos:**\n"
            "A resposta medular ao ferro surge em 7-10 dias com pico de reticulócitos (\"crise "
            "reticulocitária\"). A hemoglobina aumenta ~1 g/dL a cada 2-3 semanas. Se não houver resposta, "
            "investigar: má adesão, sangramento persistente, má absorção (H. pylori, doença celíaca) ou "
            "diagnóstico incorreto.\n\n"
            "**Por que tratar por 3-6 meses após normalizar Hb:**\n"
            "A correção da anemia ocorre antes da repleção dos estoques. Parar precocemente resulta em "
            "recidiva. A meta é ferritina > 100 ng/mL para garantir reserva adequada."
        )
    elif diag == "Anemia megaloblástica por deficiência de vitamina B12":
        parts.append(
            "**Fundamento fisiopatológico do tratamento:**\n"
            "A cianocobalamina IM bypassa a absorção intestinal (dependente de fator intrínseco gástrico). "
            "É convertida em metilcobalamina e adenosilcobalamina, as formas ativas. A dose alta inicial "
            "satura os receptores e repõe estoques hepáticos (2-5 mg são armazenados).\n\n"
            "**Por que monitorar reticulócitos e neurologia:**\n"
            "A \"crise reticulocitária\" em 3-5 dias confirma resposta medular. ATENÇÃO: pode ocorrer "
            "hipocalemia transitória pelo consumo de K+ na síntese de DNA — monitorar potássio em casos "
            "graves. Os sintomas neurológicos melhoram em semanas a meses; déficits > 6 meses podem ser "
            "irreversíveis.\n\n"
            "**Por que tratamento vitalício:**\n"
            "Na anemia perniciosa (ausência de fator intrínseco), não há como absorver B12 oral. "
            "Na gastrectomia e ressecções ileais, idem. A reposição mensal previne recidiva da anemia "
            "e progressão neurológica."
        )
    elif diag == "Anemia da doença crônica":
        parts.append(
            "**Fundamento fisiopatológico do tratamento:**\n"
            "A ADC é consequência da inflamação, não causa primária. A hepcidina elevada bloqueia o ferro, "
            "e as citocinas (IL-6, TNF-α) suprimem a eritropoetina e encurtam a sobrevida das hemácias. "
            "Tratar a doença de base reduz a hepcidina e normaliza a eritropoiese.\n\n"
            "**Por que NÃO dar ferro oral isolado:**\n"
            "O ferro oral é ineficaz porque a hepcidina bloqueia a absorção intestinal (ferroportina "
            "internalizada). A ferritina já está elevada, indicando estoques cheios. Dar ferro pode "
            "causar sobrecarga. Ferro IV pode ser considerado apenas se houver ferropenia coexistente "
            "comprovada (sTfR elevado ou ferritina < 100 ng/mL).\n\n"
            "**Papel da eritropoetina:**\n"
            "A EPO recombinante pode ser usada se Hb < 10 g/dL com sintomas, mas a resposta é limitada "
            "enquanto a inflamação persistir. A combinação EPO + ferro IV tem melhores resultados em "
            "alguns casos."
        )
    elif diag == "Anemia hemolítica autoimune":
        parts.append(
            "**Fundamento fisiopatológico do tratamento:**\n"
            "Na AHAI quente (IgG), os anticorpos opsonizam as hemácias, que são fagocitadas pelos "
            "macrófagos esplênicos. Os corticoides: 1) reduzem a produção de anticorpos pelos plasmócitos, "
            "2) diminuem a expressão de receptores Fc nos macrófagos (menos fagocitose), 3) podem "
            "estabilizar a membrana eritrocitária.\n\n"
            "**Por que prednisona 1-2 mg/kg/dia:**\n"
            "Doses altas são necessárias para efeito imunossupressor rápido. A resposta inicial "
            "(estabilização da Hb) ocorre em poucos dias, mas a negativação do Coombs leva semanas. "
            "O desmame deve ser gradual — recaídas são comuns se muito rápido.\n\n"
            "**Terapias de segunda linha:**\n"
            "Se refratário a corticoides: rituximabe (anti-CD20, depleta linfócitos B produtores de "
            "anticorpos) ou esplenectomia (remove sítio principal de destruição). Azatioprina, "
            "ciclosporina e micofenolato são opções de manutenção."
        )
    elif diag == "Anemia aplásica":
        parts.append(
            "**Fundamento fisiopatológico do tratamento:**\n"
            "A aplasia idiopática é mediada por linfócitos T autorreativos que destroem células-tronco. "
            "Há duas estratégias: 1) eliminar/substituir a medula doente (TCTH) ou 2) suprimir os "
            "linfócitos agressores (imunossupressão).\n\n"
            "**Transplante alogênico (TCTH):**\n"
            "Curativo em 80-90% dos casos. Indicado para < 40 anos com doador HLA-idêntico aparentado. "
            "IMPORTANTE: evitar múltiplas transfusões pré-transplante porque causam aloimunização "
            "e aumentam rejeição. Usar produtos leucodepletados e irradiados.\n\n"
            "**Imunossupressão (ATG + ciclosporina):**\n"
            "Para > 40 anos ou sem doador compatível. A globulina antitimocítica (ATG) depleta linfócitos T. "
            "A ciclosporina inibe a ativação de células T. Resposta em 60-70% em 3-6 meses. "
            "Risco de recidiva e evolução para SMD/leucemia de 15-20% em 10 anos."
        )
    else:
        parts.append(f"O tratamento indicado é específico para {diag}.")
    
    return "".join(parts)


def _explain_differentiation(diag: str, scenario: dict, correct: str, wrong: list[str]) -> str:
    """Explica como diferenciar os diagnósticos com fisiopatologia."""
    confounders = DISTRACTORS_BY_SCENARIO.get(diag, {}).get("confounders", [])
    parts = [f"**Resposta correta:** {correct}\n\n"]
    
    if diag == "Anemia ferropriva":
        parts.append(
            "**Fundamento fisiopatológico da diferenciação:**\n"
            "A anemia ferropriva e a anemia da doença crônica podem apresentar ferro sérico baixo, "
            "gerando confusão diagnóstica. A diferença está na disponibilidade versus sequestro de ferro.\n\n"
            "**Na ferropriva:**\n"
            "- Ferritina BAIXA (estoques depletados)\n"
            "- TIBC ELEVADO (fígado produz mais transferrina para \"capturar\" ferro escasso)\n"
            "- sTfR ELEVADO (medula aumenta receptores por carência de ferro)\n\n"
            "**Na ADC:**\n"
            "- Ferritina NORMAL/ALTA (estoques cheios, sequestrados pela hepcidina)\n"
            "- TIBC BAIXO (fase aguda suprime transferrina)\n"
            "- sTfR NORMAL (medula recebe ferro dos macrófagos locais)\n\n"
            "**Na talassemia minor:**\n"
            "- Ferritina NORMAL, ferro sérico NORMAL\n"
            "- RDW NORMAL (hemácias uniformemente microcíticas)\n"
            "- Eletroforese com HbA2 > 3,5% confirma β-talassemia\n"
        )
    elif diag == "Anemia megaloblástica por deficiência de vitamina B12":
        parts.append(
            "**Fundamento fisiopatológico da diferenciação:**\n"
            "Ambas as deficiências (B12 e folato) causam macrocitose e megaloblastose, mas diferem "
            "nas manifestações neurológicas e nos marcadores bioquímicos.\n\n"
            "**Na deficiência de B12:**\n"
            "- Homocisteína ELEVADA (metionina sintase bloqueada)\n"
            "- Ácido metilmalônico ELEVADO (metilmalonil-CoA mutase bloqueada)\n"
            "- Sintomas NEUROLÓGICOS presentes (desmielinização por acúmulo de metilmalonato)\n\n"
            "**Na deficiência de folato:**\n"
            "- Homocisteína ELEVADA (mesma via)\n"
            "- Ácido metilmalônico NORMAL (esta enzima não depende de folato)\n"
            "- Sintomas neurológicos AUSENTES ou mínimos\n\n"
            "**Na SMD:**\n"
            "- B12 e folato NORMAIS\n"
            "- Displasia em > 10% de uma linhagem no mielograma\n"
            "- Citogenética frequentemente alterada\n"
        )
    elif diag == "Anemia da doença crônica":
        parts.append(
            "**Fundamento fisiopatológico da diferenciação:**\n"
            "O desafio é distinguir ADC pura de ADC + ferropenia coexistente, comum em pacientes "
            "inflamados com perdas GI (AINE, neoplasia).\n\n"
            "**ADC pura:**\n"
            "- Ferritina > 100 ng/mL (estoques adequados)\n"
            "- sTfR normal ou levemente elevado\n"
            "- Índice sTfR/log ferritina < 1\n\n"
            "**ADC + ferropenia:**\n"
            "- Ferritina 30-100 ng/mL (zona cinza)\n"
            "- sTfR elevado (medula carente)\n"
            "- Índice sTfR/log ferritina > 2\n\n"
            "**Na DRC:**\n"
            "- Creatinina elevada (> 2-3 mg/dL)\n"
            "- EPO endógena inapropriadamente baixa para o grau de anemia\n"
            "- Geralmente normocítica, sem ferro sérico tão baixo\n"
        )
    elif diag == "Anemia hemolítica autoimune":
        parts.append(
            "**Fundamento fisiopatológico da diferenciação:**\n"
            "O Coombs direto positivo diferencia AHAI de outras causas de hemólise (reticulocitose + "
            "LDH alto + haptoglobina baixa podem estar presentes em todas).\n\n"
            "**AHAI vs Esferocitose hereditária:**\n"
            "- Ambas têm esferócitos no esfregaço\n"
            "- AHAI: Coombs POSITIVO, história de infecção recente ou doença autoimune\n"
            "- Esferocitose: Coombs NEGATIVO, história FAMILIAR positiva, teste de fragilidade osmótica +\n\n"
            "**AHAI vs PTT:**\n"
            "- AHAI: plaquetas NORMAIS, esferócitos no esfregaço\n"
            "- PTT: plaquetopenia GRAVE, ESQUIZÓCITOS (não esferócitos), febre, alteração neurológica, IRA\n"
            "- PTT é emergência hematológica — plasmaférese imediata\n\n"
            "**AHAI vs Megaloblástica:**\n"
            "- AHAI: reticulocitose (medula compensando), VCM pode estar alto pelos reticulócitos\n"
            "- Megaloblástica: reticulócitos BAIXOS (eritropoiese ineficaz), VCM muito alto (> 110 fL)\n"
        )
    elif diag == "Anemia aplásica":
        parts.append(
            "**Fundamento fisiopatológico da diferenciação:**\n"
            "A pancitopenia pode ocorrer em várias condições, mas o padrão medular difere.\n\n"
            "**Aplasia vs Leucemia aguda:**\n"
            "- Aplasia: medula HIPOCELULAR (< 30%), sem blastos, sem organomegalia\n"
            "- Leucemia aguda: medula HIPERCELULAR com blastos > 20%, pode ter hepatoesplenomegalia\n\n"
            "**Aplasia vs SMD hipoplásica:**\n"
            "- Aplasia: SEM displasia, citogenética normal na maioria\n"
            "- SMD: displasia em ≥ 10% de uma linhagem, anomalias citogenéticas frequentes\n"
            "- A diferenciação pode ser difícil — alguns casos são \"overlap\"\n\n"
            "**Aplasia vs HPN:**\n"
            "- Podem coexistir (\"síndrome aplasia-HPN\")\n"
            "- Citometria de fluxo mostra deficiência de CD55/CD59 na HPN\n"
            "- HPN isolada tem mais hemólise e tromboses\n"
        )
    else:
        parts.append("A diferenciação diagnóstica requer análise integrada dos achados.\n")
    
    parts.append("\n**Por que os outros exames não diferenciam bem:**\n")
    for w in wrong[:3]:
        if "(" in w:
            w_clean = w.split(") ", 1)[1] if ") " in w else w
        else:
            w_clean = w
        parts.append(f"- {w_clean}\n")
    
    return "".join(parts)


def _explain_diagnosis_complication(diag: str, scenario: dict, correct: str, wrong: list[str]) -> str:
    """Explica diagnóstico e complicação a monitorar com fisiopatologia."""
    confounders = DISTRACTORS_BY_SCENARIO.get(diag, {}).get("confounders", [])
    parts = [f"**Resposta correta:** {correct}\n\n"]
    
    if diag == "Anemia ferropriva":
        parts.append(
            "**Fundamento fisiopatológico das complicações:**\n"
            "A anemia crônica leva a mecanismos compensatórios: aumento do débito cardíaco, vasodilatação "
            "periférica e desvio da curva de dissociação da hemoglobina (efeito Bohr). Quando a Hb cai "
            "abaixo de 7-8 g/dL, esses mecanismos se esgotam.\n\n"
            "**Descompensação cardiovascular:**\n"
            "O coração trabalha em alto débito para compensar a hipóxia tissular. Em pacientes com "
            "doença coronariana prévia, isso precipita angina. Em idosos, pode causar insuficiência "
            "cardíaca de alto débito, edema pulmonar e arritmias.\n\n"
            "**Por que investigar sangramento oculto:**\n"
            "Em adultos > 40 anos, a principal causa de ferropenia é perda GI (úlceras, pólipos, "
            "neoplasias de cólon). A investigação com EDA e colonoscopia é mandatória mesmo sem "
            "sintomas GI, pois neoplasias podem sangrar lentamente de forma assintomática."
        )
    elif diag == "Anemia megaloblástica por deficiência de vitamina B12":
        parts.append(
            "**Fundamento fisiopatológico das complicações neurológicas:**\n"
            "O ácido metilmalônico acumulado é incorporado na síntese de ácidos graxos da mielina, "
            "produzindo ácidos graxos de cadeia ímpar anômalos. Isso causa desmielinização dos "
            "cordões posteriores (sensibilidade profunda) e laterais (via piramidal) da medula espinhal.\n\n"
            "**Degeneração combinada subaguda:**\n"
            "Manifesta-se como: parestesias simétricas em mãos/pés, perda de sensibilidade vibratória "
            "e propriocepção, ataxia sensitiva (Romberg +), fraqueza de membros inferiores. "
            "Pode haver alterações cognitivas e psiquiátricas (\"loucura megaloblástica\").\n\n"
            "**Reversibilidade:**\n"
            "Déficits presentes há menos de 3-6 meses geralmente melhoram com tratamento. "
            "Déficits prolongados podem ser permanentes. Por isso, o tratamento deve ser iniciado "
            "ANTES da confirmação laboratorial se houver alta suspeita clínica."
        )
    elif diag == "Anemia da doença crônica":
        parts.append(
            "**Fundamento fisiopatológico das complicações:**\n"
            "A persistência da anemia na ADC é um marcador de atividade inflamatória não controlada. "
            "A anemia em si contribui para fadiga e intolerância ao exercício, piorando a qualidade "
            "de vida e a capacidade funcional do paciente.\n\n"
            "**Progressão da doença de base:**\n"
            "Em doenças autoimunes (AR, lúpus), a anemia acompanha a atividade inflamatória. "
            "Se a Hb não melhora com tratamento, pode indicar: doença refratária, ferropenia "
            "coexistente não diagnosticada, ou outra causa de anemia (renal, medicamentosa).\n\n"
            "**Refratariedade à eritropoetina:**\n"
            "20-30% dos pacientes não respondem à EPO. Causas: inflamação persistente (IL-6 alta suprime "
            "eritropoiese), ferropenia funcional (ferritina normal mas sTfR alto), anticorpos "
            "anti-EPO, ou dose/via inadequada."
        )
    elif diag == "Anemia hemolítica autoimune":
        parts.append(
            "**Fundamento fisiopatológico das complicações:**\n"
            "Na hemólise intravascular, a hemoglobina livre satura a haptoglobina e escapa para a urina "
            "(hemoglobinúria). A hemoglobina é nefrotóxica, causando lesão tubular aguda. O ferro liberado "
            "catalisa formação de radicais livres que lesam o endotélio.\n\n"
            "**Crise hemolítica aguda:**\n"
            "Caracterizada por queda abrupta da Hb (> 2 g/dL em horas), icterícia intensa, "
            "hemoglobinúria (urina escura como coca-cola), dor lombar. Pode evoluir para IRA, "
            "CID e instabilidade hemodinâmica. EMERGÊNCIA — considerar transfusão e UTI.\n\n"
            "**Monitorização inicial:**\n"
            "Nas primeiras 48-72h de corticoterapia, monitorar: hemoglobina (resposta adequada: "
            "estabilização em 24-48h), reticulócitos, função renal, cor da urina, potássio "
            "(hipercalemia pode ocorrer por destruição celular maciça)."
        )
    elif diag == "Anemia aplásica":
        parts.append(
            "**Fundamento fisiopatológico das complicações:**\n"
            "A pancitopenia grave expõe o paciente a três riscos principais: infecção (neutropenia), "
            "sangramento (plaquetopenia) e sintomas de hipóxia (anemia). A gravidade é classificada "
            "pelos critérios de Camitta (neutrófilos, plaquetas, reticulócitos).\n\n"
            "**Sepse neutropênica:**\n"
            "Com neutrófilos < 500/mm³, qualquer infecção pode progredir rapidamente para sepse. "
            "Gram-negativos (Pseudomonas, E. coli) e Aspergillus são os principais agentes. "
            "Febre em neutropênico é emergência — antibioticoterapia de amplo espectro imediata "
            "(ex: cefepima) após coleta de culturas.\n\n"
            "**Sangramento:**\n"
            "Com plaquetas < 10.000/mm³, há risco de sangramento espontâneo, incluindo hemorragia "
            "intracraniana. Transfusão profilática de plaquetas está indicada. Evitar AAS e AINEs. "
            "Menorragia pode ser controlada com contraceptivos orais."
        )
    else:
        parts.append(f"As complicações específicas de {diag} devem ser monitoradas.")
    
    # Explicar por que as outras alternativas estão incorretas
    parts.append("\n\n**Por que as outras alternativas estão incorretas:**\n")
    for conf in confounders[:3]:
        parts.append(f"- **{conf['diag']}:** {conf['justificativa']}.\n")
    
    return "".join(parts)


def _format_alternatives(options: list[str]) -> list[str]:
    letters = ["A", "B", "C", "D"]
    return [f"({letter}) {text}" for letter, text in zip(letters, options)]


# Perfis clínicos EXPANDIDOS para distratores plausíveis com sobreposição de achados
CLINICAL_SCENARIOS = {
    "Anemia ferropriva": {
        "vinheta": (
            "Mulher de {age} anos, diarista, comparece à UBS com queixa de fadiga progressiva "
            "e dispneia aos médios esforços há {duration}. Refere ciclos menstruais regulares, "
            "porém intensos, com duração de 7 a 8 dias. Nega sangramentos gastrointestinais ou "
            "perda ponderal. Ao exame: mucosas hipocoradas (++/4+), FC 92 bpm, PA 110x70 mmHg, "
            "sem hepatoesplenomegalia. Unhas quebradiças e queilite angular discreta."
        ),
        "labs_completos": """
┌─────────────────────────┬─────────────┬─────────────────┐
│ Exame                   │ Resultado   │ Referência      │
├─────────────────────────┼─────────────┼─────────────────┤
│ Hemoglobina             │  8,4 g/dL   │ 12-16 g/dL      │
│ Hematócrito             │  26%        │ 36-48%          │
│ VCM                     │  68 fL      │ 80-100 fL       │
│ HCM                     │  22 pg      │ 27-34 pg        │
│ RDW                     │  18%        │ 11,5-14,5%      │
│ Reticulócitos           │  0,8%       │ 0,5-2,0%        │
│ Ferritina               │  8 ng/mL    │ 30-300 ng/mL    │
│ Ferro sérico            │  25 µg/dL   │ 60-170 µg/dL    │
│ TIBC                    │  480 µg/dL  │ 250-370 µg/dL   │
│ Saturação transferrina  │  5%         │ 20-50%          │
│ Leucócitos              │  6.800/mm³  │ 4.000-11.000    │
│ Plaquetas               │  420.000    │ 150.000-450.000 │
└─────────────────────────┴─────────────┴─────────────────┘""",
        "labs_parciais": [
            "Hemoglobina 8,4 g/dL; VCM 68 fL; RDW 18%",
            "Ferritina 8 ng/mL; ferro sérico baixo; TIBC elevado",
            "Hemoglobina baixa com microcitose e hipocromia",
        ],
        "diag_correto": "Anemia ferropriva",
        "conduta_correta": "solicitar endoscopia digestiva alta e colonoscopia para investigação etiológica; iniciar sulfato ferroso 200 mg, 3 vezes ao dia",
        "tratamento": "sulfato ferroso 200 mg VO 3x/dia, longe das refeições, por 3-6 meses; reavaliar em 30 dias com reticulócitos",
    },
    "Anemia megaloblástica por deficiência de vitamina B12": {
        "vinheta": (
            "Homem de {age} anos, vegetariano estrito há 8 anos, procura atendimento por "
            "parestesias em mãos e pés há {duration}, associadas a fadiga, dificuldade de "
            "concentração e alteração de marcha progressiva. Refere episódios de glossite "
            "e queda capilar. Ao exame: mucosas hipocoradas (+/4+), glossite atrófica, "
            "reflexos aquileus diminuídos bilateralmente, Romberg positivo."
        ),
        "labs_completos": """
┌────────────────────────┬────────────────────────────┬─────────────────┐
│ Exame                  │ Resultado                  │ Referência      │
├────────────────────────┼────────────────────────────┼─────────────────┤
│ Hemoglobina            │  9,2 g/dL                  │ 13-17 g/dL      │
│ Hematócrito            │  28%                       │ 40-54%          │
│ VCM                    │  118 fL                    │ 80-100 fL       │
│ HCM                    │  34 pg                     │ 27-34 pg        │
│ RDW                    │  16%                       │ 11,5-14,5%      │
│ Reticulócitos          │  1,0%                      │ 0,5-2,0%        │
│ Vitamina B12           │  95 pg/mL                  │ 200-900 pg/mL   │
│ Ácido fólico           │  12 ng/mL                  │ 3-17 ng/mL      │
│ Homocisteína           │  48 µmol/L                 │ 5-15 µmol/L     │
│ Ácido metilmalônico    │  1.200 nmol/L              │ <370 nmol/L     │
│ LDH                    │  890 U/L                   │ 135-225 U/L     │
│ Bilirrubina indireta   │  1,8 mg/dL                 │ 0,1-0,8 mg/dL   │
│ Leucócitos             │  3.200/mm³                 │ 4.000-11.000    │
│ Plaquetas              │  130.000/mm³               │ 150.000-450.000 │
│ Esfregaço              │  neutrófilos hipersegment. │ —               │
└────────────────────────┴────────────────────────────┴─────────────────┘""",
        "labs_parciais": [
            "Hemoglobina 9,2 g/dL; VCM 118 fL; neutrófilos hipersegmentados",
            "LDH 890 U/L; bilirrubina indireta 1,8 mg/dL; B12 95 pg/mL",
            "Pancitopenia leve com macrocitose acentuada",
        ],
        "diag_correto": "Anemia megaloblástica por deficiência de vitamina B12",
        "conduta_correta": "iniciar cianocobalamina 1000 mcg IM diária por 7 dias, depois semanal por 4 semanas; avaliar resposta neurológica",
        "tratamento": "cianocobalamina 1000 mcg IM: diária por 7 dias → semanal por 4 semanas → mensal vitalícia",
    },
    "Anemia da doença crônica": {
        "vinheta": (
            "Mulher de {age} anos, em acompanhamento por artrite reumatoide há 10 anos, "
            "comparece com queixa de fadiga e dispneia aos esforços há {duration}. Refere "
            "controle irregular da doença de base, com sinovites frequentes. Nega sangramentos "
            "ou alterações do hábito intestinal. Ao exame: mucosas levemente hipocoradas, "
            "sinovite em punhos bilateralmente, sem hepatoesplenomegalia."
        ),
        "labs_completos": """
┌────────────────────────┬─────────────┬─────────────────┐
│ Exame                  │ Resultado   │ Referência      │
├────────────────────────┼─────────────┼─────────────────┤
│ Hemoglobina            │  9,8 g/dL   │ 12-16 g/dL      │
│ Hematócrito            │  30%        │ 36-48%          │
│ VCM                    │  82 fL      │ 80-100 fL       │
│ HCM                    │  27 pg      │ 27-34 pg        │
│ RDW                    │  14%        │ 11,5-14,5%      │
│ Reticulócitos          │  0,9%       │ 0,5-2,0%        │
│ Ferritina              │  280 ng/mL  │ 30-300 ng/mL    │
│ Ferro sérico           │  35 µg/dL   │ 60-170 µg/dL    │
│ TIBC                   │  180 µg/dL  │ 250-370 µg/dL   │
│ Saturação transferrina │  19%        │ 20-50%          │
│ PCR                    │  45 mg/L    │ <5 mg/L         │
│ VHS                    │  68 mm/h    │ <20 mm/h        │
│ Leucócitos             │  9.200/mm³  │ 4.000-11.000    │
│ Plaquetas              │  380.000    │ 150.000-450.000 │
└────────────────────────┴─────────────┴─────────────────┘""",
        "labs_parciais": [
            "Hemoglobina 9,8 g/dL; VCM 82 fL; ferritina 280 ng/mL com ferro sérico baixo",
            "Ferritina elevada; TIBC baixo; PCR 45 mg/L; VHS 68 mm/h",
            "Anemia normocítica com perfil de ferro dissociado e inflamação ativa",
        ],
        "diag_correto": "Anemia da doença crônica",
        "conduta_correta": "otimizar tratamento da artrite reumatoide com imunossupressor; evitar reposição de ferro oral isolada",
        "tratamento": "controle da doença de base; considerar eritropoetina se Hb < 10 g/dL sintomática; ferro IV se ferropenia associada comprovada",
    },
    "Anemia hemolítica autoimune": {
        "vinheta": (
            "Mulher de {age} anos, previamente hígida, procura emergência com icterícia "
            "e urina escura há {duration}. Refere quadro gripal há 2 semanas, com resolução "
            "espontânea. Nega uso de medicamentos ou doenças prévias. Ao exame: ictérica (+/4+), "
            "mucosas hipocoradas (++/4+), baço palpável a 2 cm do RCE, sem hepatomegalia."
        ),
        "labs_completos": """
┌─────────────────────┬──────────────────────┬─────────────────┐
│ Exame               │ Resultado            │ Referência      │
├─────────────────────┼──────────────────────┼─────────────────┤
│ Hemoglobina         │  7,8 g/dL            │ 12-16 g/dL      │
│ Hematócrito         │  24%                 │ 36-48%          │
│ VCM                 │  105 fL              │ 80-100 fL       │
│ HCM                 │  34 pg               │ 27-34 pg        │
│ RDW                 │  18%                 │ 11,5-14,5%      │
│ Reticulócitos       │  12%                 │ 0,5-2,0%        │
│ LDH                 │  780 U/L             │ 135-225 U/L     │
│ Bilirrubina total   │  4,2 mg/dL           │ 0,3-1,2 mg/dL   │
│ Bilirrubina indireta│  3,6 mg/dL           │ 0,1-0,8 mg/dL   │
│ Haptoglobina        │  <10 mg/dL           │ 30-200 mg/dL    │
│ Coombs direto       │  positivo (IgG+C3d)  │ negativo        │
│ Leucócitos          │  11.400/mm³          │ 4.000-11.000    │
│ Plaquetas           │  245.000/mm³         │ 150.000-450.000 │
│ Esfregaço           │  esferócitos         │ —               │
└─────────────────────┴──────────────────────┴─────────────────┘""",
        "labs_parciais": [
            "Hemoglobina 7,8 g/dL; reticulócitos 12%; LDH 780 U/L",
            "Bilirrubina indireta 3,6 mg/dL; haptoglobina indetectável; Coombs direto positivo",
            "Anemia com sinais de hemólise e esferócitos em esfregaço",
        ],
        "diag_correto": "Anemia hemolítica autoimune",
        "conduta_correta": "iniciar prednisona 1 mg/kg/dia; solicitar sorologias para doenças linfoproliferativas e autoimunes",
        "tratamento": "prednisona 1 mg/kg/dia VO; considerar rituximabe ou esplenectomia se refratária; suporte transfusional se instabilidade",
    },
    "Doença da aglutinina fria": {
        "vinheta": (
            "Paciente de {age} anos, com história recente de infecção respiratória, procura emergência por "
            "fadiga, acrocianose e urina escura há {duration}. Refere piora dos sintomas ao frio. "
            "Ao exame: icterícia discreta, extremidades frias e sem sangramento ativo."
        ),
        "labs_completos": """
┌─────────────────────┬──────────────────────┬─────────────────┐
│ Exame               │ Resultado            │ Referência      │
├─────────────────────┼──────────────────────┼─────────────────┤
│ Hemoglobina         │  8,6 g/dL            │ 12-16 g/dL      │
│ VCM                 │  101 fL              │ 80-100 fL       │
│ Reticulócitos       │  8,0%                │ 0,5-2,0%        │
│ LDH                 │  690 U/L             │ 135-225 U/L     │
│ Bilirrubina indireta│  2,4 mg/dL           │ 0,1-0,8 mg/dL   │
│ Haptoglobina        │  12 mg/dL            │ 30-200 mg/dL    │
│ Coombs direto       │  C3 positivo / IgG - │ negativo        │
│ Crioaglutininas     │  título elevado      │ negativo        │
└─────────────────────┴──────────────────────┴─────────────────┘""",
        "labs_parciais": [
            "Hemoglobina 8,6 g/dL; reticulócitos 8%; Coombs com C3 positivo",
            "Hemólise com piora ao frio e acrocianose",
            "LDH elevado, bilirrubina indireta elevada e crioaglutininas positivas",
        ],
        "diag_correto": "Doença da aglutinina fria",
        "conduta_correta": "evitar exposição ao frio; pesquisar doença linfoproliferativa; considerar rituximabe em casos sintomáticos",
        "tratamento": "medidas de proteção térmica; rituximabe em monoterapia ou combinação conforme gravidade",
    },
    "Deficiência de G6PD": {
        "vinheta": (
            "Homem de {age} anos, previamente hígido, apresenta icterícia e colúria há {duration}, "
            "após uso de sulfonamida para infecção urinária. Refere dor lombar leve e fadiga. "
            "Ao exame: ictérico, sem esplenomegalia importante, hemodinamicamente estável."
        ),
        "labs_completos": """
┌─────────────────────┬──────────────────────┬─────────────────┐
│ Exame               │ Resultado            │ Referência      │
├─────────────────────┼──────────────────────┼─────────────────┤
│ Hemoglobina         │  7,9 g/dL            │ 12-16 g/dL      │
│ VCM                 │  98 fL               │ 80-100 fL       │
│ Reticulócitos       │  10,5%               │ 0,5-2,0%        │
│ LDH                 │  840 U/L             │ 135-225 U/L     │
│ Bilirrubina indireta│  3,1 mg/dL           │ 0,1-0,8 mg/dL   │
│ Haptoglobina        │  <10 mg/dL           │ 30-200 mg/dL    │
│ Coombs direto       │  negativo            │ negativo        │
│ Esfregaço           │  bite cells / Heinz  │ ausentes        │
└─────────────────────┴──────────────────────┴─────────────────┘""",
        "labs_parciais": [
            "Crise hemolítica após fármaco oxidante; Coombs negativo",
            "Reticulocitose, LDH elevado e haptoglobina baixa",
            "Esfregaço com bite cells e corpos de Heinz",
        ],
        "diag_correto": "Deficiência de G6PD",
        "conduta_correta": "suspender agente oxidante; suporte clínico e hidratação; orientar prevenção de novos gatilhos",
        "tratamento": "retirada de desencadeante, hidratação e suporte transfusional quando indicado",
    },
    "Esferocitose hereditária": {
        "vinheta": (
            "Paciente de {age} anos com história familiar de anemia e esplenectomia em parentes de 1º grau, "
            "refere icterícia intermitente e fadiga crônica há {duration}. Ao exame: palidez discreta e "
            "esplenomegalia leve, sem sinais de sangramento ativo."
        ),
        "labs_completos": """
┌─────────────────────┬──────────────────────┬─────────────────┐
│ Exame               │ Resultado            │ Referência      │
├─────────────────────┼──────────────────────┼─────────────────┤
│ Hemoglobina         │  9,4 g/dL            │ 12-16 g/dL      │
│ VCM                 │  90 fL               │ 80-100 fL       │
│ CHCM                │  37 g/dL             │ 32-36 g/dL      │
│ Reticulócitos       │  7,2%                │ 0,5-2,0%        │
│ LDH                 │  520 U/L             │ 135-225 U/L     │
│ Bilirrubina indireta│  2,2 mg/dL           │ 0,1-0,8 mg/dL   │
│ Coombs direto       │  negativo            │ negativo        │
│ EMA (eosina-5-m.)   │  reduzido            │ normal          │
└─────────────────────┴──────────────────────┴─────────────────┘""",
        "labs_parciais": [
            "Anemia hemolítica crônica com Coombs negativo",
            "Reticulocitose e CHCM elevado",
            "História familiar positiva e esplenomegalia",
        ],
        "diag_correto": "Esferocitose hereditária",
        "conduta_correta": "confirmar com EMA/fragilidade osmótica; suplementar ácido fólico; avaliar esplenectomia em casos moderados a graves",
        "tratamento": "ácido fólico contínuo; esplenectomia seletiva em doença sintomática relevante",
    },
    "Anemia hemolítica microangiopática (PTT)": {
        "vinheta": (
            "Mulher de {age} anos procura emergência com fadiga intensa, confusão mental leve e petéquias há {duration}. "
            "Refere urina escura e cefaleia. Ao exame: palidez, petéquias em membros inferiores e déficit neurológico focal transitório."
        ),
        "labs_completos": """
┌─────────────────────┬──────────────────────┬─────────────────┐
│ Exame               │ Resultado            │ Referência      │
├─────────────────────┼──────────────────────┼─────────────────┤
│ Hemoglobina         │  7,1 g/dL            │ 12-16 g/dL      │
│ Plaquetas           │  22.000/mm³          │ 150.000-450.000 │
│ Reticulócitos       │  9,6%                │ 0,5-2,0%        │
│ LDH                 │  1.050 U/L           │ 135-225 U/L     │
│ Bilirrubina indireta│  2,8 mg/dL           │ 0,1-0,8 mg/dL   │
│ Haptoglobina        │  <10 mg/dL           │ 30-200 mg/dL    │
│ Coombs direto       │  negativo            │ negativo        │
│ Esfregaço           │  esquizócitos > 2%   │ ausentes        │
└─────────────────────┴──────────────────────┴─────────────────┘""",
        "labs_parciais": [
            "Anemia hemolítica com plaquetopenia grave e esquizócitos",
            "LDH muito elevado; Coombs negativo",
            "Sintomas neurológicos e lesão de órgão-alvo",
        ],
        "diag_correto": "Anemia hemolítica microangiopática (PTT)",
        "conduta_correta": "iniciar plasmaférese imediata e corticoterapia; evitar transfusão profilática de plaquetas",
        "tratamento": "plasmaférese de urgência diária até remissão; imunossupressão conforme protocolo",
    },
    "Anemia aplásica": {
        "vinheta": (
            "Jovem de {age} anos, sem comorbidades, procura emergência com sangramento "
            "gengival espontâneo, petéquias em membros inferiores e febre há {duration}. "
            "Refere episódios de amigdalite de repetição no último mês. Nega uso de "
            "medicamentos, exposição a tóxicos ou viagens recentes. Ao exame: hipocorado (+++/4+), "
            "febril (38,2°C), petéquias disseminadas, gengivorragia ativa, sem hepatoesplenomegalia."
        ),
        "labs_completos": """
┌────────────────────┬─────────────────┬─────────────────┐
│ Exame              │ Resultado       │ Referência      │
├────────────────────┼─────────────────┼─────────────────┤
│ Hemoglobina        │  6,2 g/dL       │ 12-16 g/dL      │
│ Hematócrito        │  19%            │ 36-48%          │
│ VCM                │  94 fL          │ 80-100 fL       │
│ HCM                │  31 pg          │ 27-34 pg        │
│ RDW                │  13%            │ 11,5-14,5%      │
│ Reticulócitos      │  0,2%           │ 0,5-2,0%        │
│ Leucócitos         │  1.100/mm³      │ 4.000-11.000    │
│ Neutrófilos        │  220/mm³        │ 1.500-7.000     │
│ Linfócitos         │  770/mm³        │ 1.000-4.000     │
│ Plaquetas          │  8.000/mm³      │ 150.000-450.000 │
│ Ferritina          │  450 ng/mL      │ 30-300 ng/mL    │
│ LDH                │  180 U/L        │ 135-225 U/L     │
│ Bilirrubinas       │  normais        │ —               │
└────────────────────┴─────────────────┴─────────────────┘""",
        "labs_parciais": [
            "Hemoglobina 6,2 g/dL; leucócitos 1.100/mm³ (neutrófilos 220/mm³); plaquetas 8.000/mm³",
            "Pancitopenia grave com reticulócitos 0,2%; ferritina elevada",
            "Pancitopenia com hipoplasia medular",
        ],
        "diag_correto": "Anemia aplásica",
        "conduta_correta": "internação em isolamento protetor; suporte transfusional; antibioticoterapia de amplo espectro; encaminhar para hematologia",
        "tratamento": "suporte transfusional; ATG + ciclosporina para não candidatos a transplante; TCTH alogênico para jovens com doador compatível",
    },
}

# Distratores que criam confusão diagnóstica real
DISTRACTORS_BY_SCENARIO = {
    "Anemia ferropriva": {
        "confounders": [
            {
                "diag": "Anemia da doença crônica",
                "justificativa": "também pode apresentar ferro sérico baixo, mas ferritina estará normal/elevada e TIBC baixo",
                "conduta_errada": "iniciar tratamento imunossupressor e evitar suplementação de ferro",
            },
            {
                "diag": "Talassemia minor",
                "justificativa": "também causa microcitose, mas RDW tende a ser normal e ferritina não está baixa",
                "conduta_errada": "aconselhamento genético e evitar suplementação de ferro",
            },
            {
                "diag": "Anemia sideroblástica",
                "justificativa": "microcítica com ferro sérico normal ou elevado e sideroblastos em anel na medula",
                "conduta_errada": "piridoxina em altas doses e quelação de ferro",
            },
        ],
    },
    "Anemia megaloblástica por deficiência de vitamina B12": {
        "confounders": [
            {
                "diag": "Anemia megaloblástica por deficiência de folato",
                "justificativa": "também macrocítica com megaloblastos, mas sem sintomas neurológicos e ácido metilmalônico normal",
                "conduta_errada": "ácido fólico 5 mg/dia isolado",
            },
            {
                "diag": "Síndrome mielodisplásica",
                "justificativa": "também pode causar macrocitose e citopenias, mas com displasia medular e sem resposta à B12",
                "conduta_errada": "azacitidina e suporte transfusional",
            },
            {
                "diag": "Anemia hemolítica",
                "justificativa": "também eleva LDH e bilirrubina indireta, mas reticulócitos estarão elevados e VCM pode ser normal",
                "conduta_errada": "prednisona 1 mg/kg/dia e investigação de hemólise",
            },
        ],
    },
    "Anemia da doença crônica": {
        "confounders": [
            {
                "diag": "Anemia ferropriva",
                "justificativa": "também tem ferro sérico baixo, mas ferritina estará baixa e TIBC elevado",
                "conduta_errada": "sulfato ferroso 200 mg VO 3x/dia por 6 meses",
            },
            {
                "diag": "Anemia ferropriva + doença crônica (mista)",
                "justificativa": "pode ocorrer quando ferritina está entre 30-100 ng/mL em contexto inflamatório",
                "conduta_errada": "ferro IV isolado sem tratar a doença de base",
            },
            {
                "diag": "Insuficiência renal crônica",
                "justificativa": "também causa anemia normocítica por déficit de EPO, mas creatinina estará elevada",
                "conduta_errada": "eritropoetina recombinante em monoterapia",
            },
        ],
    },
    "Anemia hemolítica autoimune": {
        "confounders": [
            {
                "diag": "Esferocitose hereditária",
                "justificativa": "também tem esferócitos e esplenomegalia, mas Coombs direto é negativo e história familiar positiva",
                "conduta_errada": "esplenectomia eletiva sem corticoterapia prévia",
            },
            {
                "diag": "Anemia megaloblástica",
                "justificativa": "também eleva LDH e BI por hemólise intramedular, mas reticulócitos baixos e macrocitose acentuada",
                "conduta_errada": "cianocobalamina 1000 mcg IM",
            },
            {
                "diag": "Púrpura trombocitopênica trombótica",
                "justificativa": "também tem anemia + hemólise, mas com esquizócitos, plaquetopenia e alteração neurológica",
                "conduta_errada": "plasmaférese de urgência",
            },
        ],
    },
    "Doença da aglutinina fria": {
        "confounders": [
            {
                "diag": "Anemia hemolítica autoimune",
                "justificativa": "também cursa com hemólise e Coombs positivo, porém na aglutinina fria predomina C3 e piora com frio",
                "conduta_errada": "prednisona isolada em altas doses como primeira escolha",
            },
            {
                "diag": "Hemoglobinúria paroxística noturna",
                "justificativa": "hemólise intravascular com Coombs negativo e risco trombótico, sem crioaglutininas",
                "conduta_errada": "eculizumabe de imediato sem investigação de complemento",
            },
            {
                "diag": "Deficiência de G6PD",
                "justificativa": "hemólise após gatilho oxidante com Coombs negativo e bite cells",
                "conduta_errada": "apenas retirar fármaco sem proteção térmica e sem investigação etiológica",
            },
        ],
    },
    "Deficiência de G6PD": {
        "confounders": [
            {
                "diag": "Anemia hemolítica autoimune",
                "justificativa": "na AHAI o Coombs tende a ser positivo, ao contrário da G6PD",
                "conduta_errada": "corticoterapia prolongada sem retirada de gatilho oxidante",
            },
            {
                "diag": "Esferocitose hereditária",
                "justificativa": "também hemólise crônica, mas com história familiar típica e EMA reduzido",
                "conduta_errada": "encaminhar para esplenectomia na fase aguda sem confirmação",
            },
            {
                "diag": "Doença da aglutinina fria",
                "justificativa": "hemólise por complemento e piora ao frio, geralmente sem bite cells",
                "conduta_errada": "orientar apenas evitar frio sem retirar agentes oxidantes",
            },
        ],
    },
    "Esferocitose hereditária": {
        "confounders": [
            {
                "diag": "Anemia hemolítica autoimune",
                "justificativa": "esferócitos podem ocorrer em ambas, mas Coombs é negativo na esferocitose",
                "conduta_errada": "iniciar prednisona contínua como terapia principal",
            },
            {
                "diag": "Deficiência de G6PD",
                "justificativa": "G6PD é episódica e relacionada a gatilho oxidante, com bite cells",
                "conduta_errada": "focar somente em gatilho oxidante e não avaliar membrana eritrocitária",
            },
            {
                "diag": "Anemia hemolítica microangiopática (PTT)",
                "justificativa": "PTT cursa com esquizócitos e plaquetopenia acentuada",
                "conduta_errada": "iniciar plasmaférese sem critério clínico-laboratorial",
            },
        ],
    },
    "Anemia hemolítica microangiopática (PTT)": {
        "confounders": [
            {
                "diag": "Anemia hemolítica autoimune",
                "justificativa": "AHAI costuma ter Coombs positivo e plaquetas preservadas",
                "conduta_errada": "corticoterapia isolada sem plasmaférese",
            },
            {
                "diag": "Síndrome hemolítico-urêmica",
                "justificativa": "também microangiopática, com predominância renal e contexto infeccioso típico",
                "conduta_errada": "antibiótico empírico de rotina em toda apresentação microangiopática",
            },
            {
                "diag": "Coagulação intravascular disseminada",
                "justificativa": "pode cursar com esquizócitos, mas com coagulograma consumptivo alterado",
                "conduta_errada": "plasmaférese como única medida terapêutica",
            },
        ],
    },
    "Anemia aplásica": {
        "confounders": [
            {
                "diag": "Leucemia aguda",
                "justificativa": "também causa pancitopenia, mas com blastos em sangue periférico ou medula e organomegalia frequente",
                "conduta_errada": "quimioterapia de indução com antraciclina + citarabina",
            },
            {
                "diag": "Síndrome mielodisplásica",
                "justificativa": "também causa citopenias com medula normo/hipercelular e displasia",
                "conduta_errada": "agentes hipometilantes",
            },
            {
                "diag": "Hemoglobinúria paroxística noturna",
                "justificativa": "pode evoluir de aplasia; citometria de fluxo mostra deficiência de GPI",
                "conduta_errada": "eculizumabe e suporte transfusional",
            },
        ],
    },
}


CLINICAL_CASE_VARIANTS = {
    "Anemia ferropriva": [
        "Mulher de {age} anos, com menorragia há 6 meses, relata fadiga progressiva e pica por gelo há {duration}. Ao exame: palidez cutâneo-mucosa, queilite angular e coiloníquia discreta.",
        "Homem de {age} anos, refere astenia e queda de performance funcional há {duration}, associado a epigastralgia e uso crônico de AINE. Ao exame: palidez e taquicardia leve.",
        "Mulher de {age} anos, submetida à cirurgia bariátrica há 2 anos, procura UBS por dispneia aos esforços e tontura há {duration}. Ao exame: mucosas hipocoradas e unhas frágeis.",
        "Gestante de {age} anos no 2º trimestre, com dieta restritiva, queixa-se de fadiga importante há {duration}. Ao exame: palidez e sopro sistólico funcional discreto.",
        "Mulher de {age} anos com sangramento uterino anormal, descreve cefaleia e fraqueza há {duration}. Ao exame: palidez ++/4+, sem organomegalias.",
    ],
    "Anemia megaloblástica por deficiência de vitamina B12": [
        "Homem de {age} anos, vegetariano estrito há 10 anos, apresenta parestesias em pés e mãos, instabilidade de marcha e fadiga há {duration}. Ao exame: Romberg positivo e glossite atrófica.",
        "Mulher de {age} anos, com gastrite atrófica autoimune, refere piora cognitiva leve e dormência distal há {duration}. Ao exame: palidez, hipoestesia vibratória e reflexos aquileus diminuídos.",
        "Homem de {age} anos, pós-gastrectomia subtotal, procura atendimento por astenia, glossite e dificuldade de concentração há {duration}. Ao exame: mucosas hipocoradas e língua despapilada.",
        "Mulher de {age} anos com doença de Crohn ileal, relata fadiga e parestesias simétricas há {duration}. Ao exame: marcha atáxica e sinal de Romberg.",
        "Homem de {age} anos com uso prolongado de metformina e IBP, apresenta fraqueza, formigamento distal e queda de memória recente há {duration}. Ao exame: déficit sensitivo em membros inferiores.",
    ],
    "Anemia da doença crônica": [
        "Mulher de {age} anos com artrite reumatoide ativa, refere fadiga e limitação ao esforço há {duration}. Ao exame: sinovite em punhos e palidez discreta.",
        "Homem de {age} anos com tuberculose pulmonar em tratamento irregular, relata astenia e perda funcional há {duration}. Ao exame: palidez leve e estado inflamatório sistêmico.",
        "Mulher de {age} anos com lúpus eritematoso sistêmico, queixa-se de cansaço progressivo há {duration}. Ao exame: artralgia ativa e mucosas hipocoradas.",
        "Homem de {age} anos com neoplasia colorretal em quimioterapia, apresenta fadiga persistente há {duration}. Ao exame: palidez leve e sem sinais de sangramento agudo.",
        "Mulher de {age} anos com osteomielite crônica, relata intolerância ao exercício e fadiga há {duration}. Ao exame: palidez e dor inflamatória local.",
    ],
    "Anemia hemolítica autoimune": [
        "Mulher de {age} anos, após infecção viral recente, evolui com icterícia, urina escura e fadiga há {duration}. Ao exame: esplenomegalia discreta e palidez.",
        "Homem de {age} anos com lúpus em atividade, apresenta queda de hemoglobina, icterícia e colúria há {duration}. Ao exame: baço palpável e sem hepatomegalia.",
        "Mulher de {age} anos com história de linfoma em remissão, procura emergência por dispneia, colúria e tontura há {duration}. Ao exame: ictérica e taquicárdica.",
        "Homem de {age} anos sem comorbidades, com quadro gripal prévio, relata urina escura e fraqueza intensa há {duration}. Ao exame: icterícia e dor em hipocôndrio esquerdo.",
        "Mulher de {age} anos no puerpério, apresenta icterícia progressiva e queda funcional há {duration}. Ao exame: palidez e esplenomegalia leve.",
    ],
    "Doença da aglutinina fria": [
        "Paciente de {age} anos com acrocianose e piora da colúria após exposição ao frio há {duration}. Ao exame: extremidades frias e palidez discreta.",
        "Mulher de {age} anos com infecção respiratória recente, evolui com hemólise e piora ao clima frio há {duration}. Ao exame: icterícia leve e livedo em extremidades.",
        "Homem de {age} anos com fadiga e urina escura, relata desencadeio dos sintomas durante viagem para região fria há {duration}. Ao exame: acrocianose e taquicardia discreta.",
        "Paciente de {age} anos com fenômeno de Raynaud prévio, apresenta anemia hemolítica e desconforto acral há {duration}. Ao exame: cianose periférica transitória.",
        "Mulher de {age} anos com quadro pós-viral, evolui com anemia hemolítica e intolerância ao frio há {duration}. Ao exame: ictérica +/4+ e extremidades pálidas ao frio.",
    ],
    "Deficiência de G6PD": [
        "Homem de {age} anos com colúria e icterícia após uso de dapsona há {duration}. Ao exame: palidez e dor lombar leve.",
        "Paciente de {age} anos com hemólise aguda após consumo de favas há {duration}. Ao exame: icterícia e fadiga intensa.",
        "Homem de {age} anos com infecção bacteriana recente, evolui com queda abrupta de Hb e urina escura há {duration}. Ao exame: hemodinamicamente estável, ictérico.",
        "Paciente de {age} anos com automedicação antibiótica, apresenta crise hemolítica súbita há {duration}. Ao exame: palidez +++/4+ e sem esplenomegalia importante.",
        "Homem de {age} anos com dor abdominal leve e colúria após antimalárico há {duration}. Ao exame: icterícia discreta e taquicardia.",
    ],
    "Esferocitose hereditária": [
        "Paciente de {age} anos com histórico familiar de esplenectomia, refere icterícia intermitente e fadiga há {duration}. Ao exame: esplenomegalia leve.",
        "Homem de {age} anos com litíase biliar pigmentária prévia e anemia crônica há {duration}. Ao exame: palidez e baço palpável.",
        "Mulher de {age} anos com episódios recorrentes de icterícia desde adolescência, piora clínica há {duration}. Ao exame: sem sangramento ativo, com esplenomegalia discreta.",
        "Paciente de {age} anos com anemia hemolítica compensada há anos, apresenta descompensação após infecção viral há {duration}. Ao exame: palidez e subicterícia.",
        "Homem de {age} anos com fadiga crônica e antecedente familiar positivo para anemia hemolítica há {duration}. Ao exame: baço palpável a 2 cm do RCE.",
    ],
    "Anemia hemolítica microangiopática (PTT)": [
        "Mulher de {age} anos com petéquias, confusão e colúria há {duration}. Ao exame: déficit neurológico transitório e palidez intensa.",
        "Paciente de {age} anos com fadiga, plaquetopenia grave e disfunção renal inicial há {duration}. Ao exame: petéquias e estado geral comprometido.",
        "Mulher de {age} anos com cefaleia, febre baixa e anemia hemolítica abrupta há {duration}. Ao exame: palidez +++/4+ e equimoses.",
        "Paciente de {age} anos em pós-parto recente, evolui com hemólise, trombocitopenia e alteração neurológica há {duration}. Ao exame: confusão leve e petéquias.",
        "Homem de {age} anos com dispneia e cansaço progressivo, associado a petéquias e urina escura há {duration}. Ao exame: palidez e sinais de microangiopatia.",
    ],
    "Anemia aplásica": [
        "Paciente de {age} anos com petéquias, gengivorragia e febre intermitente há {duration}. Ao exame: palidez importante, sem hepatoesplenomegalia.",
        "Paciente de {age} anos com história ocupacional de exposição a benzeno, relata fadiga intensa, infecções de repetição e equimoses há {duration}. Ao exame: palidez +++/4+.",
        "Paciente de {age} anos em uso prévio de cloranfenicol, evolui com sangramento gengival e febre há {duration}. Ao exame: petéquias disseminadas e ausência de organomegalias.",
        "Paciente de {age} anos com hepatite viral recente, apresenta fraqueza acentuada, epistaxe e infecção recorrente há {duration}. Ao exame: hipocorado, sem linfonodomegalias.",
        "Paciente de {age} anos com quadro de odinofagia frequente e hematomas espontâneos há {duration}. Ao exame: plaquetopatia clínica e sem esplenomegalia.",
    ],
}


ENAMED_CASE_COMPLEMENTS = {
    "Anemia ferropriva": {
        "contexto": [
            "Relata piora da tolerância ao exercício, cefaleia vespertina e sonolência diurna, sem febre ou perda ponderal importante.",
            "Refere queda de cabelo e unhas quebradiças no último trimestre, com manutenção do apetite habitual.",
            "Nega uso de suplementos de ferro prévios e informa adesão alimentar irregular por rotina de trabalho extensa.",
        ],
        "antecedentes": [
            "Antecedentes: sem comorbidades relevantes; nega tabagismo e etilismo pesado.",
            "Antecedentes: sem doença renal ou hepática; sem história familiar de hemoglobinopatias.",
            "Antecedentes: uso eventual de anti-inflamatórios; sem transfusões prévias.",
        ],
        "exame": [
            "Sinais vitais na admissão: FC 96 bpm, PA 108x68 mmHg, FR 18 irpm, SatO₂ 98% em ar ambiente.",
            "Exame físico complementar: ausculta cardiopulmonar sem alterações significativas e abdome sem visceromegalias.",
            "Estado geral preservado, porém com lentificação ao esforço e palidez cutaneomucosa difusa.",
        ],
    },
    "Anemia megaloblástica por deficiência de vitamina B12": {
        "contexto": [
            "Descreve formigamento distal progressivo, com piora noturna e dificuldade para caminhar em superfícies irregulares.",
            "Relata esquecimento recente e dificuldade de concentração no trabalho, além de glossite recorrente.",
            "Nega sangramento ativo, mas refere fadiga incapacitante para atividades habituais.",
        ],
        "antecedentes": [
            "Antecedentes: dieta com baixa ingesta de proteína animal; sem etilismo pesado.",
            "Antecedentes: história prévia de gastrite crônica, sem seguimento regular.",
            "Antecedentes: sem nefropatia crônica, sem uso de quimioterápicos mielotóxicos.",
        ],
        "exame": [
            "Sinais vitais na admissão: FC 90 bpm, PA 112x70 mmHg, FR 17 irpm, SatO₂ 97% em ar ambiente.",
            "Exame neurológico: redução de sensibilidade vibratória em membros inferiores e marcha de base alargada.",
            "Sem hepatoesplenomegalia; mucosas hipocoradas e língua despapilada ao exame da cavidade oral.",
        ],
    },
    "Anemia da doença crônica": {
        "contexto": [
            "Refere piora funcional progressiva, com limitação para atividades de rotina e rigidez matinal prolongada.",
            "Evolui com fadiga persistente apesar de tratamento irregular da doença inflamatória de base.",
            "Nega melena, hematoquezia ou metrorragia, e mantém padrão intestinal habitual.",
        ],
        "antecedentes": [
            "Antecedentes: doença inflamatória de longa data com baixa adesão ao seguimento ambulatorial.",
            "Antecedentes: sem história familiar de talassemia ou anemia hemolítica hereditária.",
            "Antecedentes: sem cirurgia bariátrica prévia e sem uso recente de reposição de ferro.",
        ],
        "exame": [
            "Sinais vitais na admissão: FC 88 bpm, PA 118x74 mmHg, FR 16 irpm, SatO₂ 98% em ar ambiente.",
            "Exame físico: palidez discreta, sem icterícia, sem linfonodomegalias e sem hepatoesplenomegalia.",
            "Achados inflamatórios articulares ativos ao exame osteoarticular, compatíveis com doença de base em atividade.",
        ],
    },
    "Anemia hemolítica autoimune": {
        "contexto": [
            "Refere colúria intermitente e piora da dispneia aos esforços nas últimas semanas, sem sangramento evidente.",
            "Episódios de icterícia flutuante com fadiga importante, especialmente após quadro infeccioso recente.",
            "Nega exposição recente a fármacos oxidantes e nega transfusão no último ano.",
        ],
        "antecedentes": [
            "Antecedentes: sem história familiar de hemoglobinopatias; sem esplenectomia prévia.",
            "Antecedentes: sem etilismo pesado e sem hepatopatia conhecida.",
            "Antecedentes: sem doença renal crônica, sem uso atual de quimioterapia.",
        ],
        "exame": [
            "Sinais vitais na admissão: FC 104 bpm, PA 106x66 mmHg, FR 20 irpm, SatO₂ 96% em ar ambiente.",
            "Exame físico: icterícia cutaneomucosa, esplenomegalia discreta e ausência de sinais de sangramento ativo.",
            "Estado geral regular, com palidez acentuada e dor leve em hipocôndrio esquerdo à palpação profunda.",
        ],
    },
    "Doença da aglutinina fria": {
        "contexto": [
            "Refere piora importante dos sintomas em ambientes frios e melhora parcial com aquecimento.",
            "Sem sangramento ativo, com episódios recorrentes de acrocianose em mãos e pés.",
            "Relata astenia progressiva e colúria intermitente desencadeada por exposição térmica.",
        ],
        "antecedentes": [
            "Antecedentes: infecção respiratória recente, sem uso de fármacos oxidantes.",
            "Antecedentes: investigação prévia para doença linfoproliferativa em andamento.",
            "Antecedentes: sem história familiar de membranopatias eritrocitárias.",
        ],
        "exame": [
            "Sinais vitais: FC 98 bpm, PA 112x70 mmHg, FR 18 irpm, SatO₂ 97% em ar ambiente.",
            "Exame físico: acrocianose distal, ictérica +/4+ e sem plaquetopenia clínica evidente.",
            "Estado geral regular, extremidades frias e sem organomegalia exuberante.",
        ],
    },
    "Deficiência de G6PD": {
        "contexto": [
            "Crise hemolítica após gatilho oxidante, com instalação aguda de colúria e icterícia.",
            "Nega história prévia de autoimunidade; refere uso recente de medicação desencadeante.",
            "Relata melhora parcial após suspensão do fármaco antes da admissão.",
        ],
        "antecedentes": [
            "Antecedentes: sem doença hematológica conhecida; sem transfusões recentes.",
            "Antecedentes: episódios prévios autolimitados após infecções febris.",
            "Antecedentes: sem história familiar bem definida, investigação genética pendente.",
        ],
        "exame": [
            "Sinais vitais: FC 102 bpm, PA 110x68 mmHg, FR 19 irpm, SatO₂ 97% em ar ambiente.",
            "Exame físico: icterícia ++/4+, palidez e dor lombar discreta à percussão.",
            "Sem esplenomegalia importante e sem sinais de sangramento ativo.",
        ],
    },
    "Esferocitose hereditária": {
        "contexto": [
            "Curso crônico com episódios de descompensação hemolítica após infecções intercorrentes.",
            "Refere histórico familiar positivo para anemia hemolítica e colelitíase precoce.",
            "Queixa-se de fadiga de longa data com piora gradual no último semestre.",
        ],
        "antecedentes": [
            "Antecedentes: sem uso recente de fármacos oxidantes; sem doenças autoimunes.",
            "Antecedentes: investigação hematológica prévia com suspeita de membranopatia.",
            "Antecedentes: sem doença renal crônica ou hepatopatia significativa.",
        ],
        "exame": [
            "Sinais vitais: FC 92 bpm, PA 116x72 mmHg, FR 17 irpm, SatO₂ 98% em ar ambiente.",
            "Exame físico: esplenomegalia discreta, subicterícia e palidez cutaneomucosa.",
            "Sem sinais neurológicos focais e sem manifestações hemorrágicas.",
        ],
    },
    "Anemia hemolítica microangiopática (PTT)": {
        "contexto": [
            "Evolução aguda com anemia hemolítica, plaquetopenia e manifestações neurológicas flutuantes.",
            "Relata cefaleia intensa e rebaixamento funcional nos últimos dias, sem sangramento volumoso.",
            "Queixa-se de colúria e fadiga extrema com piora rápida do estado geral.",
        ],
        "antecedentes": [
            "Antecedentes: sem doença hematológica prévia conhecida; sem anticoagulação crônica.",
            "Antecedentes: sem exposição recente a fármacos clássicos de hemólise oxidativa.",
            "Antecedentes: sem história familiar de membranopatias eritrocitárias.",
        ],
        "exame": [
            "Sinais vitais: FC 112 bpm, PA 104x64 mmHg, FR 22 irpm, SatO₂ 95% em ar ambiente.",
            "Exame físico: petéquias difusas, palidez acentuada e alteração neurológica leve.",
            "Estado geral grave, com sinais clínicos de microangiopatia trombótica ativa.",
        ],
    },
    "Anemia aplásica": {
        "contexto": [
            "Apresenta episódios recorrentes de febre e infecção de vias aéreas superiores no último trimestre.",
            "Refere equimoses espontâneas e sangramento gengival com piora progressiva da astenia.",
            "Nega dor óssea intensa, perda ponderal importante ou sudorese noturna profusa.",
        ],
        "antecedentes": [
            "Antecedentes: sem neoplasia hematológica conhecida; sem radioterapia prévia.",
            "Antecedentes: sem história familiar de síndrome de falência medular hereditária.",
            "Antecedentes: possível exposição a agentes mielotóxicos ocupacionais, em investigação.",
        ],
        "exame": [
            "Sinais vitais na admissão: FC 110 bpm, PA 102x64 mmHg, FR 22 irpm, SatO₂ 96% em ar ambiente, T 38,1°C.",
            "Exame físico: petéquias disseminadas, palidez +++/4+, sem hepatoesplenomegalia e sem adenomegalias.",
            "Sinais de sangramento cutaneomucoso ativo e estado geral comprometido, sem foco infeccioso evidente.",
        ],
    },
}


def _patient_vignette_enamed(scenario_key: str) -> str:
    """Gera vinheta clínica no estilo ENAMED com dados realistas."""
    scenario = CLINICAL_SCENARIOS[scenario_key]
    age = random.randint(25, 72)
    duration = random.choice(["duas semanas", "um mês", "três meses", "quatro meses"])
    templates = CLINICAL_CASE_VARIANTS.get(scenario_key)
    forced_variant = _FORCED_CASE_VARIANT_BY_DIAG.get(scenario_key)
    if templates:
        if forced_variant is None:
            chosen_template = random.choice(templates)
        else:
            chosen_template = templates[forced_variant % len(templates)]
        base = chosen_template.format(age=age, duration=duration)
    else:
        base = scenario["vinheta"].format(age=age, duration=duration)

    complements = ENAMED_CASE_COMPLEMENTS.get(scenario_key, {})
    contexto_list = complements.get("contexto", [""])
    antecedentes_list = complements.get("antecedentes", [""])
    exame_list = complements.get("exame", [""])

    if forced_variant is None:
        contexto = random.choice(contexto_list)
        antecedentes = random.choice(antecedentes_list)
        exame = random.choice(exame_list)
    else:
        contexto = contexto_list[forced_variant % len(contexto_list)] if contexto_list else ""
        antecedentes = antecedentes_list[forced_variant % len(antecedentes_list)] if antecedentes_list else ""
        exame = exame_list[forced_variant % len(exame_list)] if exame_list else ""

    return " ".join(part for part in [base, contexto, antecedentes, exame] if part).strip()


def _pick_distractors(scenario_key: str, n: int = 3) -> list[dict]:
    """Seleciona distratores clinicamente plausíveis."""
    confounders = DISTRACTORS_BY_SCENARIO[scenario_key]["confounders"]
    random.shuffle(confounders)
    return confounders[:n]


def _build_format_1(block: dict, blocks: list[dict], style_context: str) -> tuple[str, list[str], str]:
    """Formato: Diagnóstico + Conduta + Justificativa"""
    diag = block["diagnostico"]
    scenario = CLINICAL_SCENARIOS[diag]
    
    stem = (
        f"QUESTÃO X\n\n"
        f"{_patient_vignette_enamed(diag)}\n\n"
        f"Exames laboratoriais:\n{scenario['labs_completos']}\n\n"
        f"Com base nos achados clínicos e laboratoriais, o diagnóstico e a conduta adequada são, respectivamente,"
    )
    
    correct = f"{scenario['diag_correto']}; {scenario['conduta_correta']}"
    options = [correct]
    
    for dist in _pick_distractors(diag, n=3):
        options.append(f"{dist['diag']}; {dist['conduta_errada']}")
    
    random.shuffle(options)
    return stem, options, correct


def _build_format_2(block: dict, blocks: list[dict], style_context: str) -> tuple[str, list[str], str]:
    """Formato: Diagnóstico diferencial com dados incompletos"""
    diag = block["diagnostico"]
    scenario = CLINICAL_SCENARIOS[diag]
    labs = random.choice(scenario["labs_parciais"])
    
    stem = (
        f"QUESTÃO X\n\n"
        f"{_patient_vignette_enamed(diag)}\n\n"
        f"Exames iniciais: {labs}.\n\n"
        f"Para confirmação diagnóstica, o próximo exame mais indicado e o resultado esperado são, respectivamente,"
    )
    
    # Opções baseadas em exames confirmatórios
    correct_exam = _get_confirmatory_exam(diag)
    options = [correct_exam]
    
    for dist in _pick_distractors(diag, n=3):
        options.append(_get_wrong_exam(dist["diag"]))
    
    random.shuffle(options)
    return stem, options, correct_exam


def _build_format_3(block: dict, blocks: list[dict], style_context: str) -> tuple[str, list[str], str]:
    """Formato: Tratamento de primeira linha com justificativa"""
    diag = block["diagnostico"]
    scenario = CLINICAL_SCENARIOS[diag]
    
    stem = (
        f"QUESTÃO X\n\n"
        f"{_patient_vinheta_simples(diag)}\n\n"
        f"Exames laboratoriais:\n{scenario['labs_completos']}\n\n"
        f"Confirmado o diagnóstico, o tratamento de primeira linha e o parâmetro para monitorização de resposta são, respectivamente,"
    )
    
    correct = _get_treatment_response(diag)
    options = [correct]
    
    for dist in _pick_distractors(diag, n=3):
        options.append(_get_wrong_treatment(dist["diag"]))
    
    random.shuffle(options)
    return stem, options, correct


def _build_format_4(block: dict, blocks: list[dict], style_context: str) -> tuple[str, list[str], str]:
    """Formato: Identificar o exame alterado que MAIS diferencia as hipóteses"""
    diag = block["diagnostico"]
    scenario = CLINICAL_SCENARIOS[diag]
    distractors = _pick_distractors(diag, n=2)
    
    second_diag = distractors[0]["diag"] if distractors else "Anemia ferropriva"
    
    stem_templates = [
        (
            f"QUESTÃO X\n\n"
            f"{_patient_vignette_enamed(diag)}\n\n"
            f"Diante do quadro, considere como hipóteses principais {scenario['diag_correto']} e {second_diag}. "
            f"Qual exame laboratorial tem MAIOR poder discriminatório inicial e qual achado favorece a primeira hipótese?"
        ),
        (
            f"QUESTÃO X\n\n"
            f"{_patient_vignette_enamed(diag)}\n\n"
            f"Na distinção entre {scenario['diag_correto']} e {second_diag}, "
            f"qual combinação exame-resultado mais direciona o diagnóstico para a primeira opção?"
        ),
        (
            f"QUESTÃO X\n\n"
            f"{_patient_vignette_enamed(diag)}\n\n"
            f"Entre as hipóteses {scenario['diag_correto']} e {second_diag}, "
            f"qual marcador laboratorial é mais útil no pronto atendimento para favorecer a primeira hipótese?"
        ),
    ]
    stem = random.choice(stem_templates)
    
    correct = _get_differentiating_exam(diag, second_diag)
    options = [correct]
    options.extend(_get_wrong_differentiating_exams(diag, second_diag))
    
    random.shuffle(options)
    return stem, options, correct


def _build_format_5(block: dict, blocks: list[dict], style_context: str) -> tuple[str, list[str], str]:
    """Formato: Tabela laboratorial completa + conduta imediata"""
    diag = block["diagnostico"]
    scenario = CLINICAL_SCENARIOS[diag]
    
    stem = (
        f"QUESTÃO X\n\n"
        f"{_patient_vignette_enamed(diag)}\n\n"
        f"Exames laboratoriais:\n{scenario['labs_completos']}\n\n"
        f"Qual é a hipótese diagnóstica mais provável e qual complicação deve ser monitorizada nesse caso?"
    )
    
    correct = _get_diagnosis_complication(diag)
    options = [correct]
    
    for dist in _pick_distractors(diag, n=3):
        options.append(_get_wrong_diagnosis_complication(dist["diag"]))
    
    random.shuffle(options)
    return stem, options, correct


# Funções auxiliares para construir opções
def _patient_vinheta_simples(diag: str) -> str:
    """Vinheta resumida para formatos que já têm tabela."""
    vignette = _patient_vignette_enamed(diag)
    return vignette.split(". Ao exame:")[0] + "."


def _get_confirmatory_exam(diag: str) -> str:
    """Retorna exame confirmatório e resultado esperado."""
    exams = {
        "Anemia ferropriva": "ferritina sérica e índice de saturação de transferrina; ferritina < 30 ng/mL e saturação < 20%",
        "Anemia megaloblástica por deficiência de vitamina B12": "vitamina B12 sérica e ácido metilmalônico; B12 < 200 pg/mL e ácido metilmalônico elevado",
        "Anemia da doença crônica": "ferritina sérica e receptor solúvel de transferrina; ferritina > 100 ng/mL e sTfR/log ferritina < 1",
        "Anemia hemolítica autoimune": "teste de Coombs direto e haptoglobina; Coombs positivo (IgG) e haptoglobina indetectável",
        "Doença da aglutinina fria": "teste de Coombs direto e título de crioaglutininas; C3 positivo com IgG negativo e crioaglutininas elevadas",
        "Deficiência de G6PD": "dosagem de G6PD (fora da crise) e esfregaço periférico; atividade enzimática reduzida com bite cells/heinz bodies",
        "Esferocitose hereditária": "teste EMA por citometria e fragilidade osmótica; EMA reduzido com fragilidade aumentada",
        "Anemia hemolítica microangiopática (PTT)": "esfregaço periférico e atividade ADAMTS13; esquizócitos > 1% com atividade ADAMTS13 reduzida",
        "Anemia aplásica": "biópsia de medula óssea; hipocelularidade < 25% com substituição adiposa, sem fibrose ou infiltração",
    }
    return exams.get(diag, "hemograma completo; anemia")


def _get_wrong_exam(diag: str) -> str:
    """Retorna exame errado para distrator."""
    wrong_exams = {
        "Anemia ferropriva": "eletroforese de hemoglobina; padrão normal",
        "Anemia megaloblástica": "vitamina B12 sérica isolada; valor limítrofe sem confirmação funcional",
        "Anemia megaloblástica por deficiência de folato": "ácido fólico sérico; < 3 ng/mL",
        "Talassemia minor": "eletroforese de hemoglobina; HbA2 elevada (> 3,5%)",
        "Síndrome mielodisplásica": "biópsia de medula; displasia de mais de 10% em uma linhagem",
        "Anemia hemolítica": "teste de fragilidade osmótica; aumentada",
        "Esferocitose hereditária": "teste de fragilidade osmótica e EMA; fragilidade aumentada e EMA reduzido",
        "Leucemia aguda": "mielograma; > 20% de blastos",
        "Insuficiência renal crônica": "creatinina e clearance; TFG < 60 mL/min",
        "Anemia ferropriva + doença crônica (mista)": "ferritina sérica isolada; resultado em zona cinzenta (30-100 ng/mL)",
        "Anemia sideroblástica": "mielograma com coloração de Perls; sideroblastos em anel > 15%",
        "Púrpura trombocitopênica trombótica": "esfregaço com esquizócitos; > 1% de esquizócitos",
        "Hemoglobinúria paroxística noturna": "citometria de fluxo para CD55/CD59; clone PNH detectável",
    }
    return wrong_exams.get(diag, "dosagem de ferro sérico isolada; achado não conclusivo para diferenciação etiológica")


def _get_treatment_response(diag: str) -> str:
    """Retorna tratamento e parâmetro de resposta."""
    treatments = {
        "Anemia ferropriva": "sulfato ferroso 200 mg VO 3x/dia; reticulócitos em 7-10 dias e hemoglobina em 4-8 semanas",
        "Anemia megaloblástica por deficiência de vitamina B12": "cianocobalamina 1000 mcg IM diária por 7 dias; reticulócitos em 3-5 dias e melhora neurológica progressiva",
        "Anemia da doença crônica": "otimização do tratamento da doença de base; PCR e VHS para controle inflamatório",
        "Anemia hemolítica autoimune": "prednisona 1-2 mg/kg/dia; reticulócitos em 7 dias e negativação do Coombs em semanas",
        "Doença da aglutinina fria": "proteção térmica + rituximabe; melhora de hemoglobina e queda do título de crioaglutininas",
        "Deficiência de G6PD": "retirada de desencadeante + suporte clínico; estabilização da Hb e queda de LDH em dias",
        "Esferocitose hereditária": "ácido fólico e avaliação para esplenectomia; melhora de Hb e redução da hemólise crônica",
        "Anemia hemolítica microangiopática (PTT)": "plasmaférese imediata + corticoide; recuperação plaquetária e redução de LDH",
        "Anemia aplásica": "ATG + ciclosporina ou TCTH; contagem de neutrófilos e independência transfusional",
    }
    return treatments.get(diag, "tratamento específico; hemoglobina em resposta")


def _get_wrong_treatment(diag: str) -> str:
    """Retorna tratamento errado para distrator."""
    wrong = {
        "Anemia megaloblástica por deficiência de folato": "ácido fólico 5 mg/dia VO; reticulócitos em 5-7 dias",
        "Talassemia minor": "aconselhamento genético apenas; sem necessidade de tratamento farmacológico",
        "Síndrome mielodisplásica": "azacitidina 75 mg/m²/dia SC por 7 dias; hemograma em 4-6 ciclos",
        "Anemia hemolítica": "prednisona 1 mg/kg/dia; haptoglobina normalizada",
        "Esferocitose hereditária": "esplenectomia eletiva após vacinação; hemoglobina normalizada",
        "Leucemia aguda": "quimioterapia de indução 7+3; blastos < 5% na medula",
        "Anemia ferropriva": "sulfato ferroso 200 mg/dia; ferritina normalizada em 3 meses",
        "Insuficiência renal crônica": "eritropoetina 50-100 UI/kg 3x/semana; hemoglobina alvo 10-12 g/dL",
        "Anemia sideroblástica": "piridoxina 100-200 mg/dia; resposta reticulocitária em 2-3 semanas",
        "Anemia ferropriva + doença crônica (mista)": "ferro IV + tratamento da doença de base; ferritina > 100 ng/mL como alvo",
        "Púrpura trombocitopênica trombótica": "plasmaférese de urgência; normalização de plaquetas e esquizócitos",
        "Hemoglobinúria paroxística noturna": "eculizumabe 600 mg/semana; LDH normalizada",
    }
    return wrong.get(diag, f"{diag.split()[0].lower()} específica; monitorar resposta hematimétrica")


def _normalize_diag_label(diag: str) -> str:
    aliases = {
        "Púrpura trombocitopênica trombótica": "Anemia hemolítica microangiopática (PTT)",
        "Anemia megaloblástica": "Anemia megaloblástica por deficiência de vitamina B12",
        "Anemia hemolítica": "Anemia hemolítica autoimune",
    }
    return aliases.get(diag, diag)


def _differentiating_pairs() -> dict[tuple[str, str], str]:
    return {
        ("Anemia ferropriva", "Anemia da doença crônica"): "ferritina sérica e TIBC; ferritina < 30 ng/mL com TIBC elevado na ferropriva versus ferritina normal/alta com TIBC baixo na ADC",
        ("Anemia ferropriva", "Talassemia minor"): "RDW e eletroforese de hemoglobina; RDW elevado com ferritina baixa na ferropriva versus RDW normal com HbA2 > 3,5% na talassemia",
        ("Anemia ferropriva", "Anemia sideroblástica"): "ferro medular (sideroblastos em anel); ausentes na ferropriva versus presentes na sideroblástica com ferro sérico normal/alto",
        ("Anemia da doença crônica", "Anemia ferropriva"): "receptor solúvel de transferrina (sTfR); normal na ADC e elevado na ferropriva",

        ("Anemia megaloblástica por deficiência de vitamina B12", "Anemia megaloblástica por deficiência de folato"): "ácido metilmalônico e homocisteína; ambos elevados na deficiência de B12 versus apenas homocisteína elevada na de folato",
        ("Anemia megaloblástica por deficiência de vitamina B12", "Síndrome mielodisplásica"): "vitamina B12 sérica e mielograma; B12 baixa com megaloblastos na deficiência versus B12 normal com displasia trilinear na SMD",
        ("Anemia megaloblástica por deficiência de vitamina B12", "Anemia hemolítica autoimune"): "reticulócitos e B12 sérica; reticulócitos baixos com B12 baixa na megaloblástica versus reticulocitose com B12 normal na hemólise",

        ("Anemia da doença crônica", "Anemia ferropriva + doença crônica (mista)"): "receptor solúvel de transferrina (sTfR/log ferritina); < 1 na ADC pura versus > 2 na mista com ferropenia",
        ("Anemia da doença crônica", "Insuficiência renal crônica"): "creatinina e PCR; creatinina normal com PCR elevado na ADC versus creatinina > 3 mg/dL com PCR variável na DRC",

        ("Anemia hemolítica autoimune", "Esferocitose hereditária"): "teste de Coombs direto; positivo (IgG ou C3) na AHAI versus negativo na esferocitose com história familiar positiva",
        ("Anemia hemolítica autoimune", "Anemia megaloblástica por deficiência de vitamina B12"): "reticulócitos e Coombs; reticulocitose com Coombs positivo na AHAI versus reticulócitos baixos com Coombs negativo na megaloblástica",
        ("Anemia hemolítica autoimune", "Anemia hemolítica microangiopática (PTT)"): "esfregaço de sangue periférico e plaquetas; esferócitos com plaquetas preservadas na AHAI versus esquizócitos com plaquetopenia grave na PTT",
        ("Anemia hemolítica microangiopática (PTT)", "Esferocitose hereditária"): "esfregaço periférico e plaquetas; esquizócitos com plaquetopenia na PTT versus esferócitos com plaquetas normais na esferocitose",
        ("Anemia hemolítica microangiopática (PTT)", "Deficiência de G6PD"): "esfregaço periférico e Coombs; esquizócitos com Coombs negativo na PTT versus bite cells/Heinz e Coombs negativo na deficiência de G6PD",
        ("Anemia hemolítica microangiopática (PTT)", "Doença da aglutinina fria"): "Coombs direto e esfregaço; Coombs tipicamente negativo com esquizócitos na PTT versus C3 positivo com aglutinação eritrocitária na aglutinina fria",
        ("Anemia hemolítica autoimune", "Doença da aglutinina fria"): "perfil do Coombs direto; IgG positivo na AHAI quente versus C3 isolado na doença da aglutinina fria",
        ("Esferocitose hereditária", "Deficiência de G6PD"): "teste EMA e esfregaço; EMA reduzido com esferócitos na esferocitose versus EMA normal com bite cells na deficiência de G6PD",

        ("Anemia aplásica", "Leucemia aguda"): "biópsia de medula óssea; hipocelular (< 25%) sem blastos na aplasia versus hipercelular com blastos > 20% na leucemia",
        ("Anemia aplásica", "Síndrome mielodisplásica"): "celularidade medular e displasia; hipocelular sem displasia na aplasia versus normo/hipercelular com displasia trilinear na SMD",
        ("Anemia aplásica", "Hemoglobinúria paroxística noturna"): "citometria de fluxo para GPI; normal na aplasia versus deficiência de CD55/CD59 na HPN",
    }


def _get_differentiating_exam(diag1: str, diag2: str) -> str:
    """Retorna exame que diferencia os diagnósticos."""
    diag1 = _normalize_diag_label(diag1)
    diag2 = _normalize_diag_label(diag2)
    pairs = _differentiating_pairs()
    key = (diag1, diag2)
    reverse_key = (diag2, diag1)
    return pairs.get(key, pairs.get(reverse_key, "esfregaço periférico e reticulócitos; padrão de hemólise e morfologia diferencial entre etiologias"))


def _get_wrong_differentiating_exams(diag1: str, diag2: str) -> list[str]:
    """Retorna distratores plausíveis no estilo ENAMED para diferenciação."""
    diag1 = _normalize_diag_label(diag1)
    diag2 = _normalize_diag_label(diag2)

    pair_specific = {
        ("Anemia ferropriva", "Anemia da doença crônica"): [
            "ferritina sérica e TIBC; ferritina > 100 ng/mL e TIBC baixo na ferropriva versus ferritina < 30 ng/mL e TIBC elevado na ADC",
            "saturação de transferrina; > 45% na ferropriva versus < 20% na ADC",
            "receptor solúvel de transferrina; reduzido na ferropriva e elevado na ADC",
        ],
        ("Anemia ferropriva", "Talassemia minor"): [
            "eletroforese de hemoglobina; HbA2 < 2% na talassemia minor e > 3,5% na ferropriva",
            "RDW; normal na ferropriva e aumentado na talassemia minor",
            "ferritina sérica; elevada na ferropriva e reduzida na talassemia minor",
        ],
        ("Anemia ferropriva", "Anemia sideroblástica"): [
            "ferritina sérica; elevada na ferropriva e reduzida na sideroblástica",
            "saturação de transferrina; alta na ferropriva e baixa na sideroblástica",
            "receptor solúvel de transferrina; reduzido na ferropriva e elevado na sideroblástica",
        ],
        ("Anemia megaloblástica por deficiência de vitamina B12", "Anemia megaloblástica por deficiência de folato"): [
            "ácido metilmalônico; normal na deficiência de B12 e elevado na deficiência de folato",
            "vitamina B12 sérica; elevada na deficiência de B12 e baixa na de folato",
            "homocisteína; normal na deficiência de B12 e elevada apenas na deficiência de folato",
        ],
        ("Anemia megaloblástica por deficiência de vitamina B12", "Síndrome mielodisplásica"): [
            "mielograma; ausência de displasia trilinear na SMD e presença de displasia acentuada na deficiência de B12",
            "vitamina B12 sérica; baixa na SMD e normal na deficiência de B12",
            "citogenética medular; tipicamente normal na SMD e alterada na deficiência de B12",
        ],
        ("Anemia megaloblástica por deficiência de vitamina B12", "Anemia hemolítica"): [
            "reticulócitos; elevados na deficiência de B12 e baixos na anemia hemolítica",
            "Coombs direto; positivo na deficiência de B12 e negativo na anemia hemolítica autoimune",
            "ácido metilmalônico; reduzido na deficiência de B12 e elevado na anemia hemolítica",
        ],
        ("Anemia da doença crônica", "Anemia ferropriva + doença crônica (mista)"): [
            "índice sTfR/log ferritina; < 1 na anemia mista e > 2 na ADC pura",
            "ferritina sérica; < 30 ng/mL na ADC pura e > 200 ng/mL na mista",
            "sTfR; reduzido na anemia mista e elevado na ADC pura",
        ],
        ("Anemia da doença crônica", "Insuficiência renal crônica"): [
            "creatinina sérica; normal na DRC avançada e elevada na ADC",
            "eritropoetina sérica; elevada na DRC e reduzida na ADC",
            "PCR; invariavelmente baixa na ADC e elevada na DRC",
        ],
        ("Anemia hemolítica autoimune", "Esferocitose hereditária"): [
            "teste de Coombs direto; negativo na AHAI e positivo na esferocitose hereditária",
            "teste EMA; reduzido na AHAI e normal na esferocitose hereditária",
            "fragilidade osmótica; normal na esferocitose e aumentada apenas na AHAI",
        ],
        ("Anemia hemolítica autoimune", "Anemia megaloblástica por deficiência de vitamina B12"): [
            "reticulócitos e Coombs; reticulócitos baixos com Coombs positivo na AHAI versus reticulocitose com Coombs negativo na megaloblástica",
            "vitamina B12 sérica; normal na megaloblástica e baixa na AHAI",
            "ácido metilmalônico; normal na megaloblástica e elevado na AHAI",
        ],
        ("Anemia hemolítica autoimune", "Anemia hemolítica microangiopática (PTT)"): [
            "esfregaço periférico; esquizócitos predominantes na AHAI e esferócitos na PTT",
            "plaquetas; normais na PTT e plaquetopenia grave na AHAI",
            "Coombs direto; positivo na PTT e tipicamente negativo na AHAI",
        ],
        ("Anemia hemolítica microangiopática (PTT)", "Esferocitose hereditária"): [
            "teste EMA; reduzido na PTT e normal na esferocitose hereditária",
            "fragilidade osmótica; francamente aumentada na PTT e tipicamente normal na esferocitose",
            "Coombs direto; fortemente positivo na PTT e negativo na esferocitose",
        ],
        ("Anemia hemolítica microangiopática (PTT)", "Deficiência de G6PD"): [
            "dosagem de G6PD na crise; sempre reduzida na PTT e normal na deficiência de G6PD",
            "Coombs direto; IgG positivo na PTT e C3 isolado na deficiência de G6PD",
            "plaquetas; elevadas na PTT e normais na deficiência de G6PD",
        ],
        ("Anemia hemolítica microangiopática (PTT)", "Doença da aglutinina fria"): [
            "crioaglutininas; título muito elevado na PTT e baixo/ausente na aglutinina fria",
            "Coombs direto; IgG positivo na PTT e negativo na aglutinina fria",
            "esfregaço; esferócitos predominantes na PTT e esquizócitos na aglutinina fria",
        ],
        ("Anemia hemolítica autoimune", "Doença da aglutinina fria"): [
            "perfil do Coombs direto; C3 isolado na AHAI quente e IgG positivo na aglutinina fria",
            "esfregaço; esquizócitos predominantes na AHAI e aglutinação sem hemólise na doença da aglutinina fria",
            "resposta ao frio; ausência de piora na aglutinina fria com piora marcante na AHAI quente",
        ],
        ("Esferocitose hereditária", "Deficiência de G6PD"): [
            "teste de Coombs direto; positivo na esferocitose hereditária e negativo na deficiência de G6PD",
            "CHCM; invariavelmente baixo na esferocitose e alto na deficiência de G6PD",
            "história familiar; ausente na esferocitose e obrigatoriamente presente na deficiência de G6PD",
        ],
        ("Anemia aplásica", "Leucemia aguda"): [
            "biópsia de medula óssea; hipercelular com blastos > 20% na aplasia e hipocelular sem blastos na leucemia aguda",
            "mielograma; ausência de blastos na leucemia aguda e blastose na aplasia",
            "imunofenotipagem; sem clonalidade em leucemia aguda e clonalidade mieloide na aplasia",
        ],
        ("Anemia aplásica", "Síndrome mielodisplásica"): [
            "citogenética; alterações clonais típicas na aplasia e cariótipo normal na SMD",
            "medula óssea; hipercelular na aplasia e hipocelular na SMD hipoplásica",
            "displasia morfológica; ausente na SMD e presente na aplasia",
        ],
        ("Anemia aplásica", "Hemoglobinúria paroxística noturna"): [
            "citometria de fluxo CD55/CD59; deficiência ausente na HPN e presente na aplasia",
            "LDH; persistentemente normal na HPN e elevado na aplasia",
            "reticulócitos; acentuadamente elevados na aplasia e baixos na HPN",
        ],
    }

    key = (diag1, diag2)
    reverse_key = (diag2, diag1)
    options = pair_specific.get(key, pair_specific.get(reverse_key, []))

    if not options:
        all_correct_candidates = list(set(_differentiating_pairs().values()))
        correct_current = _get_differentiating_exam(diag1, diag2)
        options = [candidate for candidate in all_correct_candidates if candidate != correct_current]

    random.shuffle(options)
    return options[:3]


def _get_diagnosis_complication(diag: str) -> str:
    """Retorna diagnóstico e complicação a monitorar."""
    complications = {
        "Anemia ferropriva": "Anemia ferropriva; descompensação cardiovascular em Hb < 7 g/dL ou sangramento oculto persistente",
        "Anemia megaloblástica por deficiência de vitamina B12": "Anemia megaloblástica por B12; degeneração combinada subaguda da medula espinhal se atraso terapêutico",
        "Anemia da doença crônica": "Anemia da inflamação; progressão da doença de base e refratariedade à eritropoetina",
        "Anemia hemolítica autoimune": "Anemia hemolítica autoimune; crise hemolítica aguda com insuficiência renal por hemoglobinúria",
        "Doença da aglutinina fria": "Doença da aglutinina fria; crise hemolítica em exposição ao frio e acrocianose recorrente",
        "Deficiência de G6PD": "Deficiência de G6PD; novas crises hemolíticas após gatilhos oxidantes",
        "Esferocitose hereditária": "Esferocitose hereditária; colelitíase pigmentar e crise aplásica por parvovírus",
        "Anemia hemolítica microangiopática (PTT)": "PTT; isquemia de órgão-alvo com risco neurológico e renal agudo",
        "Anemia aplásica": "Anemia aplásica grave; sepse por neutropenia profunda e sangramento por plaquetopenia < 10.000",
    }
    return complications.get(diag, "anemia; complicações gerais")


def _get_wrong_diagnosis_complication(diag: str) -> str:
    """Retorna diagnóstico errado com complicação."""
    wrong = {
        "Anemia megaloblástica por deficiência de folato": "Anemia por folato; defeitos do tubo neural se gestante",
        "Talassemia minor": "Talassemia minor; geralmente assintomática, sem complicações graves",
        "Síndrome mielodisplásica": "Síndrome mielodisplásica; transformação leucêmica em 30% dos casos",
        "Anemia hemolítica": "Anemia hemolítica intravascular; insuficiência renal aguda por hemoglobinúria",
        "Esferocitose hereditária": "Esferocitose; crise aplásica por parvovírus B19",
        "Leucemia aguda": "Leucemia aguda; síndrome de lise tumoral após quimioterapia",
        "Anemia ferropriva": "Ferropenia grave; comprometimento neurocognitivo e síndrome de Plummer-Vinson",
        "Insuficiência renal crônica": "Doença renal com anemia; sobrecarga de ferro por transfusões frequentes",
        "Anemia sideroblástica": "Anemia sideroblástica; sobrecarga de ferro tecidual",
        "Anemia ferropriva + doença crônica (mista)": "Anemia mista; refratariedade a ferro oral isolado",
        "Púrpura trombocitopênica trombótica": "PTT; microangiopatia trombótica com lesão renal e neurológica",
        "Hemoglobinúria paroxística noturna": "HPN; tromboses venosas em sítios atípicos",
    }
    return wrong.get(diag, f"{diag}; complicação específica da condição")


BUILDERS = {
    "1": _build_format_1,
    "2": _build_format_2,
    "3": _build_format_3,
    "4": _build_format_4,
    "5": _build_format_5,
}


def _generate_template_question_internal(
    tema: str,
    style_context: str = "",
    explanation_context: str = "",
    forced_format_code: str | None = None,
    forced_objective: str | None = None,
    forced_case_variant_index: int | None = None,
    forced_diagnostico: str | None = None,
) -> Question:
    blocks = load_blocks()
    filtered = blocks if tema == "Todos" else [item for item in blocks if item["tema"] == tema]
    if tema == "Hemolítica":
        filtered = HEMOLYTIC_SUBTYPE_BLOCKS

    if forced_diagnostico:
        forced_candidates = [item for item in filtered if item.get("diagnostico") == forced_diagnostico]
        selected = random.choice(forced_candidates) if forced_candidates else random.choice(filtered)
    else:
        selected = random.choice(filtered)

    format_code = forced_format_code if forced_format_code in BUILDERS else random.choice(FORMAT_WEIGHTS)
    objective_candidates = FORMAT_OBJECTIVE_MAP.get(format_code, QUESTION_OBJECTIVES)
    objective = forced_objective if forced_objective in QUESTION_OBJECTIVES else random.choice(objective_candidates)
    diag = selected["diagnostico"]
    _FORCED_CASE_VARIANT_BY_DIAG[diag] = forced_case_variant_index
    try:
        prompt, options, correct = BUILDERS[format_code](selected, filtered, style_context)
    finally:
        _FORCED_CASE_VARIANT_BY_DIAG[diag] = None

    formatted_options = _format_alternatives(options)
    correct_tagged = formatted_options[options.index(correct)]
    
    # Identifica alternativas erradas para a explicação
    wrong_options = [opt for opt in formatted_options if opt != correct_tagged]
    
    explanation = _build_question_specific_explanation(
        selected, format_code, correct_tagged, wrong_options
    )

    return Question(
        tema=selected["tema"],
        dificuldade=FORMAT_DIFFICULTY[format_code],
        tipo=FORMAT_LABELS[format_code],
        objetivo=objective,
        pergunta=prompt,
        alternativas=formatted_options,
        resposta_correta=correct_tagged,
        explicacao=explanation,
        fonte=selected["fonte"],
    )


def generate_template_question(
    tema: str,
    style_context: str = "",
    explanation_context: str = "",
) -> Question:
    return _generate_template_question_internal(
        tema,
        style_context=style_context,
        explanation_context=explanation_context,
    )


def _clean_option_prefix(text: str) -> str:
    return re.sub(r"^\([A-D]\)\s*", "", text.strip())


def _extract_differential_pair(question_text: str) -> str:
    pattern = r"diagnósticos diferenciais são\s+(.+?)\s+e\s+(.+?)\."
    match = re.search(pattern, question_text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    first = " ".join(match.group(1).split())
    second = " ".join(match.group(2).split())
    return f"{first}|{second}"


def _extract_clinical_axis(text: str) -> str:
    normalized = text.lower()
    axis_groups = {
        "ferro_ferritina": ["ferritina", "transferrina", "tibc", "ferro sérico", "stfr"],
        "megaloblastica_b12": ["vitamina b12", "ácido metilmalônico", "homocisteína", "megaloblast"],
        "hemolise": ["coombs", "haptoglobina", "esferócito", "esquizócito", "ldh", "bilirrubina"],
        "medula_aplasia": ["biópsia de medula", "mielograma", "hipocelular", "blastos", "cd55", "cd59"],
        "tratamento": ["prednisona", "cianocobalamina", "sulfato ferroso", "atg", "ciclosporina", "tcth"],
        "inflamacao": ["pcr", "vhs", "hepcidina", "doença de base", "eritropoetina"],
    }
    found = [group for group, words in axis_groups.items() if any(word in normalized for word in words)]
    return "|".join(sorted(found)) if found else "axis_geral"


def _extract_case_context(stem: str) -> str:
    normalized = stem.lower()
    context_groups = {
        "menorragia": ["menorrag", "sangramento uterino", "ciclos menstruais intensos"],
        "bariatrica": ["bariátrica", "gastrectomia", "pós-gastrectomia"],
        "gestacao": ["gestante", "trimestre", "puerp"],
        "artrite_reumatoide": ["artrite reumatoide", "sinovite"],
        "lupus": ["lúpus", "les"],
        "tuberculose": ["tuberculose", "tb pulmonar"],
        "osteomielite": ["osteomielite"],
        "neoplasia_colorretal": ["colorretal", "quimioterapia"],
        "vegetariano_estrito": ["vegetariano", "vegano", "dieta restritiva"],
        "gastrite_autoimune": ["gastrite atrófica", "anemia perniciosa", "fator intrínseco"],
        "doenca_ileal": ["crohn", "ileal", "ressecção ileal"],
        "farmacos_b12": ["metformina", "ibp", "inibidor de bomba"],
        "aglutinina_fria": ["acrocianose", "frio", "crioaglutininas", "c3 positivo"],
        "g6pd": ["g6pd", "bite cells", "heinz", "favas", "oxidante"],
        "esferocitose": ["ema", "fragilidade osmótica", "esferocitose", "história familiar"],
        "microangiopatica_ptt": ["esquizócitos", "adamts13", "petéquias", "plaquetopenia", "ptt"],
        "inflamatoria_autoimune": ["artrite reumatoide", "lúpus", "doença autoimune"],
        "infeccao_cronica": ["tuberculose", "osteomielite", "infecção crônica", "hepatite viral"],
        "neoplasia": ["neoplasia", "linfoma", "quimioterapia"],
        "pos_viral": ["quadro gripal", "infecção viral recente", "pós-viral"],
        "exposicao_toxica": ["benzeno", "cloranfenicol", "exposição ocupacional"],
        "neurologico": ["parestesias", "romberg", "ataxia", "déficit sensitivo"],
    }
    found = [group for group, words in context_groups.items() if any(word in normalized for word in words)]
    return "|".join(sorted(found)) if found else "contexto_geral"


def _semantic_signature(question: Question) -> str:
    stem = " ".join(question.pergunta.split())
    answer = _clean_option_prefix(question.resposta_correta)
    differential_pair = _extract_differential_pair(stem)
    axis = _extract_clinical_axis(f"{stem} {answer}")
    case_context = _extract_case_context(stem)
    return f"{question.tema}::{question.tipo}::{question.objetivo}::{differential_pair}::{axis}::{case_context}"


def _generate_theme_pool(
    tema: str,
    style_context: str,
    explanation_context: str,
    target_count: int,
    hemolitica_profile: str = "standard",
) -> list[Question]:
    pool: list[Question] = []
    seen_text_keys: set[str] = set()
    seen_semantic_keys: set[str] = set()

    # 25 questões = grade balanceada por formato/variante
    format_cycle = ["1", "2", "3", "4", "5"]
    if tema == "Hemolítica" and hemolitica_profile == "advanced":
        format_cycle = ["1", "2", "3", "5", "5"]

    theme_to_diag = {
        "Ferropriva": "Anemia ferropriva",
        "Megaloblástica": "Anemia megaloblástica por deficiência de vitamina B12",
        "Doença crônica": "Anemia da doença crônica",
        "Aplásica": "Anemia aplásica",
        "Hemolítica": "Anemia hemolítica autoimune",
    }
    main_diag = theme_to_diag.get(tema, "")
    variant_count = max(1, len(CLINICAL_CASE_VARIANTS.get(main_diag, [])))
    variant_cycle = list(range(variant_count))

    planned_pairs = [(fmt, var) for var in variant_cycle for fmt in format_cycle]
    while len(planned_pairs) < target_count:
        planned_pairs.extend(planned_pairs)
    planned_pairs = planned_pairs[:target_count]
    random.shuffle(planned_pairs)

    # Balanceia objetivos pedagógicos ao longo das 25 questões
    objective_pool = QUESTION_OBJECTIVES
    if tema == "Hemolítica" and hemolitica_profile == "advanced":
        objective_pool = [
            "Manejo",
            "Tratamento farmacológico",
            "Padrão laboratorial",
            "Fisiopatologia",
            "Etiologia",
            "Manejo",
            "Tratamento não farmacológico",
        ]

    objective_cycle = (objective_pool * ((target_count // len(objective_pool)) + 1))[:target_count]
    random.shuffle(objective_cycle)

    # Planejamento ponderado de subtipos para Hemolítica avançada
    diag_plan: list[str | None] = [None] * target_count
    if tema == "Hemolítica" and hemolitica_profile == "advanced":
        weighted_diags: list[str] = []
        for diag_name, weight in HEMOLYTIC_ADVANCED_DIAG_WEIGHTS.items():
            weighted_diags.extend([diag_name] * max(1, weight))
        while len(weighted_diags) < target_count:
            weighted_diags.extend(weighted_diags)
        random.shuffle(weighted_diags)
        diag_plan = weighted_diags[:target_count]

    max_attempts = max(target_count * 80, 400)
    attempts = 0
    next_idx = 0

    while len(pool) < target_count and attempts < max_attempts:
        forced_format, forced_variant = planned_pairs[next_idx % len(planned_pairs)]
        forced_objective = objective_cycle[next_idx % len(objective_cycle)]
        forced_diag = diag_plan[next_idx % len(diag_plan)]
        question = _generate_template_question_internal(
            tema,
            style_context=style_context,
            explanation_context=explanation_context,
            forced_format_code=forced_format,
            forced_objective=forced_objective,
            forced_case_variant_index=forced_variant,
            forced_diagnostico=forced_diag,
        )

        text_key = f"{question.tema}|{question.tipo}|{question.pergunta}|{question.resposta_correta}"
        semantic_key = _semantic_signature(question)
        if text_key not in seen_text_keys and semantic_key not in seen_semantic_keys:
            seen_text_keys.add(text_key)
            seen_semantic_keys.add(semantic_key)
            pool.append(question)
            next_idx += 1

        attempts += 1

    # Fallback 1: relaxa semântica, mantém texto único
    while len(pool) < target_count:
        question = _generate_template_question_internal(
            tema,
            style_context=style_context,
            explanation_context=explanation_context,
        )
        text_key = f"{question.tema}|{question.tipo}|{question.pergunta}|{question.resposta_correta}"
        if text_key not in seen_text_keys:
            seen_text_keys.add(text_key)
            pool.append(question)

        if len(seen_text_keys) > target_count * 40:
            break

    # Fallback 2: completa caso ainda falte
    while len(pool) < target_count:
        question = _generate_template_question_internal(
            tema,
            style_context=style_context,
            explanation_context=explanation_context,
        )
        pool.append(question)

    random.shuffle(pool)
    return pool


def generate_question_pool(
    tema: str,
    style_context: str = "",
    explanation_context: str = "",
    count_per_theme: int = QUESTIONS_PER_THEME,
    hemolitica_profile: str = "standard",
) -> list[Question]:
    """Gera pool de questões: 25 por tema (ou 125 em 'Todos')."""
    blocks = load_blocks()

    if tema != "Todos":
        return _generate_theme_pool(
            tema=tema,
            style_context=style_context,
            explanation_context=explanation_context,
            target_count=count_per_theme,
            hemolitica_profile=hemolitica_profile,
        )

    all_themes = [theme for theme in SUPPORTED_THEMES if theme in {item["tema"] for item in blocks}]
    full_pool: list[Question] = []

    for current_theme in all_themes:
        full_pool.extend(
            _generate_theme_pool(
                tema=current_theme,
                style_context=style_context,
                explanation_context=explanation_context,
                target_count=count_per_theme,
                hemolitica_profile=hemolitica_profile,
            )
        )

    random.shuffle(full_pool)
    return full_pool


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
