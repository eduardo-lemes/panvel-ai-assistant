import re
import json
from app.application.interfaces.llm import LLMProvider
from app.domain.models.llm import LLMCompletionResult, LLMUsage


class MockLLMProvider(LLMProvider):
    def __init__(self, model: str) -> None:
        self.model = model

    def complete(
        self,
        message: str,
        system_prompt: str,
        history: list[dict[str, str]] | None = None,
    ) -> LLMCompletionResult:
        if "=== CONTEXTO DAS BULAS ===" in system_prompt:
            # RAG mock response
            files = re.findall(r"Arquivo: ([a-zA-Z0-9__\-\.]+)", system_prompt)
            pages = re.findall(r"Página: (\d+)", system_prompt)
            if files:
                citations = []
                for f, p in zip(files[:2], pages[:2]):
                    citations.append(f"bula {f} (pág. {p})")
                text = f"Resposta RAG simulada para a pergunta: '{message}'. Com base na {', '.join(citations)}, a losartana serve para tratamento de hipertensão."
            else:
                text = f"Não encontrei informações suficientes no corpus de bulas para responder à pergunta: '{message}'."
                
        elif "=== RETORNO DA TOOL buscar_filiais ===" in system_prompt:
            # Buscar filiais mock response
            try:
                json_str = system_prompt.split("=== RETORNO DA TOOL buscar_filiais ===")[1].strip()
                data = json.loads(json_str)
                if data.get("error"):
                    err = data["error"]
                    text = f"Erro na busca de filiais: {err['message']}. Sugestão: {err.get('suggestion')}"
                else:
                    total = data.get("total_results", 0)
                    filiais = data.get("filiais", [])
                    filiais_list = ", ".join([f"filial {f['codigo_filial']} ({f['localidade']})" for f in filiais[:3]])
                    text = f"Encontrei {total} filiais para os filtros. Principais encontradas: {filiais_list}."
            except Exception:
                text = f"Busca de filiais executada com sucesso. Resultados encontrados no banco de dados."
                
        elif "=== RETORNO DA TOOL detalhes_filial ===" in system_prompt:
            # Detalhes filial mock response
            try:
                json_str = system_prompt.split("=== RETORNO DA TOOL detalhes_filial ===")[1].strip()
                data = json.loads(json_str)
                if data.get("error"):
                    err = data["error"]
                    text = f"Erro ao buscar detalhes da filial: {err['message']}."
                else:
                    filial = data.get("filial") or {}
                    text = f"Detalhes da filial {data['codigo_filial']}: Localizada em {filial.get('localidade')}-{filial.get('uf')}, " \
                           f"24h: {'Sim' if filial.get('atendimento_24_horas') else 'Não'}, " \
                           f"Clinic: {'Sim' if filial.get('panvel_clinic') else 'Não'}."
            except Exception:
                text = f"Detalhes da filial obtidos com sucesso."
        else:
            # General direct conversation
            text = f"Olá! Sou o assistente Panvel (Modo Mock). Recebi sua mensagem: '{message}'. Para ativar respostas reais do GPT/Gemini, configure uma chave de API válida no arquivo .env do projeto."

        input_tokens = len(message.split())
        output_tokens = len(text.split())
        return LLMCompletionResult(
            text=text,
            model=self.model,
            usage=LLMUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
            ),
        )
