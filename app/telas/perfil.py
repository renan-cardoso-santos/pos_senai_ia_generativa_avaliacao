"""Perfil profissional: cadastro e atualização do **currículo padronizado**.

Esta tela é o ponto de partida do processo — o currículo padrão da plataforma é o
dado que inicia e alimenta toda a análise CV × vaga (ver
docs/dicionario_dados_curriculo_estruturado.md). O upload de um CV fora do padrão
é apenas um acelerador opcional que pré-preenche os campos; o usuário revisa,
completa os obrigatórios e salva. A análise em si mora na tela **Nova análise**,
que consome sempre este currículo já padronizado.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from agents.ia_service import get_ia_service
from agents.modelos import (
    CurriculoEstruturado,
    DadosPessoais,
    ExperienciaItem,
    FormacaoItem,
    RESUMO_MAX_PALAVRAS,
)
from app import db, exemplos, extracao_cv, lgpd, ui

# Colunas (ordem) das tabelas editáveis de experiência e formação.
_EXP_COLS = ["cargo", "empresa", "periodo", "descricao"]
_FORM_COLS = ["curso", "instituicao", "periodo"]


def render() -> None:
    ui.cabecalho(
        "Perfil profissional",
        "Cadastre e mantenha seu currículo padronizado — o dado que alimenta todas as análises.",
    )
    usuario_id = st.session_state.usuario["id"]
    _editor_curriculo(usuario_id)


# ---------------------------------------------------------------------------
# Currículo padronizado (upload → pré-preenchimento → revisão → salvar)
# ---------------------------------------------------------------------------
def _editor_curriculo(usuario_id: int) -> None:
    """Renderiza o cadastro/atualização do CV padronizado.

    O currículo padronizado fica sempre editável. O upload de um CV fora do padrão
    é apenas um acelerador opcional que pré-preenche os campos. Só é considerado
    salvo depois que o usuário grava o CV com todos os obrigatórios.
    """
    ultimo = db.ultimo_curriculo(usuario_id)
    with st.container(border=True):
        st.markdown("##### Currículo padronizado")
        st.caption(
            "Este é o **currículo padrão da plataforma** — o dado que inicia e alimenta "
            "toda a análise. Preencha os campos abaixo; se preferir, pré-preencha a "
            "partir de um arquivo."
        )

        # Acelerador OPCIONAL — pré-preenche o CV padronizado a partir de um arquivo.
        with st.expander("⬆️ Pré-preencher a partir de um arquivo (PDF/DOCX) — opcional"):
            arquivo = st.file_uploader("CV em PDF ou DOCX", type=["pdf", "docx"])
            if arquivo is not None and st.session_state.get("cv_arquivo_nome") != arquivo.name:
                with st.spinner("Extraindo e estruturando o CV…"):
                    texto = extracao_cv.extrair_texto(arquivo)
                    estruturado = ui.chamar_ia(get_ia_service().estruturar_cv, texto)
                st.session_state.cv_arquivo_nome = arquivo.name
                st.session_state.cv_texto_bruto = texto
                st.session_state.cv_estruturado = estruturado.model_dump()
                st.session_state.cv_token = f"upload-{arquivo.name}"
                st.session_state.cv_curriculo_id = None  # linha criada só ao salvar
                st.session_state.cv_salvo = False
                st.session_state.pop("cv_snapshot", None)
                # Snapshot de origem para rastreabilidade do pré-preenchimento.
                st.session_state.cv_origem = estruturado.model_dump()
                st.session_state.cv_origem_tipo = "arquivo"
                st.session_state.cv_origem_rotulo = arquivo.name
                st.success("Campos pré-preenchidos abaixo. Revise e complete os obrigatórios (*).")

        # Demonstração — preenche com um CV de exemplo (fictício), pronto para salvar.
        if st.button("📋 Preencher com um CV de exemplo (demonstração)"):
            exemplo = exemplos.cv_exemplo().model_dump()
            st.session_state.cv_estruturado = exemplo
            st.session_state.cv_origem = exemplo
            st.session_state.cv_origem_tipo = "exemplo"
            st.session_state.cv_origem_rotulo = "CV de exemplo"
            st.session_state.cv_token = "exemplo"
            st.session_state.cv_arquivo_nome = "CV de exemplo (demonstração)"
            st.session_state.cv_texto_bruto = ""
            st.session_state.cv_curriculo_id = None
            st.session_state.cv_salvo = False
            st.session_state.pop("cv_snapshot", None)
            st.rerun()

        # Estado inicial: último CV padronizado salvo, ou um CV em branco.
        if "cv_estruturado" not in st.session_state:
            dados_ultimo = db.ultimo_curriculo_estruturado(usuario_id)  # dados_pessoais decifrado
            if ultimo is not None and dados_ultimo is not None:
                st.session_state.cv_estruturado = dados_ultimo
                st.session_state.cv_curriculo_id = ultimo["id"]
                st.session_state.cv_token = f"ultimo-{ultimo['id']}"
                st.session_state.cv_snapshot = st.session_state.cv_estruturado
                st.session_state.cv_salvo = True
                st.session_state.cv_origem = st.session_state.cv_estruturado
                st.session_state.cv_origem_tipo = "salvo"
                st.session_state.cv_origem_rotulo = ultimo["nome_arquivo"] or ""
            else:
                st.session_state.cv_estruturado = CurriculoEstruturado().model_dump()
                st.session_state.cv_curriculo_id = None
                st.session_state.cv_token = "novo"
                st.session_state.cv_salvo = False
                st.session_state.cv_origem = CurriculoEstruturado().model_dump()
                st.session_state.cv_origem_tipo = "manual"
                st.session_state.cv_origem_rotulo = ""

        # Formulário do CV padronizado — sempre visível.
        _garantir_estado_editor(st.session_state.cv_estruturado, st.session_state.cv_token)
        estruturado = _editor_estruturado()
        atual = estruturado.model_dump()
        st.session_state.cv_estruturado = atual

        # Edição após salvar invalida o "salvo" (precisa re-salvar).
        if atual != st.session_state.get("cv_snapshot"):
            st.session_state.cv_salvo = False

        faltantes = estruturado.campos_faltantes()
        if faltantes:
            st.warning(
                "Preencha os campos obrigatórios para salvar:\n"
                + "\n".join(f"- {f}" for f in faltantes)
            )

        salvar = st.button(
            "💾 Salvar currículo padronizado",
            type="primary",
            disabled=bool(faltantes),
        )
        if salvar:
            cid = _persistir_curriculo(usuario_id, atual)
            st.session_state.cv_curriculo_id = cid
            st.session_state.cv_snapshot = atual
            st.session_state.cv_salvo = True
            st.toast("Currículo padronizado salvo.", icon="✅")

        # Baixar o CV editado no padrão da plataforma (JSON estruturado + texto).
        _download_curriculo(estruturado)

        # Rastreabilidade: de onde veio cada dado (origem × ajuste manual × pendente).
        with st.expander("🔎 Rastreabilidade do preenchimento"):
            _mostrar_rastreabilidade(
                atual,
                st.session_state.get("cv_origem", CurriculoEstruturado().model_dump()),
                st.session_state.get("cv_origem_tipo", "manual"),
                st.session_state.get("cv_origem_rotulo", ""),
            )

        if st.session_state.get("cv_salvo"):
            st.success("Currículo padronizado salvo. ✅")
            if st.button("🔍 Ir para Nova análise"):
                ui.navegar("Nova análise")
        elif not faltantes:
            st.info("Tudo preenchido! Clique em **Salvar** para registrar seu perfil.")


def _persistir_curriculo(usuario_id: int, estruturado: dict) -> int:
    """Cria a linha do currículo (se ainda não existe) e grava o CV padronizado."""
    cid = st.session_state.get("cv_curriculo_id")
    if cid is None:
        nome = st.session_state.get("cv_arquivo_nome") or "Currículo padronizado"
        texto_bruto = st.session_state.get("cv_texto_bruto", "")
        cid = db.salvar_curriculo(usuario_id, nome, texto_bruto)
    db.atualizar_estruturado(cid, estruturado)
    return cid


def _download_curriculo(estruturado: CurriculoEstruturado) -> None:
    """Download do CV editado em **Word (.docx)**, no layout-padrão da plataforma.

    O arquivo é editável no Word mantendo o formato e, se reenviado, volta a ser
    extraído corretamente. Reflete o estado atual do editor (mesmo antes de salvar).
    """
    from app import exportacao_cv

    st.caption("Baixe o currículo em **Word (.docx)** para editar mantendo o padrão:")
    st.download_button(
        "⬇️ Baixar CV padronizado (.docx)",
        data=exportacao_cv.curriculo_para_docx(estruturado),
        file_name="curriculo_padronizado.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        use_container_width=True,
    )


# ---------------------------------------------------------------------------
# Editor do CV padronizado
# ---------------------------------------------------------------------------
def _garantir_estado_editor(dados: dict, token: str) -> None:
    """Semeia o estado dos widgets uma vez por CV (evita conflito value×key)."""
    if st.session_state.get("cv_editor_token") == token:
        return
    st.session_state.cv_editor_token = token
    dp = dados.get("dados_pessoais", {}) or {}
    st.session_state["f_nome"] = dp.get("nome", "")
    st.session_state["f_email"] = dp.get("email", "")
    st.session_state["f_tel"] = dp.get("telefone", "")
    st.session_state["f_loc"] = dp.get("localizacao", "")
    st.session_state["f_lkd"] = dp.get("linkedin", "")
    st.session_state["f_resumo"] = dados.get("resumo", "")
    st.session_state["f_skills"] = "\n".join(dados.get("skills", []) or [])
    st.session_state["f_idiomas"] = "\n".join(dados.get("idiomas", []) or [])
    st.session_state["f_cert"] = "\n".join(dados.get("certificacoes", []) or [])
    exp = [_norm_exp(e) for e in (dados.get("experiencias") or [])] or [_norm_exp({})]
    form = [_norm_form(f) for f in (dados.get("formacao") or [])] or [_norm_form({})]
    # DataFrames persistidos são a fonte da verdade dos editores — é o formato que
    # o st.data_editor suporta para editar células já preenchidas (não só add/del).
    st.session_state["f_exp_df"] = pd.DataFrame(exp, columns=_EXP_COLS)
    st.session_state["f_form_df"] = pd.DataFrame(form, columns=_FORM_COLS)
    # Zera deltas de edições anteriores do data_editor.
    st.session_state.pop("f_exp", None)
    st.session_state.pop("f_form", None)


def _editor_estruturado() -> CurriculoEstruturado:
    st.markdown("**Dados pessoais**")
    st.info(lgpd.AVISO_COLETA)  # nota padrão de coleta (LGPD)
    c1, c2 = st.columns(2)
    nome = c1.text_input("Nome completo *", key="f_nome", max_chars=120)
    email = c2.text_input("E-mail *", key="f_email", max_chars=120)
    c3, c4 = st.columns(2)
    telefone = c3.text_input("Telefone *", key="f_tel", max_chars=20)
    localizacao = c4.text_input("Localização *", key="f_loc", max_chars=80)
    linkedin = st.text_input("LinkedIn (opcional)", key="f_lkd", max_chars=200)

    resumo = st.text_area("Resumo profissional *", key="f_resumo", height=140)
    n_palavras = len(resumo.split())
    excedeu = n_palavras > RESUMO_MAX_PALAVRAS
    st.caption(
        f"{'⚠️ ' if excedeu else ''}{n_palavras}/{RESUMO_MAX_PALAVRAS} palavras"
    )

    st.markdown("**Experiências profissionais** &nbsp;⁎ _cargo, empresa e período são obrigatórios; edite as células diretamente._")
    exp_edit = st.data_editor(
        st.session_state["f_exp_df"],
        key="f_exp",
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            # Sem max_chars: um valor importado que exceda o limite deixaria a
            # célula não-editável no data_editor (só permitindo add/remover linha).
            "cargo": st.column_config.TextColumn("Cargo *"),
            "empresa": st.column_config.TextColumn("Empresa *"),
            "periodo": st.column_config.TextColumn("Período *"),
            "descricao": st.column_config.TextColumn("Descrição", width="large"),
        },
    )

    st.markdown("**Formação acadêmica** &nbsp;⁎ _curso, instituição e período são obrigatórios; edite as células diretamente._")
    form_edit = st.data_editor(
        st.session_state["f_form_df"],
        key="f_form",
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "curso": st.column_config.TextColumn("Curso *"),
            "instituicao": st.column_config.TextColumn("Instituição *"),
            "periodo": st.column_config.TextColumn("Período *"),
        },
    )
    exp_rows = exp_edit.to_dict("records")
    form_rows = form_edit.to_dict("records")

    c5, c6 = st.columns(2)
    skills_txt = c5.text_area(
        "Skills * (uma por linha ou separadas por vírgula)", key="f_skills", height=120
    )
    idiomas_txt = c6.text_area(
        "Idiomas * (um por linha ou separados por vírgula)", key="f_idiomas", height=120
    )
    cert_txt = st.text_area("Certificações (opcional, uma por linha)", key="f_cert", height=100)

    return CurriculoEstruturado(
        dados_pessoais=DadosPessoais(
            nome=nome, email=email, telefone=telefone,
            localizacao=localizacao, linkedin=linkedin,
        ),
        resumo=resumo,
        experiencias=[
            ExperienciaItem(**_norm_exp(e)) for e in exp_rows if _linha_preenchida(e)
        ],
        formacao=[
            FormacaoItem(**_norm_form(f)) for f in form_rows if _linha_preenchida(f)
        ],
        skills=_split_itens(skills_txt),
        idiomas=_split_itens(idiomas_txt),
        certificacoes=_split_linhas(cert_txt),
    )


# -- Rastreabilidade do pré-preenchimento -----------------------------------
_ORIGEM_TEXTO = {
    "arquivo": "📄 Do arquivo",
    "salvo": "💾 Do CV salvo",
    "exemplo": "📋 Do exemplo",
    "manual": "✏️ Manual",
    "pendente": "⚪ Pendente",
}


def _classificar_campo(valor: str, origem_valor: str, tipo_base: str) -> str:
    """Classifica um campo escalar: veio da origem, é manual, ou está pendente."""
    if not str(valor or "").strip():
        return "pendente"
    origem_valor = str(origem_valor or "").strip()
    if tipo_base != "manual" and origem_valor and str(valor).strip() == origem_valor:
        return tipo_base  # "arquivo" ou "salvo"
    return "manual"


def _contar_itens(atuais: list, origem: list, tipo_base: str, chave) -> tuple[int, int, int]:
    """Conta itens de uma lista por origem: (total, da_fonte, manuais)."""
    origem_chaves = {chave(i) for i in origem if chave(i)}
    da_fonte = manuais = 0
    for item in atuais:
        k = chave(item)
        if not k:
            continue
        if tipo_base != "manual" and k in origem_chaves:
            da_fonte += 1
        else:
            manuais += 1
    return da_fonte + manuais, da_fonte, manuais


def _mostrar_rastreabilidade(atual: dict, origem: dict, tipo_base: str, rotulo: str) -> None:
    origem_desc = {
        "arquivo": f"arquivo **{rotulo}**",
        "salvo": "**CV salvo anteriormente**",
        "exemplo": "**CV de exemplo** (demonstração)",
        "manual": "**preenchimento manual** (sem arquivo)",
    }.get(tipo_base, "**preenchimento manual**")
    st.caption(
        f"Origem base: {origem_desc}. Cada campo mostra se veio da origem, "
        "foi ajustado manualmente ou está pendente."
    )

    dp_a = atual.get("dados_pessoais", {})
    dp_o = origem.get("dados_pessoais", {})
    escalares = [
        ("Nome completo", dp_a.get("nome", ""), dp_o.get("nome", "")),
        ("E-mail", dp_a.get("email", ""), dp_o.get("email", "")),
        ("Telefone", dp_a.get("telefone", ""), dp_o.get("telefone", "")),
        ("Localização", dp_a.get("localizacao", ""), dp_o.get("localizacao", "")),
        ("LinkedIn", dp_a.get("linkedin", ""), dp_o.get("linkedin", "")),
        ("Resumo", atual.get("resumo", ""), origem.get("resumo", "")),
    ]
    linhas = ["| Campo | Origem |", "|---|---|"]
    for nome, val, org in escalares:
        linhas.append(f"| {nome} | {_ORIGEM_TEXTO[_classificar_campo(val, org, tipo_base)]} |")
    st.markdown("\n".join(linhas))

    _exp_key = lambda e: (
        str(e.get("cargo", "")).strip().lower(),
        str(e.get("empresa", "")).strip().lower(),
        str(e.get("periodo", "")).strip().lower(),
    )
    _form_key = lambda f: (
        str(f.get("curso", "")).strip().lower(),
        str(f.get("instituicao", "")).strip().lower(),
        str(f.get("periodo", "")).strip().lower(),
    )
    _txt_key = lambda s: str(s).strip().lower()

    blocos = [
        ("Experiências", atual.get("experiencias", []), origem.get("experiencias", []), _exp_key),
        ("Formação", atual.get("formacao", []), origem.get("formacao", []), _form_key),
        ("Skills", atual.get("skills", []), origem.get("skills", []), _txt_key),
        ("Idiomas", atual.get("idiomas", []), origem.get("idiomas", []), _txt_key),
        ("Certificações", atual.get("certificacoes", []), origem.get("certificacoes", []), _txt_key),
    ]
    emoji = {"arquivo": "📄", "salvo": "💾", "exemplo": "📋"}.get(tipo_base, "")
    rotulo_fonte = {"arquivo": "do arquivo", "salvo": "do CV salvo", "exemplo": "do exemplo"}.get(
        tipo_base, "da origem"
    )
    itens_md: list[str] = []
    for nome, atuais, orig, chave in blocos:
        total, da_fonte, manuais = _contar_itens(atuais, orig, tipo_base, chave)
        if total == 0:
            itens_md.append(f"- **{nome}:** ⚪ nenhum item")
        elif tipo_base == "manual" or da_fonte == 0:
            itens_md.append(f"- **{nome}:** {total} no total · ✏️ {manuais} manual(is)")
        else:
            itens_md.append(
                f"- **{nome}:** {total} no total · {emoji} {da_fonte} {rotulo_fonte}, "
                f"✏️ {manuais} manual(is)"
            )
    st.markdown("\n".join(itens_md))


# -- Helpers de normalização ------------------------------------------------
def _txt(valor) -> str:
    """Texto limpo, tratando None e NaN (célula vazia do data_editor) como ''."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    return str(valor).strip()


def _norm_exp(e: dict) -> dict:
    return {k: _txt(e.get(k)) for k in _EXP_COLS}


def _norm_form(f: dict) -> dict:
    return {k: _txt(f.get(k)) for k in _FORM_COLS}


def _linha_preenchida(linha: dict) -> bool:
    return any(_txt(v) for v in linha.values())


def _split_itens(texto: str) -> list[str]:
    """Quebra em itens por linha ou vírgula/;, sem duplicar nem deixar vazios."""
    itens: list[str] = []
    for parte in (texto or "").replace(",", "\n").replace(";", "\n").splitlines():
        p = parte.strip(" -•\t")
        if p and p not in itens:
            itens.append(p)
    return itens


def _split_linhas(texto: str) -> list[str]:
    return [l.strip(" -•\t") for l in (texto or "").splitlines() if l.strip()]
