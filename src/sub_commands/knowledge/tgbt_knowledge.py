# std
import json

# pip
import typer

# local
from state.knowledge_system import KnowledgeSystem


def tgbt_knowledge_search_impl(question: str) -> None:
    """repo についての質問を知識システムで検索し、JSON として出力する."""
    # Codex CLI から機械的に読めるよう、検索結果は schema と同じ JSON で出力する。
    result = KnowledgeSystem().search(question)
    typer.echo(
        json.dumps(
            result.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        )
    )
