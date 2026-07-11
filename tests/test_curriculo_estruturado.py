"""Testes da feature de currículo padronizado (CV estruturado).

Cobre as três peças da lógica de negócio:
- `estruturar_cv`: parser heurístico texto bruto → CV estruturado (pré-preenchimento);
- gate de obrigatoriedade (`campos_faltantes`) e serialização (`para_texto`);
- `db.curriculo_padronizado_texto`: a entrada padronizada consumida pelas telas.
"""
from __future__ import annotations

import pytest

from agents.modelos import (
    RESUMO_MAX_PALAVRAS,
    CurriculoEstruturado,
    DadosPessoais,
    ExperienciaItem,
    FormacaoItem,
)
from tools import definicoes as tools

CV_EXEMPLO = """Maria Souza
maria@ex.com | (21) 99999-1111 | linkedin.com/in/maria

RESUMO
Engenheira de dados com foco em pipelines.

EXPERIENCIA
Engenheira de Dados — DataCo (2020 - Atual)
Construi pipelines em Spark.
Relatorios em Power BI.
Analista de Dados — Beta (2018 - 2020)

FORMACAO
Bacharelado em Ciencia da Computacao — USP (2014 - 2018)

HABILIDADES
Python, Spark, SQL

IDIOMAS
Ingles avancado, Espanhol intermediario
"""


@pytest.fixture(autouse=True)
def _chave_lgpd_isolada(tmp_path_factory, monkeypatch):
    """Isola a chave de cifragem de PII em um arquivo temporário por sessão."""
    from app import lgpd

    chave = tmp_path_factory.mktemp("lgpd") / ".lgpd.key"
    monkeypatch.setattr(lgpd, "_KEY_PATH", str(chave))
    monkeypatch.setattr(lgpd, "_fernet_cache", None)


@pytest.fixture
def cv_completo() -> CurriculoEstruturado:
    return CurriculoEstruturado(
        dados_pessoais=DadosPessoais(
            nome="Ana", email="ana@ex.com", telefone="11999", localizacao="SP"
        ),
        resumo="Resumo profissional.",
        experiencias=[ExperienciaItem(cargo="Dev", empresa="X", periodo="2020-2022")],
        formacao=[FormacaoItem(curso="CC", instituicao="USP", periodo="2019")],
        skills=["Python"],
        idiomas=["Inglês — avançado"],
    )


# CV no "modelo padrão": marcador ➢ por vaga (empresa / cargo / período em linhas
# separadas), • por curso (Curso, Instituição, Local (período)), header IDIOMA no
# singular e localização "Cidade, Estado, País".
CV_MODELO_PADRAO = """RENAN CARDOSO DOS SANTOS
Salvador, Bahia, Brasil.
+55 (71) 98285-2775
Email: renan.cs.sants@gmail.com
LinkedIn: https://www.linkedin.com/in/renan-cardoso-8323b151/

OBJETIVO
Cientista de Dados Pleno | Visão Computacional e Machine Learning

RESUMO PROFISSIONAL
Cientista de Dados com atuação em Machine Learning e Visão Computacional.

FORMAÇÃO ACADÊMICA
• Mestrado Profissional em Gestão e Tecnologia Industrial com Computação Quântica, SENAI CIMATEC/QuIIn (Quantum Industrial Innovation), Salvador - (2025 – atual)
• Engenharia Mecatrônica, Universidade Salvador (UNIFACS), Salvador (2006 — 2013)

COMPETÊNCIAS TÉCNICAS (STACK)
• Linguagens: Python, SQL
• MLOps: MLflow, Docker

IDIOMA
• Inglês Intermediário (B1)

EXPERIÊNCIA PROFISSIONAL
➢ Freelancer
Consultor em Data Analytics e IA Generativa
fev/2026 – atual
Desenvolvimento de plataforma de Analytics e IA.
o Arquitetura de dados end-to-end com Data Warehouse.
o Implementação de soluções com IA Generativa e RAG.
➢ PetroReconcavo | Oil & Gas
Analista de Dados
Jun/2023 a jul/2024
o Preparação e processamento de dados com Python e PySpark.
"""


