# HematoQuest — Blueprint MVP (hoje)

## Objetivo
Aplicativo simples para gerar e praticar questões sobre anemias, com explicações didáticas e referência de estudo.

## Público
Estudantes e colegas de medicina.

## Escopo MVP
1. Gerar 1 questão por vez.
2. Tipos: formatos clínicos e objetivos padronizados (abaixo).
3. Dificuldade: fácil, média, difícil.
4. Correção automática com explicação.
5. Histórico local de tentativas.

## Conteúdo inicial
- Ferropriva
- Megaloblástica (B12/folato)
- Doença crônica
- Hemolítica
- Aplásica

## Regras de qualidade
- Questões devem ter apenas 1 alternativa correta.
- Explicação curta (3–6 linhas) com racional clínico.
- Sempre registrar fonte/resumo do bloco de conhecimento usado.
- Linguagem objetiva, sem ambiguidade e sem pegadinhas.
- Sempre que aplicável, citar contexto de atenção à saúde (APS/AE/terciária) e conduta inicial segura.

## Blueprint oficial dos formatos de questões

### Campos comuns (todos os formatos)
- `id_questao`
- `formato`
- `tema`
- `subtema`
- `dificuldade` (fácil/média/difícil)
- `enunciado` (texto completo)
- `alternativas` (A, B, C, D)
- `gabarito` (apenas uma correta)
- `explicacao` (3–6 linhas)
- `fonte` (livro/artigo/resumo)

### Formato 1 — Vinheta + Diagnóstico + Conduta
```text
QUESTÃO X

Paciente de __ anos, sexo __, procura [serviço] com queixa de ___ há ___ tempo.
Relata ___.
Nega ___.

Ao exame físico:
- Sinais vitais: ___
- Achados específicos: ___

Exames laboratoriais:
- ___
- ___
- ___

Considerando o quadro apresentado, a conduta mais adequada é

(A) ___
(B) ___
(C) ___
(D) ___
```

### Formato 2 — Diagnóstico + Tratamento (dupla associação)
```text
QUESTÃO X

Paciente de __ anos apresenta ___ há ___ tempo.
Refere ___.
Ao exame físico: ___.

Exames mostram:
- ___
- ___

A hipótese diagnóstica e o tratamento de primeira linha são, respectivamente,

(A) Diagnóstico A; Tratamento A
(B) Diagnóstico B; Tratamento B
(C) Diagnóstico C; Tratamento C
(D) Diagnóstico D; Tratamento D
```

### Formato 3 — Caso curto + Classificação
```text
QUESTÃO X

Paciente de __ anos apresenta ___.
Exame físico revela ___.
Exames complementares mostram ___.

Com base nos achados, o quadro é classificado como

(A) ___
(B) ___
(C) ___
(D) ___
```

### Formato 4 — Caso clínico + Nível de Atenção / SUS
```text
QUESTÃO X

Paciente acompanhado na [atenção primária/secundária] apresenta ___.
É encaminhado para ___.

Ao ser assistido pelo especialista, estará em qual nível de atenção e receberá que tipo de prevenção, respectivamente?

(A) ___
(B) ___
(C) ___
(D) ___
```

### Formato 5 — Interpretação de Exames (laboratório pesado)
```text
QUESTÃO X

Paciente de __ anos apresenta ___.
Exame físico: ___.

Resultados laboratoriais:

Exame     Resultado     Valor de referência
___       ___           ___
___       ___           ___
___       ___           ___

O diagnóstico e a conduta inicial indicada são, respectivamente,

(A) ___
(B) ___
(C) ___
(D) ___
```

### Formato 7 — Situação-problema ética / legal
```text
QUESTÃO X

Profissional de saúde atende paciente que ___.
Diante da situação descrita, a conduta adequada é

(A) ___
(B) ___
(C) ___
(D) ___
```

### Formato 8 — Rastreamento / Medicina Preventiva
```text
QUESTÃO X

Paciente de __ anos comparece à consulta para revisão de saúde.
Apresenta os seguintes antecedentes: ___.

Considerando as recomendações de rastreamento, o médico deve

(A) ___
(B) ___
(C) ___
(D) ___
```

### Formato 9 — Conduta expectante vs intervenção
```text
QUESTÃO X

Paciente apresenta ___.
Exame físico: ___.
Sem sinais de gravidade.

Qual é o próximo passo mais adequado?

(A) Exame avançado
(B) Internação
(C) Tratamento imediato
(D) Conduta expectante com reavaliação
```

### Formato 10 — Questão epidemiológica
```text
QUESTÃO X

Em uma população com prevalência de ___, foi aplicado um teste com sensibilidade de ___ e especificidade de ___.

Nesse contexto, é correto afirmar que

(A) ___
(B) ___
(C) ___
(D) ___
```

Uso típico:
- Falsos positivos
- Valor preditivo
- Triagem vs confirmação

## Critérios de construção de alternativas
- 1 alternativa correta e 3 distratores plausíveis.
- Distratores devem ser clinicamente possíveis, mas incorretos no detalhe-chave.
- Evitar alternativas com absolutos como “sempre” e “nunca”, exceto quando diretriz realmente exigir.

## Metadados extras recomendados
- `competencia_cobrada` (diagnóstico, conduta, prevenção, ética, epidemiologia)
- `tags` (microcitose, macrocitose, hemólise, pancitopenia, etc.)
- `tempo_estimado_segundos`
- `justificativa_distratores`

## Arquitetura simples
- Frontend + backend no mesmo app: Streamlit.
- Banco local: SQLite.
- Conteúdo base: JSON local (editable).
- Geração:
  - Modo `template` (offline): não depende de API.
  - Modo `llm` (opcional): usa OPENAI_API_KEY.

## Entregáveis de hoje
- App funcional rodando localmente.
- Banco inicial populado.
- Guia rápido para adicionar novos conteúdos e novos formatos.
- Passo a passo para compartilhar com colegas.
