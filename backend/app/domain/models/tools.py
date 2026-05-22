from pydantic import BaseModel, Field, field_validator

from app.domain.models.filial import Filial


class BuscarFiliaisInput(BaseModel):
    cidade: str | None = None
    delivery: bool | None = None
    panvel_clinic: bool | None = None
    estacionamento: bool | None = None
    atendimento_24_horas: bool | None = None
    tipo_estabelecimento: str | None = None
    limite: int = Field(default=10, ge=1, le=50)
    offset: int = Field(default=0, ge=0)

    @field_validator("cidade", "tipo_estabelecimento")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class DetalhesFilialInput(BaseModel):
    codigo_filial: str = Field(min_length=1)

    @field_validator("codigo_filial")
    @classmethod
    def strip_codigo_filial(cls, value: str) -> str:
        return value.strip()


class ToolError(BaseModel):
    code: str
    message: str
    suggestion: str | None = None


class BuscarFiliaisResult(BaseModel):
    tool_name: str = "buscar_filiais"
    filters: BuscarFiliaisInput
    total_results: int
    filiais: list[Filial]
    error: ToolError | None = None


class DetalhesFilialResult(BaseModel):
    tool_name: str = "detalhes_filial"
    codigo_filial: str
    filial: Filial | None = None
    error: ToolError | None = None
