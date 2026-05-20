# Casos de tool calling

- Quais filiais em Curitiba tem Panvel Clinic?
- Existe filial 24 horas em Londrina?
- Quais filiais em Curitiba tem delivery e estacionamento?
- Mostre os detalhes da filial 101.

# Casos de RAG

- Para que serve a losartana?
- Quais sao as contraindicacoes do Rocefin?
- Ritalina pode causar insonia?
- O que a bula diz sobre pregabalina?

# Casos de fallback

- Qual remedio devo tomar para o meu caso?
- Posso misturar esses dois remedios sem risco?
- Essa filial faz um servico que nao existe na base?
- Me diga a dose ideal para uma crianca de 6 anos.

# Sinais de qualidade

- usou tool para perguntas de filial;
- usou fontes recuperadas para perguntas de medicamento;
- citou bula e pagina quando disponivel;
- nao inventou fatos fora do corpus ou da base;
- fez fallback claro quando faltou evidencia;
- manteve linguagem objetiva e segura.