# ---------------------------------------------------------------------------
# estruturar_cv — pré-preenchimento
# ---------------------------------------------------------------------------
def test_estruturar_extrai_contato():
    cv = tools.executar("estruturar_cv", cv_texto=CV_EXEMPLO)
    assert cv.dados_pessoais.nome == "Maria Souza"
    assert cv.dados_pessoais.email == "maria@ex.com"
    assert cv.dados_pessoais.telefone == "(21) 99999-1111"
    assert "linkedin.com/in/maria" in cv.dados_pessoais.linkedin


def test_estruturar_separa_experiencia_por_traco():
    cv = tools.executar("estruturar_cv", cv_texto=CV_EXEMPLO)
    primeira = cv.experiencias[0]
    assert primeira.cargo == "Engenheira de Dados"
    assert primeira.empresa == "DataCo"
    assert primeira.periodo == "2020 - Atual"
    # A linha "Relatorios em Power BI" é descrição, não abre novo registro.
    assert "Power BI" in primeira.descricao


def test_estruturar_nao_quebra_curso_no_conector_em():
    cv = tools.executar("estruturar_cv", cv_texto=CV_EXEMPLO)
    formacao = cv.formacao[0]
    assert formacao.curso == "Bacharelado em Ciencia da Computacao"
    assert formacao.instituicao == "USP"


def test_estruturar_lista_skills_e_idiomas():
    cv = tools.executar("estruturar_cv", cv_texto=CV_EXEMPLO)
    assert cv.skills == ["Python", "Spark", "SQL"]
    assert "Ingles avancado" in cv.idiomas


def test_estruturar_detecta_localizacao_cidade_uf():
    cv = tools.executar(
        "estruturar_cv", cv_texto="Fulano Tal\nfulano@ex.com\nSão Paulo, SP\n"
    )
    assert cv.dados_pessoais.localizacao == "São Paulo, SP"


def test_estruturar_texto_vazio_nao_quebra():
    cv = tools.executar("estruturar_cv", cv_texto="")
    assert isinstance(cv, CurriculoEstruturado)
    assert cv.campos_faltantes()  # tudo pendente


# ---------------------------------------------------------------------------
# estruturar_cv — modelo padrão (marcadores ➢/•, IDIOMA, Cidade, Estado, País)
# ---------------------------------------------------------------------------
def test_modelo_padrao_localizacao_cidade_estado_pais():
    cv = tools.executar("estruturar_cv", cv_texto=CV_MODELO_PADRAO)
    assert cv.dados_pessoais.localizacao == "Salvador, Bahia, Brasil"


def test_modelo_padrao_experiencia_nao_quebra_por_marcador():
    cv = tools.executar("estruturar_cv", cv_texto=CV_MODELO_PADRAO)
    assert len(cv.experiencias) == 2
    primeira = cv.experiencias[0]
    assert primeira.empresa == "Freelancer"
    assert primeira.cargo == "Consultor em Data Analytics e IA Generativa"
    assert primeira.periodo == "fev/2026 – atual"
    # A descrição junta intro + sub-bullets (sem o marcador 'o').
    assert "Arquitetura de dados" in primeira.descricao
    assert not primeira.descricao.startswith("o ")
    # 2ª vaga: empresa vem antes do '|', cargo e período nas linhas seguintes.
    segunda = cv.experiencias[1]
    assert segunda.empresa == "PetroReconcavo"
    assert segunda.cargo == "Analista de Dados"
    assert segunda.periodo == "Jun/2023 a jul/2024"


def test_modelo_padrao_formacao_separa_curso_e_instituicao():
    cv = tools.executar("estruturar_cv", cv_texto=CV_MODELO_PADRAO)
    assert len(cv.formacao) == 2
    mestrado = cv.formacao[0]
    assert mestrado.curso.startswith("Mestrado Profissional em Gestão")
    assert "SENAI CIMATEC/QuIIn" in mestrado.instituicao
    assert mestrado.periodo == "2025 – atual"
    eng = cv.formacao[1]
    assert eng.curso == "Engenharia Mecatrônica"
    assert "Universidade Salvador (UNIFACS)" in eng.instituicao
    assert eng.periodo == "2006 — 2013"


