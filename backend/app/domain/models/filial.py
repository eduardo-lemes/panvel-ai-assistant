from pydantic import BaseModel


class Filial(BaseModel):
    codigo_filial: str
    faixa_vida: str | None = None
    localidade: str
    uf: str
    tipo_estabelecimento: str | None = None
    delivery: bool | None = None
    metragem_area_venda: float | None = None
    panvel_clinic: bool | None = None
    estacionamento: bool | None = None
    atendimento_24_horas: bool | None = None
