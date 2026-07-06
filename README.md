# Dashboard FGTS Profissional V28

Versão consolidada com layout expandido ao máximo para direita e esquerda.

Ajustes desta versão:
- área útil do Streamlit expandida para 100% da tela;
- redução das margens laterais do container principal;
- manutenção do gráfico vertical por empresa com quantidade de colaboradores abaixo de cada barra;
- drill-down Empresa → Colaborador preservado;
- botão Voltar laranja preservado abaixo do gráfico;
- pesquisa por Nome / CPF / Matrícula preservada abaixo do gráfico;
- exportação Excel e execução via BAT preservadas.

## Como usar
1. Extraia o ZIP em um caminho curto, exemplo: `C:\FGTS_DASH`.
2. Execute `rodar_dashboard.bat`.
3. O navegador abrirá automaticamente em `http://localhost:8501`.


## V29
- Clique direto no gráfico vertical Empresa → Colaborador usando componente de evento Plotly.
- Mantém fallback compatível com Streamlit nativo.


Versão 31:
- Gráfico Empresa mantido obrigatoriamente em barras verticais.
- Clique no gráfico ajustado com seleção nativa do Streamlit.
- Removido componente externo que podia renderizar o gráfico na horizontal.


## Versão 35
- Card laranja renomeado para **FGTS MENSAL TOTAL**.
- Mantida a lógica de exibir valor filtrado por empresa ou total geral sem filtro.


## V41
- Corrigido o cálculo do card MÉDIA BASE FGTS / COLAB.: agora usa Base FGTS Total (mensal + 13º) / quantidade de colaboradores filtrados.