def test_modelo_padrao_idioma_singular_preenche_e_nao_vaza_para_skills():
    cv = tools.executar("estruturar_cv", cv_texto=CV_MODELO_PADRAO)
    assert cv.idiomas == ["Inglês Intermediário (B1)"]
    # O idioma NÃO deve aparecer dentro das skills.
    assert all("Inglês" not in s for s in cv.skills)


def test_modelo_padrao_gate_exige_idioma():
    cv = tools.executar("estruturar_cv", cv_texto=CV_MODELO_PADRAO)
    # Modelo padrão completo passa no gate...
    assert cv.campos_faltantes() == []
    # ...e remover os idiomas passa a bloquear o salvamento.
    cv.idiomas = []
    assert "Ao menos um idioma" in cv.campos_faltantes()


# ---------------------------------------------------------------------------
# Gate de obrigatoriedade
# ---------------------------------------------------------------------------
def test_gate_completo_sem_faltantes(cv_completo):
    assert cv_completo.campos_faltantes() == []
    assert cv_completo.esta_completo()


def test_cv_exemplo_demonstracao_esta_completo():
    from app import exemplos

    # O CV de exemplo (botão de demonstração) deve estar pronto para salvar.
    assert exemplos.cv_exemplo().esta_completo()
    # E o texto-modelo (arquivo de upload) deve extrair sem pendências.
    est = tools.executar("estruturar_cv", cv_texto=exemplos.texto_cv_exemplo())
    assert est.campos_faltantes() == []


def test_gate_email_invalido(cv_completo):
    cv_completo.dados_pessoais.email = "sem-arroba"
    assert "E-mail válido" in cv_completo.campos_faltantes()


def test_gate_localizacao_obrigatoria(cv_completo):
    cv_completo.dados_pessoais.localizacao = ""
    assert "Localização" in cv_completo.campos_faltantes()


def test_gate_periodo_obrigatorio_na_experiencia(cv_completo):
    cv_completo.experiencias[0].periodo = ""
    assert any("experiência" in f for f in cv_completo.campos_faltantes())


def test_gate_resumo_excede_limite(cv_completo):
    cv_completo.resumo = "palavra " * (RESUMO_MAX_PALAVRAS + 1)
    assert any(str(RESUMO_MAX_PALAVRAS) in f for f in cv_completo.campos_faltantes())


def test_para_texto_tem_secoes(cv_completo):
    texto = cv_completo.para_texto()
    for cabecalho in ("RESUMO", "EXPERIÊNCIA", "FORMAÇÃO", "SKILLS"):
        assert cabecalho in texto


# ---------------------------------------------------------------------------
# Consumo padronizado pelas telas
# ---------------------------------------------------------------------------
def test_curriculo_padronizado_texto(tmp_path, monkeypatch, cv_completo):
    import os

    from app import db

    monkeypatch.setattr(db, "DB_PATH", os.path.join(tmp_path, "app.db"))
    db.criar_tabelas()
    uid = db.criar_usuario("t@t.com", "hash", "T")

    # Sem estruturado → fallback ao texto bruto.
    cid = db.salvar_curriculo(uid, "cv.pdf", "TEXTO BRUTO")
    assert db.curriculo_padronizado_texto(uid) == "TEXTO BRUTO"

    # Com estruturado → texto padronizado (para_texto).
    db.atualizar_estruturado(cid, cv_completo.model_dump())
    texto = db.curriculo_padronizado_texto(uid)
    assert "RESUMO" in texto and "SKILLS" in texto
    assert "TEXTO BRUTO" not in texto


# ---------------------------------------------------------------------------
# LGPD — proteção de dados pessoais em repouso
# ---------------------------------------------------------------------------
def test_lgpd_cifrar_decifrar_roundtrip():
    from app import lgpd

    token = lgpd.cifrar("ana@ex.com")
    assert token.startswith("enc:") and "ana@ex.com" not in token
    assert lgpd.decifrar(token) == "ana@ex.com"
    # Valor legado/claro (sem prefixo) passa direto.
    assert lgpd.decifrar("texto claro") == "texto claro"
    # Idempotente: não recifra.
    assert lgpd.cifrar(token) == token


