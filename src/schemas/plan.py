from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OriginalInstruction(StrictModel):
    """
    人間から与えられた指示文
    """

    text: str


class CompletionCriterion(StrictModel):
    """
    計画を完了とする条件
    """

    id: str  # e.g. "COMP-001"
    text: str


class RiskNote(StrictModel):
    """
    計画のリスク要素
    """

    id: str  # e.g. "RISK-001"
    text: str


class PlannedProcedure(StrictModel):
    """
    計画の構成手順
    """

    id: str  # e.g. "PROC-001"
    text: str


class Assumption(StrictModel):
    """
    計画を立てるにあたって用いた仮定。
    人間の指示が無い隙間については AI による仮定を置いても良いとしている。
    """

    id: str  # e.g. "ASMP-001"
    text: str


class TgbtPlan(StrictModel):
    """
    `tgbt run` の実行対象となる「計画」
    この構造化された計画情報が正本である
    """

    schema_version: str
    original_instructions: list[OriginalInstruction]
    completion_criteria: list[CompletionCriterion]
    risk_notes: list[RiskNote]
    planned_procedures: list[PlannedProcedure]
    assumptions: list[Assumption]
    self_check_notes: list[str]
