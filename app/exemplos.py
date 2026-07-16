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

    Pré-preenche os campos da tela Nova análise com um processo seletivo do SENAI-SC
    (Bolsista em IA/Geointeligência/New Space), permitindo testar a solução ponta a
    ponta sem colar uma vaga manualmente. É uma vaga rica em requisitos técnicos —
    exercita bem a extração de must-haves/gaps da análise.
    """
    return {
        "empresa": "SENAI-SC",
        "cargo": (
            "Bolsista de negócios, Pesquisa e Desenvolvimento e Inovação Aplicada em "
            "IA, Geointeligência e New Space"
        ),
        "link": (
            "https://ielsc.enlizt.me/vagas/senai_-_bolsista_de_negocios-_pesquisa_e_"
            "desenvolvimento_e_inovacao_aplicada_em_ia-_geointeligencia_e_new_space-100726"
        ),
        "descricao": (
            "Estamos em busca de um Engenheiro de IA sênior para atuar alocado nas "
            "áreas de negócio do nosso cliente, desenvolvendo soluções pontuais de IA "
            "sob demanda, com o apoio do time interno de dados. O profissional será "
            "responsável por transformar necessidades das áreas em agentes inteligentes "
            "funcionais, desde a concepção até a entrega. Atuará como ponte entre as "
            "áreas de negócio e o time de dados, sendo responsável por entender os "
            "problemas de cada área, propor soluções baseadas em IA e executá-las de "
            "ponta a ponta.\n\n"
            "Responsabilidades\n"
            "- Desenvolver agentes autônomos utilizando frameworks como Agno, "
            "combinando múltiplas ferramentas em fluxos inteligentes.\n"
            "- Criar agentes conversacionais com memória de curto e longo prazo, com "
            "rastreabilidade e personalização.\n"
            "- Experimentar e integrar diferentes LLMs (OpenAI, Gemini, DeepSeek, entre "
            "outros), avaliando trade-offs de performance e custo para cada caso de uso.\n"
            "- Estruturar e otimizar bancos vetoriais (ChromaDB, FAISS) e implementar "
            "técnicas avançadas de RAG conectadas ao Snowflake e sistemas internos.\n"
            "- Implementar extração inteligente de dados via web scraping (Crawl4AI) e "
            "parsing de documentos complexos (Docling, Textract).\n"
            "- Integrar agentes a APIs internas para que executem tarefas e atualizem "
            "sistemas de forma autônoma.\n"
            "- Manter boas práticas de engenharia: código limpo, versionamento e "
            "documentação que permitam continuidade pelo time interno.\n\n"
            "Requisitos\n"
            "- Domínio de Python e bibliotecas voltadas a IA (Transformers, "
            "LangChain/Agno/LlamaIndex, scikit-learn, etc).\n"
            "- Experiência com frameworks de agentes autônomos e arquiteturas de "
            "ferramentas.\n"
            "- Experiência com ferramentas da AWS: S3, Lambda, ECR, SQS, Textract, "
            "EventBridge.\n"
            "- Vivência em integrar LLMs de mercado em aplicações produtivas.\n"
            "- Experiência com APIs (requests, FastAPI), manipulação de dados e conexão "
            "a bancos de dados.\n"
            "- Vivência com bancos vetoriais para busca semântica e RAG.\n"
            "- Vivência com Docker.\n"
            "- Boas práticas de versionamento (GitHub) e arquitetura de soluções "
            "escaláveis.\n"
            "- Conhecimento em deployment de LLMs em produção e prompt engineering.\n\n"
            "Diferenciais\n"
            "- Experiência em Machine Learning (supervisionado, não supervisionado e "
            "por reforço).\n"
            "- Vivência com MLOps e automação do ciclo de vida de modelos.\n"
            "- Conhecimento em otimização de LLMs.\n"
            "- Experiência com IA conversacional integrada ao WhatsApp.\n\n"
            "Conhecimentos e Habilidades necessárias:\n"
            "Python, frameworks de agentes autônomos, Ferramentas da AWS, S3, Lambda, "
            "SQS, Textract, EventBridge, LLMs, APIs, Manipulação de dados, RAG, Bancos "
            "vetoriais, Docker, GitHub, deployment de LLMs, Prompt engineering\n\n"
            "Benefícios:\n"
            "Auxílio Creche, Auxílio Home Office, Totalpass, Auxilio Estudo, Day Off "
            "Aniversário, Plano de Saúde, Plano Odontológico, Seguro de Vida, Vale "
            "Alimentação (Flexível), Vale Transporte\n\n"
            "Departamento:\n"
            "Growth & Digital Strategy"
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
