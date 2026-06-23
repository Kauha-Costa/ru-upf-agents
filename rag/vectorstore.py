"""
Vectorstore — wrapper fino sobre o ChromaDB para o histórico de cardápios.

Usa embeddings gerados localmente via Ollama (config.EMBED_MODEL), não o
embedding function padrão do Chroma — mantém tudo 100% local, consistente
com o resto do projeto.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import chromadb
import ollama

import config

NOME_COLECAO = "cardapios_historico"

_client = None
_colecao = None


def _colecao_cardapios():
    """Inicializa o cliente/coleção uma única vez (lazy singleton)."""
    global _client, _colecao
    if _colecao is None:
        _client = chromadb.PersistentClient(path=str(config.VECTORSTORE_DIR))
        _colecao = _client.get_or_create_collection(NOME_COLECAO)
    return _colecao


def embed_texto(texto: str) -> list[float]:
    """Gera o embedding local (config.EMBED_MODEL via Ollama) de um texto."""
    resposta = ollama.embed(model=config.EMBED_MODEL, input=texto)
    return list(resposta.embeddings[0])


def _texto_do_dia(dia_semana: str, data_iso: str, dados: dict) -> str:
    """Representação textual de um dia de cardápio — é isso que vira o
    "documento" indexado e o que o LLM vê de volta numa busca."""
    return (
        f"{dia_semana.title()} ({data_iso}): {dados.get('itens_principais', '')}. "
        f"Salada: {dados.get('salada', '')}. Suco: {dados.get('suco', '')}."
    )


def adicionar_cardapio_dia(dia_semana: str, data_iso: str, dados: dict) -> None:
    """Indexa (ou reindexa, se já existir) o cardápio de um dia específico.
    O id é a própria data — então rodar de novo no mesmo dia substitui em
    vez de duplicar (idempotente)."""
    texto = _texto_do_dia(dia_semana, data_iso, dados)
    embedding = embed_texto(texto)
    _colecao_cardapios().upsert(
        ids=[data_iso],
        embeddings=[embedding],
        documents=[texto],
        metadatas=[{"dia_semana": dia_semana, "data": data_iso}],
    )


def buscar_cardapios_similares(pergunta: str, n_resultados: int = 3) -> list[dict]:
    """Busca por similaridade semântica no histórico. Retorna uma lista de
    {"texto": ..., "dia_semana": ..., "data": ...} dos dias mais relevantes
    para a pergunta."""
    colecao = _colecao_cardapios()
    if colecao.count() == 0:
        return []

    embedding_pergunta = embed_texto(pergunta)
    resultado = colecao.query(
        query_embeddings=[embedding_pergunta],
        n_results=min(n_resultados, colecao.count()),
    )

    documentos = resultado["documents"][0]
    metadados = resultado["metadatas"][0]
    return [
        {"texto": doc, **meta} for doc, meta in zip(documentos, metadados)
    ]