def test_lgpd_proteger_revelar_estruturado(cv_completo):
    from app import lgpd

    seguro = lgpd.proteger_estruturado(cv_completo.model_dump())
    for campo in ("nome", "email", "telefone", "localizacao"):  # preenchidos
        valor = seguro["dados_pessoais"][campo]
        assert valor.startswith("enc:")  # cifrado
    revelado = lgpd.revelar_estruturado(seguro)
    assert revelado["dados_pessoais"]["nome"] == "Ana"
    assert revelado["dados_pessoais"]["email"] == "ana@ex.com"


def test_lgpd_redige_pii_em_texto_livre():
    from app import lgpd

    bruto = "Contato: ana@ex.com, (11) 99999-1111, linkedin.com/in/ana"
    redigido = lgpd.redigir_pii(bruto)
    assert "ana@ex.com" not in redigido
    assert "99999-1111" not in redigido
    assert "linkedin.com/in/ana" not in redigido
    assert "removido" in redigido


def test_lgpd_banco_nao_guarda_pii_em_claro(tmp_path, monkeypatch, cv_completo):
    import json
    import os

    from app import db

    monkeypatch.setattr(db, "DB_PATH", os.path.join(tmp_path, "app.db"))
    db.criar_tabelas()
    uid = db.criar_usuario("t@t.com", "hash", "T")
    cid = db.salvar_curriculo(uid, "cv.pdf", "")
    db.atualizar_estruturado(cid, cv_completo.model_dump())

    # O JSON cru no banco não pode conter PII em claro.
    with db.conectar() as conn:
        raw = conn.execute(
            "SELECT estruturado_json FROM curriculos WHERE id = ?", (cid,)
        ).fetchone()["estruturado_json"]
    assert "ana@ex.com" not in raw and "Ana" not in raw
    assert "enc:" in raw

    # Mas o titular lê os dados decifrados.
    dados = db.ultimo_curriculo_estruturado(uid)
    assert dados["dados_pessoais"]["email"] == "ana@ex.com"


# ---------------------------------------------------------------------------
# Rastreabilidade do pré-preenchimento (tela Perfil profissional)
# ---------------------------------------------------------------------------
def test_rastreabilidade_classifica_campo_escalar():
    from app.telas import perfil

    # Campo inalterado em relação à origem "arquivo" → veio do arquivo.
    assert perfil._classificar_campo("Ana", "Ana", "arquivo") == "arquivo"
    # Campo editado → manual.
    assert perfil._classificar_campo("ana@new.com", "ana@old.com", "arquivo") == "manual"
    # Campo preenchido que não existia na origem → manual.
    assert perfil._classificar_campo("119", "", "arquivo") == "manual"
    # Vazio → pendente.
    assert perfil._classificar_campo("", "", "arquivo") == "pendente"
    # Origem manual: mesmo igualando, conta como manual (não há fonte).
    assert perfil._classificar_campo("Ana", "Ana", "manual") == "manual"


def test_rastreabilidade_conta_itens_de_lista():
    from app.telas import perfil

    chave = lambda s: str(s).strip().lower()
    # 2 skills da origem + 1 adicionada manualmente.
    total, da_fonte, manuais = perfil._contar_itens(
        ["python", "sql", "spark"], ["python", "sql"], "arquivo", chave
    )
    assert (total, da_fonte, manuais) == (3, 2, 1)
    # Origem manual → tudo manual.
    total, da_fonte, manuais = perfil._contar_itens(
        ["python"], [], "manual", chave
    )
    assert (total, da_fonte, manuais) == (1, 0, 1)


