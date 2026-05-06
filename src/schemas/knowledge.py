# std
from typing import ClassVar, Literal

# pip
from pydantic import BaseModel, ConfigDict, Field


class StrictKnowledgeModel(BaseModel):
    """
    知識システム用 schema の基底モデル。
    """

    model_config = ConfigDict(extra="forbid")


class KnowledgeReference(StrictKnowledgeModel):
    """
    知識が根拠として参照した知識ソースファイル。
    """

    path: str
    hash: str


class KnowledgeIndexEntry(StrictKnowledgeModel):
    """
    知識ソースファイルの目次 entry。
    """

    path: str
    description: str
    hash: str


class KnowledgeIndex(StrictKnowledgeModel):
    """
    知識ソースファイルの目次ファイル。
    """

    entries: list[KnowledgeIndexEntry]


class KnowledgeSourceConfig(StrictKnowledgeModel):
    """
    知識ソースファイル走査の repo 固有除外設定。
    """

    excluded_path_parts: list[str] = Field(default_factory=list)
    excluded_file_names: list[str] = Field(default_factory=list)
    excluded_globs: list[str] = Field(default_factory=list)
    max_file_bytes: int = Field(default=1024 * 1024, gt=0)


class KnowledgeFileMetadata(StrictKnowledgeModel):
    """
    知識ファイルの YAML front matter。
    """

    status: Literal["valid", "invalid"]
    summary: str
    references: list[KnowledgeReference]


class KnowledgeFile(StrictKnowledgeModel):
    """
    知識ファイル 1 件の構造化表現。
    """

    knowledge_id: str
    metadata: KnowledgeFileMetadata
    body: str


class KnowledgeSearchResult(StrictKnowledgeModel):
    """
    知識検索の結果。
    """

    answer: str
    related_paths: list[str]


class IndexDescriptionResponse(StrictKnowledgeModel):
    """
    目次 entry 用の説明生成結果。
    """

    TGBT_OUTPUT_SCHEMA_PROMPT: ClassVar[str] = """\
Field rules:
- description: Write concise Japanese bullet points describing what is in the file.
- description: Focus on natural-language searchability.
- description: Do not mention implementation facts that are not present in the file.
"""

    description: str


class KnowledgeRepairResponse(StrictKnowledgeModel):
    """
    知識ファイル修正の生成結果。
    """

    TGBT_OUTPUT_SCHEMA_PROMPT: ClassVar[str] = """\
Field rules:
- knowledge.metadata.status: Use "valid" only when the body is supported by references.
- knowledge.metadata.summary: Write a short Japanese search summary.
- knowledge.metadata.references: Include every knowledge source file used as evidence.
- knowledge.body: Keep the Markdown body short, preferably 10-30 lines.
- knowledge.body: Remove unsupported or stale claims instead of preserving them.
"""

    knowledge: KnowledgeFile


class KnowledgeImprovementResponse(StrictKnowledgeModel):
    """
    知識ファイル群の品質改善結果。
    """

    TGBT_OUTPUT_SCHEMA_PROMPT: ClassVar[str] = """\
Field rules:
- knowledge_files: Return the full replacement set of knowledge files to keep.
- Prefer fewer, shorter files when content overlaps.
- Remove claims not supported by the referenced knowledge source files.
- Keep each body short, preferably 10-30 lines.
"""

    knowledge_files: list[KnowledgeFile]


class KnowledgeCandidateSelectionResponse(StrictKnowledgeModel):
    """
    知識検索の候補選定結果。
    """

    TGBT_OUTPUT_SCHEMA_PROMPT: ClassVar[str] = """\
Field rules:
- knowledge_ids: Return at most 5 ids.
- Choose only knowledge files likely to help answer the question.
- Use only ids from the provided candidate list.
"""

    knowledge_ids: list[str]


class KnowledgeRelevanceResponse(StrictKnowledgeModel):
    """
    知識検索候補の関連判定結果。
    """

    TGBT_OUTPUT_SCHEMA_PROMPT: ClassVar[str] = """\
Field rules:
- relevant_knowledge_ids: Keep only knowledge files that are actually relevant.
- is_sufficient: Use true only if the relevant knowledge fully answers the question.
- missing_information: Explain what still needs investigation when insufficient.
"""

    relevant_knowledge_ids: list[str]
    is_sufficient: bool
    missing_information: str


class KnowledgeSourceFileSelectionResponse(StrictKnowledgeModel):
    """
    追加調査に使う知識ソースファイルの選定結果。
    """

    TGBT_OUTPUT_SCHEMA_PROMPT: ClassVar[str] = """\
Field rules:
- paths: Return at most 5 paths.
- Use only paths from the provided index.
- Select files that are likely to resolve the missing information.
"""

    paths: list[str]


class KnowledgeResearchResponse(StrictKnowledgeModel):
    """
    知識ソースファイル調査から作る新規知識。
    """

    TGBT_OUTPUT_SCHEMA_PROMPT: ClassVar[str] = """\
Field rules:
- knowledge.metadata.status: Use "valid".
- knowledge.metadata.summary: Write a short Japanese search summary.
- knowledge.metadata.references: Include every provided knowledge source file used.
- knowledge.body: Answer the missing information using only provided files.
- knowledge.body: Keep the Markdown body short, preferably 10-30 lines.
"""

    knowledge: KnowledgeFile


class KnowledgeAnswerResponse(StrictKnowledgeModel):
    """
    知識検索の最終回答。
    """

    TGBT_OUTPUT_SCHEMA_PROMPT: ClassVar[str] = """\
Field rules:
- answer: Answer the user's repository question in Japanese.
- related_paths: Include every knowledge source file path related to the answer.
- Do not include paths that were not used as evidence.
"""

    result: KnowledgeSearchResult
