from pathlib import Path

import pandas as pd

from app.application.services.filial_tools import buscar_filiais, detalhes_filial
from app.domain.models.tools import BuscarFiliaisInput, DetalhesFilialInput
from app.infrastructure.repositories.filiais import FilialRepository


def test_busca_filiais_applies_filters_and_limit(tmp_path: Path) -> None:
    repository = FilialRepository(_create_parquet_fixture(tmp_path))

    result = buscar_filiais(
        BuscarFiliaisInput(
            cidade="Curitiba",
            panvel_clinic=True,
            estacionamento=True,
            limite=1,
        ),
        repository,
    )

    assert result.error is None
    assert result.total_results == 1
    assert len(result.filiais) == 1
    assert result.filiais[0].localidade == "Curitiba"
    assert result.filiais[0].panvel_clinic is True
    assert result.filiais[0].estacionamento is True


def test_busca_filiais_returns_actionable_error_for_unknown_city(tmp_path: Path) -> None:
    repository = FilialRepository(_create_parquet_fixture(tmp_path))

    result = buscar_filiais(
        BuscarFiliaisInput(cidade="Maringa"),
        repository,
    )

    assert result.total_results == 0
    assert result.error is not None
    assert result.error.code == "city_not_found"
    assert "cidade valida" in (result.error.suggestion or "")


def test_busca_filiais_is_case_insensitive(tmp_path: Path) -> None:
    repository = FilialRepository(_create_parquet_fixture(tmp_path))

    # Test lowercase input against mixed-case repository data
    result = buscar_filiais(
        BuscarFiliaisInput(cidade="curitiba"),
        repository,
    )
    assert result.error is None
    assert result.total_results == 2


def test_busca_filiais_returns_actionable_error_for_empty_results(tmp_path: Path) -> None:
    repository = FilialRepository(_create_parquet_fixture(tmp_path))

    result = buscar_filiais(
        BuscarFiliaisInput(
            cidade="Curitiba",
            delivery=False,
            atendimento_24_horas=True,
        ),
        repository,
    )

    assert result.total_results == 0
    assert result.error is not None
    assert result.error.code == "no_results"


def test_detalhes_filial_returns_actionable_error_for_missing_code(tmp_path: Path) -> None:
    repository = FilialRepository(_create_parquet_fixture(tmp_path))

    result = detalhes_filial(
        DetalhesFilialInput(codigo_filial="999"),
        repository,
    )

    assert result.filial is None
    assert result.error is not None
    assert result.error.code == "filial_not_found"


def test_detalhes_filial_returns_filial_when_code_exists(tmp_path: Path) -> None:
    repository = FilialRepository(_create_parquet_fixture(tmp_path))

    result = detalhes_filial(
        DetalhesFilialInput(codigo_filial="102"),
        repository,
    )

    assert result.error is None
    assert result.filial is not None
    assert result.filial.codigo_filial == "102"
    assert result.filial.localidade == "Londrina"


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
