from pathlib import Path

import pandas as pd

from app.infrastructure.repositories.filiais import (
    FilialRepository,
    normalize_yes_no,
)


def test_normalize_yes_no_handles_expected_values() -> None:
    assert normalize_yes_no("SIM") is True
    assert normalize_yes_no("Não") is False
    assert normalize_yes_no("NAO") is False
    assert normalize_yes_no(None) is None
    assert normalize_yes_no("desconhecido") is None


def test_list_available_cities_returns_sorted_unique_values(tmp_path: Path) -> None:
    repository = FilialRepository(_create_parquet_fixture(tmp_path))

    cities = repository.list_available_cities()

    assert cities == ["Curitiba", "Londrina"]


def test_get_by_code_returns_normalized_filial(tmp_path: Path) -> None:
    repository = FilialRepository(_create_parquet_fixture(tmp_path))

    filial = repository.get_by_code("101")

    assert filial is not None
    assert filial.codigo_filial == "101"
    assert filial.localidade == "Curitiba"
    assert filial.delivery is True
    assert filial.panvel_clinic is False
    assert filial.estacionamento is True
    assert filial.atendimento_24_horas is False


def test_get_by_code_returns_none_for_missing_filial(tmp_path: Path) -> None:
    repository = FilialRepository(_create_parquet_fixture(tmp_path))

    filial = repository.get_by_code("999")

    assert filial is None


def test_search_returns_tuple_with_results_and_total_count(tmp_path: Path) -> None:
    repository = FilialRepository(_create_parquet_fixture(tmp_path))

    filiais, total = repository.search(cidade="Curitiba")

    assert total == 2
    assert len(filiais) == 2
    assert filiais[0].localidade == "Curitiba"
    assert filiais[1].localidade == "Curitiba"


def test_search_supports_offset_pagination(tmp_path: Path) -> None:
    repository = FilialRepository(_create_parquet_fixture(tmp_path))

    # Curitiba has 2 filiais: 101 and 103.
    # Page 1 (limite 1, offset 0)
    filiais_p1, total_p1 = repository.search(cidade="Curitiba", limite=1, offset=0)
    assert total_p1 == 2
    assert len(filiais_p1) == 1
    assert filiais_p1[0].codigo_filial == "101"

    # Page 2 (limite 1, offset 1)
    filiais_p2, total_p2 = repository.search(cidade="Curitiba", limite=1, offset=1)
    assert total_p2 == 2
    assert len(filiais_p2) == 1
    assert filiais_p2[0].codigo_filial == "103"

    # Page 3 (limite 1, offset 2)
    filiais_p3, total_p3 = repository.search(cidade="Curitiba", limite=1, offset=2)
    assert total_p3 == 2
    assert len(filiais_p3) == 0


def _create_parquet_fixture(tmp_path: Path) -> Path:
    dataframe = pd.DataFrame(
        [
            {
                "codigo_filial": 101,
                "faixa_vida": "5-10 anos",
                "localidade": "Curitiba",
                "uf": "PR",
                "tipo_estabelecimento": "CENTRO",
                "delivery": "SIM",
                "metragem_area_venda": 123.5,
                "panvel_clinic": "NAO",
                "estacionamento": "SIM",
                "atendimento_24_horas": "NAO",
            },
            {
                "codigo_filial": 102,
                "faixa_vida": "0-5 anos",
                "localidade": "Londrina",
                "uf": "PR",
                "tipo_estabelecimento": "BAIRRO",
                "delivery": "NAO",
                "metragem_area_venda": 98.0,
                "panvel_clinic": "SIM",
                "estacionamento": "NAO",
                "atendimento_24_horas": "SIM",
            },
            {
                "codigo_filial": 103,
                "faixa_vida": "10+ anos",
                "localidade": "Curitiba",
                "uf": "PR",
                "tipo_estabelecimento": "BAIRRO",
                "delivery": "SIM",
                "metragem_area_venda": 150.0,
                "panvel_clinic": "SIM",
                "estacionamento": "SIM",
                "atendimento_24_horas": "SIM",
            },
        ]
    )
    parquet_path = tmp_path / "filiais.parquet"
    dataframe.to_parquet(parquet_path, index=False)
    return parquet_path
