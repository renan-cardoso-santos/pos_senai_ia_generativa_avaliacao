"""Dados de exemplo (fictícios) para demonstração da tela Nova análise.

Permitem que o avaliador teste a solução ponta a ponta **sem** usar um currículo
pessoal: um clique pré-preenche o CV padronizado com um modelo completo e válido
(pronto para salvar), e o mesmo conteúdo gera o arquivo-modelo `.docx` usado para
demonstrar o caminho de upload/extração.

Todos os dados são fictícios (LGPD).
"""
from __future__ import annotations

from agents.modelos import (
    CurriculoEstruturado,
    DadosPessoais,
    ExperienciaItem,
    FormacaoItem,
)

# Credenciais da conta de demonstração (usadas no seed e pré-preenchidas no login).
DEMO_EMAIL = "demo@recrutame.dev"
DEMO_SENHA = "demo1234"


def cv_exemplo() -> CurriculoEstruturado:
    """CV padronizado de exemplo — completo e válido (passa no gate)."""
    return CurriculoEstruturado(
        dados_pessoais=DadosPessoais(
            nome="Joana Exemplo da Silva",
            email="joana.exemplo@email.com",
            telefone="(11) 98888-0000",
            localizacao="São Paulo, SP",
            linkedin="linkedin.com/in/joana-exemplo",
        ),
        resumo=(
            "Cientista de dados com 5+ anos transformando dados em decisão. "
            "Experiência em modelos de machine learning em produção, automação de "
            "pipelines e comunicação com áreas de negócio. Foco em Python, SQL e "
            "impacto mensurável."
        ),
        experiencias=[
            ExperienciaItem(
                cargo="Cientista de Dados Sênior",
                empresa="TechData",
                periodo="2021 - Atual",
                descricao=(
                    "Liderou modelos de ML em produção; reduziu em 30% o churn de "
                    "clientes e automatizou pipelines de ETL em Python/SQL."
                ),
            ),
            ExperienciaItem(
                cargo="Analista de Dados",
                empresa="Varejo S.A.",
                periodo="2018 - 2021",
                descricao="Construiu dashboards em Power BI para 5 áreas de negócio.",
            ),
        ],
        formacao=[
            FormacaoItem(
                curso="Bacharelado em Estatística",
                instituicao="Universidade de São Paulo (USP)",
                periodo="2013 - 2017",
            ),
        ],
        skills=["Python", "SQL", "Pandas", "scikit-learn", "Power BI", "Git"],
        idiomas=["Inglês — avançado", "Espanhol — intermediário"],
        certificacoes=["AWS Certified Machine Learning — Specialty"],
    )


def vaga_exemplo() -> dict[str, str]:
    """Vaga de exemplo (real, pública) para demonstrar a análise CV × vaga.

    Pré-preenche os campos da tela Nova análise com um processo seletivo do SENAI/
    FIESC, permitindo testar a solução ponta a ponta sem colar uma vaga manualmente.
    """
    return {
        "empresa": "FIESC",
        "cargo": "Analista em Pesquisa de Desenvolvimento Tecnológico e Inovação – Pleno",
        "descricao": (
            "01747/2026 - SERVIÇO NACIONAL DE APRENDIZAGEM INDUSTRIAL - Instituto SENAI "
            "de Inovação em Sistemas Embarcados\n\n"
            "Antes de realizar sua inscrição, leia com atenção as informações disponíveis "
            "no Comunicado de Processo Seletivo.\n\n"
            "ATENÇÃO: Informamos que apenas as informações preenchidas diretamente no "
            "cadastro do currículo do candidato serão consideradas para a etapa de "
            "Avaliação Curricular. Currículos anexos ao formulário de inscrição não serão "
            "considerados. Pedimos que preencha seus dados com atenção, pois o sistema não "
            "permite a edição do currículo após a finalização da inscrição.\n\n"
            "Cargo: Analista em Pesquisa de Desenvolvimento Tecnológico e Inovação – Pleno\n\n"
            "E qual será a sua missão no time?\n\n"
            "A atuação do profissional envolve o desenvolvimento de soluções inovadoras "
            "baseadas em dados, modelos preditivos, aprendizado de máquina e sistemas "
            "inteligentes para resolver problemas complexos e gerar valor estratégico para "
            "a organização.\n\n"
            "Esse profissional atua desde a pesquisa e experimentação até a implementação "
            "de soluções em produção, integrando conhecimentos de IA, engenharia de "
            "software, infraestrutura e análise de dados. Entre os principais desafios "
            "estão a incerteza dos projetos de pesquisa, a baixa qualidade ou ausência de "
            "dados estruturados, a necessidade de criar soluções escaláveis e robustas, "
            "além da rápida evolução tecnológica da área, que exige aprendizado contínuo, "
            "capacidade de adaptação e forte interação multidisciplinar com especialistas, "
            "pesquisadores e áreas de negócio.\n\n"
            "Requisitos mínimos:\n"
            "- Ensino Superior completo;\n"
            "- 06 meses de experiência em projetos ou pesquisas na área de IA;\n"
            "- CNH válida, disponibilidade para deslocamento.\n\n"
            "Requisito desejável:\n"
            "- Conhecimento em LLM e deploy em nuvem.\n\n"
            "+Informações:\n"
            "- Salário: R$6463,94\n"
            "- Carga horária: 200 horas/mês\n"
            "- Horário de trabalho: matutino e vespertino, das 08:00 às 12:00 e das 13:00 "
            "às 17:00, de segunda à sexta-feira.\n"
            "- Número de vagas: 1\n"
            "- Local de atuação: Florianópolis/SC\n"
            "- Tipo de contrato: Mensalista\n"
            "- Prazo do contrato: Prazo indeterminado\n\n"
            "A nota final (NF) do candidato será obtida mediante média ponderada, "
            "aplicando-se a seguinte fórmula: NF = ((TFC+(AP*2))/3)"
        ),
    }


