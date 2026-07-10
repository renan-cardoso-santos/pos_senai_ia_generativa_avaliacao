"""Extração de texto de currículos (PDF/DOCX).

O upload do Streamlit vive em memória (UploadedFile, com atributos .name e
.read()). Aqui convertemos esse conteúdo em texto puro, que vira insumo da
análise. Sem dependência de disco.
"""
from __future__ import annotations

import io


def extrair_texto(arquivo) -> str:
    """Recebe um UploadedFile do Streamlit e devolve o texto extraído.

    Suporta .pdf (pypdf) e .docx (python-docx). Extensão desconhecida tenta
    decodificar como texto simples.
    """
    nome = (getattr(arquivo, "name", "") or "").lower()
    dados = arquivo.read()

    if nome.endswith(".pdf"):
        return _extrair_pdf(dados)
    if nome.endswith(".docx"):
        return _extrair_docx(dados)
    # Fallback: texto simples.
    try:
        return dados.decode("utf-8", errors="ignore").strip()
    except Exception:
        return ""


def _extrair_pdf(dados: bytes) -> str:
    from pypdf import PdfReader

    leitor = PdfReader(io.BytesIO(dados))
    partes = [(pagina.extract_text() or "") for pagina in leitor.pages]
    return "\n".join(partes).strip()


def _extrair_docx(dados: bytes) -> str:
    import docx

    documento = docx.Document(io.BytesIO(dados))
    return "\n".join(p.text for p in documento.paragraphs).strip()
