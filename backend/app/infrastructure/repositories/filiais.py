from functools import lru_cache
from pathlib import Path

import pandas as pd

from app.domain.models.filial import Filial


YES_VALUES = {"sim", "s", "yes", "true", "1"}
NO_VALUES = {"nao", "não", "n", "no", "false", "0"}


class FilialRepository:
    def __init__(self, parquet_path: Path) -> None:
        self.parquet_path = parquet_path

    @lru_cache(maxsize=1)
    def _load_dataframe(self) -> pd.DataFrame:
        dataframe = pd.read_parquet(self.parquet_path)
        dataframe["codigo_filial"] = dataframe["codigo_filial"].astype(str)
        return dataframe

    def list_available_cities(self) -> list[str]:
        dataframe = self._load_dataframe()
        cities = (
            dataframe["localidade"]
            .dropna()
            .astype(str)
            .map(str.strip)
            .loc[lambda items: items != ""]
            .sort_values()
            .unique()
        )
        return cities.tolist()

    def get_by_code(self, codigo_filial: str) -> Filial | None:
        normalized_code = str(codigo_filial).strip()
        dataframe = self._load_dataframe()
        matches = dataframe.loc[dataframe["codigo_filial"] == normalized_code]
        if matches.empty:
            return None
        return _row_to_filial(matches.iloc[0].to_dict())


def build_default_filial_repository() -> FilialRepository:
    data_path = Path(__file__).resolve().parents[4] / "data" / "filiais.parquet"
    return FilialRepository(parquet_path=data_path)


def normalize_yes_no(value: object) -> bool | None:
    if value is None or pd.isna(value):
        return None

    normalized_value = str(value).strip().lower()
    if normalized_value in YES_VALUES:
        return True
    if normalized_value in NO_VALUES:
        return False
    return None


def _optional_str(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    normalized_value = str(value).strip()
    return normalized_value or None


def _optional_float(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _row_to_filial(row: dict[str, object]) -> Filial:
    return Filial(
        codigo_filial=str(row["codigo_filial"]).strip(),
        faixa_vida=_optional_str(row.get("faixa_vida")),
        localidade=str(row["localidade"]).strip(),
        uf=str(row["uf"]).strip(),
        tipo_estabelecimento=_optional_str(row.get("tipo_estabelecimento")),
        delivery=normalize_yes_no(row.get("delivery")),
        metragem_area_venda=_optional_float(row.get("metragem_area_venda")),
        panvel_clinic=normalize_yes_no(row.get("panvel_clinic")),
        estacionamento=normalize_yes_no(row.get("estacionamento")),
        atendimento_24_horas=normalize_yes_no(row.get("atendimento_24_horas")),
    )