# ---------------------------------------------------------------------------
# Editor das tabelas (data_editor) — consumo dos registros editados
# ---------------------------------------------------------------------------
def test_editor_round_trip_edicao_de_celula_propaga():
    """Simula o data_editor: DataFrame semeado → edição de célula → registros.

    Garante que editar um campo já preenchido (e não só add/remover linha) é
    refletido no CurriculoEstruturado montado a partir de `df.to_dict('records')`.
    """
    import pandas as pd
    from app.telas import perfil

    df = pd.DataFrame(
        [{"cargo": "Analista", "empresa": "Petro", "periodo": "2023-2024", "descricao": "x"}],
        columns=perfil._EXP_COLS,
    )
    # Usuário edita a célula 'cargo' da linha já preenchida.
    df.loc[0, "cargo"] = "Cientista de Dados"
    rows = df.to_dict("records")
    exps = [
        perfil.ExperienciaItem(**perfil._norm_exp(e))
        for e in rows
        if perfil._linha_preenchida(e)
    ]
    assert len(exps) == 1
    assert exps[0].cargo == "Cientista de Dados"
    assert exps[0].empresa == "Petro"


def test_editor_linha_vazia_com_nan_e_descartada():
    """Linha nova em branco (células NaN do data_editor) não vira experiência."""
    import pandas as pd
    from app.telas import perfil

    df = pd.DataFrame(
        [
            {"cargo": "Dev", "empresa": "ACME", "periodo": "2020", "descricao": "y"},
            {"cargo": None, "empresa": None, "periodo": None, "descricao": None},
        ],
        columns=perfil._EXP_COLS,
    )
    rows = df.to_dict("records")
    assert perfil._txt(rows[1]["cargo"]) == ""  # NaN/None → ""
    validas = [e for e in rows if perfil._linha_preenchida(e)]
    assert len(validas) == 1  # linha em branco descartada
    assert perfil._norm_form({"curso": float("nan"), "instituicao": "USP", "periodo": ""}) == {
        "curso": "",
        "instituicao": "USP",
        "periodo": "",
    }


# ---------------------------------------------------------------------------
# Exportação para Word (.docx) — download no padrão da plataforma
# ---------------------------------------------------------------------------
def test_download_docx_preserva_padrao_round_trip():
    """Estruturado → .docx → extração → parse deve preservar os campos-chave."""
    import io

    import docx

    from app import exportacao_cv, extracao_cv

    original = CurriculoEstruturado(
        dados_pessoais=DadosPessoais(
            nome="Renan Cardoso",
            email="renan@ex.com",
            telefone="(71) 98285-2775",
            localizacao="Salvador, Bahia, Brasil",
            linkedin="https://www.linkedin.com/in/renan/",
        ),
        resumo="Cientista de Dados com foco em Visão Computacional e MLOps.",
        experiencias=[
            ExperienciaItem(
                cargo="Analista de Dados",
                empresa="PetroReconcavo",
                periodo="Jun/2023 a jul/2024",
                descricao="Processamento de dados com Python e PySpark.",
            ),
        ],
        formacao=[
            FormacaoItem(
                curso="Engenharia Mecatrônica",
                instituicao="Universidade Salvador (UNIFACS), Salvador",
                periodo="2006 — 2013",
            ),
        ],
        skills=["Python", "SQL"],
        idiomas=["Inglês Intermediário (B1)"],
        certificacoes=["IBM Data Science Professional Certificate"],
    )

    dados = exportacao_cv.curriculo_para_docx(original)
    assert dados[:2] == b"PK"  # .docx é um zip

    class _Fake:
        name = "curriculo_padronizado.docx"

        def __init__(self, b):
            self._b = b

        def read(self):
            return self._b

    texto = extracao_cv.extrair_texto(_Fake(dados))
    reparse = tools.executar("estruturar_cv", cv_texto=texto)

    assert reparse.dados_pessoais.nome == "Renan Cardoso"
    assert reparse.dados_pessoais.localizacao == "Salvador, Bahia, Brasil"
    assert reparse.campos_faltantes() == []
    exp = reparse.experiencias[0]
    assert exp.empresa == "PetroReconcavo"
    assert exp.cargo == "Analista de Dados"
    assert exp.periodo == "Jun/2023 a jul/2024"
    form = reparse.formacao[0]
    assert form.curso == "Engenharia Mecatrônica"
    assert "UNIFACS" in form.instituicao
    assert reparse.idiomas == ["Inglês Intermediário (B1)"]
