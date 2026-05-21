from app.domain.models.tools import (
    BuscarFiliaisInput,
    BuscarFiliaisResult,
    DetalhesFilialInput,
    DetalhesFilialResult,
    ToolError,
)
from app.infrastructure.repositories.filiais import FilialRepository


def buscar_filiais(
    payload: BuscarFiliaisInput,
    repository: FilialRepository,
) -> BuscarFiliaisResult:
    available_cities = repository.list_available_cities()
    
    cidade_query = payload.cidade.strip().casefold() if payload.cidade else None
    available_cities_casefolded = [c.strip().casefold() for c in available_cities]

    if cidade_query and cidade_query not in available_cities_casefolded:
        return BuscarFiliaisResult(
            filters=payload,
            total_results=0,
            filiais=[],
            error=ToolError(
                code="city_not_found",
                message=f"Cidade '{payload.cidade}' nao encontrada na base de filiais do PR.",
                suggestion=_build_city_suggestion(available_cities),
            ),
        )

    filiais = repository.search(
        cidade=payload.cidade,
        delivery=payload.delivery,
        panvel_clinic=payload.panvel_clinic,
        estacionamento=payload.estacionamento,
        atendimento_24_horas=payload.atendimento_24_horas,
        tipo_estabelecimento=payload.tipo_estabelecimento,
        limite=payload.limite,
    )

    if not filiais:
        return BuscarFiliaisResult(
            filters=payload,
            total_results=0,
            filiais=[],
            error=ToolError(
                code="no_results",
                message="Nenhuma filial encontrada para os filtros informados.",
                suggestion="Revise cidade, servicos ou reduza a quantidade de filtros.",
            ),
        )

    return BuscarFiliaisResult(
        filters=payload,
        total_results=len(filiais),
        filiais=filiais,
    )


def detalhes_filial(
    payload: DetalhesFilialInput,
    repository: FilialRepository,
) -> DetalhesFilialResult:
    filial = repository.get_by_code(payload.codigo_filial)

    if filial is None:
        return DetalhesFilialResult(
            codigo_filial=payload.codigo_filial,
            error=ToolError(
                code="filial_not_found",
                message=f"Filial '{payload.codigo_filial}' nao encontrada.",
                suggestion="Use um codigo_filial existente retornado por buscar_filiais.",
            ),
        )

    return DetalhesFilialResult(
        codigo_filial=payload.codigo_filial,
        filial=filial,
    )


def _build_city_suggestion(available_cities: list[str]) -> str | None:
    if not available_cities:
        return None
    suggestions = ", ".join(available_cities[:5])
    return f"Use uma cidade valida da base, por exemplo: {suggestions}."