def texto_cv_exemplo() -> str:
    """Texto de um CV realista (fictício) no **modelo padrão** — arquivo de upload.

    Segue o mesmo layout que a tool `estruturar_cv` reconhece: contato no topo,
    localização "Cidade, UF", seções (OBJETIVO/RESUMO, FORMAÇÃO, CERTIFICAÇÕES,
    COMPETÊNCIAS, IDIOMA, EXPERIÊNCIA), formação em uma linha por curso com `•`
    (`Curso, Instituição (período)`) e cada vaga aberta por `➢` com empresa, cargo
    e período em linhas separadas. Assim o upload deste modelo pré-preenche todos
    os campos sem pendências. Dados 100% fictícios (LGPD).
    """
    return (
        "Joana Exemplo da Silva\n"
        "São Paulo, SP\n"
        "(11) 98888-0000\n"
        "Email: joana.exemplo@email.com\n"
        "LinkedIn: https://www.linkedin.com/in/joana-exemplo/\n\n"
        "OBJETIVO\n"
        "Cientista de Dados Pleno | Machine Learning, Analytics e Engenharia de Dados\n\n"
        "RESUMO PROFISSIONAL\n"
        "Cientista de dados com 5+ anos transformando dados em decisão. Experiência "
        "em modelos de machine learning em produção, automação de pipelines e "
        "comunicação com áreas de negócio. Foco em Python, SQL e impacto mensurável.\n\n"
        "FORMAÇÃO ACADÊMICA\n"
        "• Bacharelado em Estatística, Universidade de São Paulo (USP), São Paulo (2013 — 2017)\n\n"
        "CERTIFICAÇÕES\n"
        "• AWS Certified Machine Learning — Specialty, Amazon Web Services – 2022\n\n"
        "COMPETÊNCIAS TÉCNICAS (STACK)\n"
        "• Linguagens: Python, SQL\n"
        "• Bibliotecas: Pandas, scikit-learn\n"
        "• Visualização & BI: Power BI, Git\n\n"
        "IDIOMA\n"
        "• Inglês — avançado\n"
        "• Espanhol — intermediário\n\n"
        "EXPERIÊNCIA PROFISSIONAL\n"
        "➢ TechData | Tecnologia\n"
        "Cientista de Dados Sênior\n"
        "2021 – atual\n"
        "o Liderou modelos de ML em produção; reduziu em 30% o churn de clientes.\n"
        "o Automatizou pipelines de ETL em Python/SQL.\n"
        "➢ Varejo S.A. | Varejo\n"
        "Analista de Dados\n"
        "2018 – 2021\n"
        "o Construiu dashboards em Power BI para 5 áreas de negócio.\n"
    )
