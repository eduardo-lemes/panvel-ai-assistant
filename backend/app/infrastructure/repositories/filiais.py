from functools import lru_cache
from pathlib import Path

import pandas as pd

from app.domain.models.filial import Filial


YES_VALUES = {"sim", "s", "yes", "true", "1"}
NO_VALUES = {"nao", "n", "no", "false", "0"}


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

    def search(
        self,
        *,
        cidade: str | None = None,
        delivery: bool | None = None,
        panvel_clinic: bool | None = None,
        estacionamento: bool | None = None,
        atendimento_24_horas: bool | None = None,
        tipo_estabelecimento: str | None = None,
        limite: int = 10,
    ) -> list[Filial]:
        dataframe = self._load_dataframe().copy()

        if cidade:
            cidade_normalized = cidade.strip().casefold()
            dataframe = dataframe.loc[
                dataframe["localidade"]
                .astype(str)
                .map(str.strip)
                .map(str.casefold)
                == cidade_normalized
            ]

        if tipo_estabelecimento:
            tipo_normalized = tipo_estabelecimento.strip().casefold()
            dataframe = dataframe.loc[
                dataframe["tipo_estabelecimento"]
                .astype(str)
                .map(str.strip)
                .map(str.casefold)
                == tipo_normalized
            ]

        dataframe = _filter_yes_no_column(dataframe, "delivery", delivery)
        dataframe = _filter_yes_no_column(dataframe, "panvel_clinic", panvel_clinic)
        dataframe = _filter_yes_no_column(dataframe, "estacionamento", estacionamento)
        dataframe = _filter_yes_no_column(
            dataframe,
            "atendimento_24_horas",
            atendimento_24_horas,
        )

        records = dataframe.head(limite).to_dict(orient="records")
        return [_row_to_filial(record) for record in records]


def build_default_filial_repository() -> FilialRepository:
    base_paths = [
        Path(__file__).resolve().parents[4] / "data" / "filiais.parquet",  # Local Windows
        Path(__file__).resolve().parents[3] / "data" / "filiais.parquet",  # Local dev/Docker from root or /app/
        Path("/app/data/filiais.parquet"),                                # Docker absolute mount
        Path("/data/filiais.parquet"),                                    # Fallback root mount
    ]
    data_path = next((p for p in base_paths if p.exists()), base_paths[0])
    return FilialRepository(parquet_path=data_path)


def normalize_yes_no(value: object) -> bool | None:
    if value is None or pd.isna(value):
        return None

    normalized_value = str(value).strip().lower()
    normalized_value = normalized_value.replace("ã", "a").replace("õ", "o")
    if normalized_value in YES_VALUES:
        return True
    if normalized_value in NO_VALUES:
        return False
    return None


def _filter_yes_no_column(
    dataframe: pd.DataFrame,
    column_name: str,
    expected_value: bool | None,
) -> pd.DataFrame:
    if expected_value is None:
        return dataframe

    normalized_column = dataframe[column_name].map(normalize_yes_no)
    return dataframe.loc[normalized_column == expected_value]


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
