from __future__ import annotations

import io
import base64
import html
import re
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from tratar_fgts_plan1 import parse_plan1, gerar_resumos

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
LOGO_PATH = ASSETS_DIR / "logo_equatorial.png"
DATA_DIR = BASE_DIR / "data"
IMPORT_DIR = DATA_DIR / "importados"
COLAB_CSV = DATA_DIR / "base_fgts_colaboradores.csv"
TOTAIS_CSV = DATA_DIR / "base_fgts_totais.csv"
RESUMO_EMPRESA_CSV = DATA_DIR / "base_fgts_resumo_empresa.csv"
RESUMO_FILIAL_CSV = DATA_DIR / "base_fgts_resumo_filial.csv"
RETORNO_ESOCIAL_CSV = DATA_DIR / "base_esocial_retorno_s5003.csv"

# DE/PARA para nomes curtos das empresas no dashboard.
# Mantém o nome completo em "empresa_nome_original" para referência interna/tooltip.
DE_PARA_EMPRESAS = {
    "E-NOVA GERACAO DISTRIBUIDA S.A": "ENOVA",
    "ECHOENERGIA PARTICIPACOES S.A.": "PARTICIPACOES",
    "VENTOS DE SAO CLEMENTE VII ENERGIAS REIN": "VENTOS DE SAO CLEMENTE VII",
    "NOVA VENTOS DE TIANGUA NORTE ENERGIAS RE": "NOVA VENTOS DE TIANGUA",
    "ECHOENERGIA SUPRIMENTOS E EMPREENDIMENTO": "SUPRIMENTOS",
    "EOLICA PEDRA DO REINO S.A.": "PEDRA DO REINO",
    "EOLICA BAIXA VERDE S.A": "BAIXA VERDE",
    "EOLICA SERIDO S.A.": "SERIDO",
    "EOLICA LAGOA NOVA S.A.": "LAGOA NOVA",
    "VILA RIO GRANDE DO NORTE 2 EMPREENDIMENT": "VL RIO G. DO NORTE II",
    "SERTAO SOLAR BARREIRAS XVII S.A.": "SERTAO SOLAR BARREIRAS XVII",
    "EQUATORIAL RENOVAVEIS SA": "RENOVAVEIS",
    "RIBEIRO GONCALVES SOLAR III SA": "RIB. GONCALVES SOLAR III",
}


def empresa_nome_curto(nome: object) -> str:
    nome_limpo = str(nome).strip()
    return DE_PARA_EMPRESAS.get(nome_limpo.upper(), nome_limpo)


st.set_page_config(
    page_title="Dashboard FGTS | DP Multiempresa",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =============================
# CSS - padrão executivo azul
# =============================
st.markdown(
    """
<style>
:root{
    --bg:#061b33;
    --panel:#082846;
    --panel2:#0b335a;
    --cyan:#12b7ff;
    --green:#00b050;
    --orange:#f28c28;
    --purple:#7b3fb5;
    --text:#f2f7ff;
    --muted:#b8c8d9;
    --border:#1f6a95;
}
.stApp {
    background: radial-gradient(circle at top left, #0b3b63 0, #061b33 38%, #041326 100%) !important;
    color: var(--text);
}
/* Remove a barra branca superior padrão do Streamlit */
header[data-testid="stHeader"]{ display:none !important; height:0 !important; }
[data-testid="stToolbar"]{ display:none !important; visibility:hidden !important; }
[data-testid="stDecoration"]{ display:none !important; height:0 !important; }
[data-testid="stStatusWidget"]{ display:none !important; visibility:hidden !important; }
#MainMenu{ visibility:hidden !important; }
footer{ visibility:hidden !important; height:0 !important; }
[data-testid="stAppViewContainer"]{ background: radial-gradient(circle at top left, #0b3b63 0, #061b33 38%, #041326 100%) !important; }
.block-container{ padding-top: 1rem !important; padding-bottom: 1.5rem; padding-left:.25rem !important; padding-right:.25rem !important; max-width:none !important; width:100% !important; }
[data-testid="stAppViewContainer"] > .main{ width:100% !important; }
[data-testid="stSidebar"]{ display:none; }
/* Expansão máxima da área útil do dashboard */
[data-testid="stVerticalBlock"]{ width:100% !important; }
[data-testid="stVerticalBlockBorderWrapper"]{ width:100% !important; }
.element-container{ width:100% !important; }

.header-box{
    background: linear-gradient(90deg, #09213e 0%, #083d6b 52%, #074b72 100%);
    border:1px solid var(--border);
    border-radius:14px;
    padding:16px 22px;
    box-shadow: 0 8px 22px rgba(0,0,0,.30);
    margin-bottom:12px;
}
.header-title{ font-size:42px; font-weight:900; letter-spacing:.5px; line-height:1; }
.header-subtitle{ font-size:18px; font-weight:700; color:#dceeff; margin-top:2px; }
.header-small{ color:#d4e8f7; font-size:13px; text-transform:uppercase; font-weight:700; }
.header-value{ color:#ffffff; font-size:22px; font-weight:800; }

.header-hero{
    display:grid;
    grid-template-columns: 170px 1.35fr repeat(4, minmax(135px, 0.8fr));
    align-items:stretch;
    background:linear-gradient(90deg,#082543 0%, #09335b 28%, #072b4c 100%);
    border:1px solid rgba(82,191,255,.20);
    border-radius:16px;
    overflow:hidden;
    box-shadow:0 10px 24px rgba(0,0,0,.28);
    margin-bottom:12px;
}
.header-hero-box{
    min-height:92px;
    padding:14px 18px;
    display:flex;
    align-items:center;
    gap:12px;
    border-right:1px solid rgba(255,255,255,.08);
    box-sizing:border-box;
}
.header-hero-box:last-child{border-right:none;}
.header-hero-logo{justify-content:center; background:linear-gradient(180deg,rgba(255,255,255,.03),rgba(255,255,255,.01));}
.header-hero-logo img{max-width:132px; max-height:58px; width:auto; height:auto; display:block; filter:brightness(0) invert(1); opacity:.95;}
.header-hero-title{display:flex; flex-direction:column; justify-content:center;}
.header-hero-main{font-size:28px; line-height:1; font-weight:900; color:#eaf5ff; letter-spacing:.6px; margin:0 0 4px 0;}
.header-hero-sub{font-size:12px; line-height:1.2; font-weight:700; text-transform:uppercase; color:#d8ecff; margin:0;}
.header-hero-stat-icon{font-size:28px; line-height:1; min-width:32px; text-align:center; opacity:.95;}
.header-hero-stat-text{display:flex; flex-direction:column; justify-content:center; min-width:0;}
.header-hero-stat-value{font-size:14px; font-weight:900; color:#ffffff; line-height:1.1; margin-top:2px; white-space:nowrap;}
.header-hero-stat-label{font-size:11px; font-weight:700; color:#d7e9f9; text-transform:none; line-height:1.1;}
@media (max-width: 1180px){
  .header-hero{grid-template-columns: 1fr 1fr; }
  .header-hero-box{min-height:78px;}
}
@media (max-width: 760px){
  .header-hero{grid-template-columns: 1fr;}
}

.kpi-grid{
    display:grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap:16px;
    width:100%;
    margin: 0 0 12px 0;
}
.kpi-card{
    border-radius:14px;
    padding:14px 16px;
    border:1px solid rgba(255,255,255,.12);
    height:132px;
    min-height:132px;
    box-shadow:0 8px 20px rgba(0,0,0,.24);
    box-sizing:border-box;
    display:flex;
    flex-direction:column;
    justify-content:space-between;
    overflow:hidden;
}
.kpi-title{
    font-size:11.5px;
    line-height:1.25;
    font-weight:900;
    text-transform:uppercase;
    color:#f3f8ff;
    margin:0;
}
.kpi-value{
    font-size:clamp(18px, 1.45vw, 24px);
    line-height:1.15;
    font-weight:900;
    color:#fff;
    margin:0;
    white-space:nowrap;
    letter-spacing:-.3px;
}
.kpi-foot{
    font-size:12px;
    line-height:1.25;
    color:#e3edf7;
    margin:0;
}
@media (max-width: 1250px){
  .kpi-grid{grid-template-columns: repeat(3, minmax(0, 1fr));}
}
@media (max-width: 760px){
  .kpi-grid{grid-template-columns: repeat(1, minmax(0, 1fr));}
}
.kpi-blue{background:linear-gradient(135deg,#064b88,#0874aa);}
.kpi-green{background:linear-gradient(135deg,#006b2e,#039845);}
.kpi-purple{background:linear-gradient(135deg,#42227d,#6f3aa7);}
.kpi-orange{background:linear-gradient(135deg,#a85200,#ec8700);}
.kpi-cyan{background:linear-gradient(135deg,#075f86,#0583ad);}
.panel{
    background: linear-gradient(180deg, rgba(9,47,82,.96), rgba(5,30,55,.96));
    border:1px solid var(--border); border-radius:12px; padding:14px 15px;
    box-shadow: 0 8px 20px rgba(0,0,0,.22); margin-bottom:12px;
}
.filter-panel{
    background: linear-gradient(90deg, rgba(8,40,70,.98), rgba(7,67,103,.95));
    border:1px solid var(--border); border-radius:12px; padding:12px 14px;
    box-shadow: 0 8px 20px rgba(0,0,0,.22); margin-bottom:12px;
}
.panel-title{font-weight:900; font-size:17px; margin-bottom:8px; color:#ffffff; text-transform:uppercase;}
.stDataFrame{border:1px solid var(--border); border-radius:10px; overflow:hidden;}

/* Tabela de detalhamento: apenas o cabeçalho fica branco; linhas transparentes */
.clean-detail-wrap{
    border:1px solid var(--border);
    border-radius:10px;
    overflow-y:auto;
    overflow-x:auto;
    background:transparent !important;
    margin-top:8px;
    width:100%;
}
.clean-detail-table{
    width:max-content;
    min-width:100% !important;
    max-width:none !important;
    table-layout:auto;
    border-collapse:collapse;
    background:transparent !important;
    color:#f2f7ff !important;
    font-size:10.5px;
    line-height:1.15;
}
.clean-detail-table thead th{
    position:sticky;
    top:0;
    z-index:2;
    background:#ffffff !important;
    color:#243041 !important;
    text-align:left;
    font-weight:800;
    padding:7px 6px;
    border-right:1px solid #d8dee6;
    border-bottom:1px solid #c7d0da;
    white-space:normal;
    overflow-wrap:anywhere;
    word-break:normal;
}
.clean-detail-table tbody tr,
.clean-detail-table tbody td{
    background:transparent !important;
}
.clean-detail-table tbody td{
    color:#f2f7ff !important;
    padding:7px 6px;
    border-right:1px solid rgba(255,255,255,.12);
    border-bottom:1px solid rgba(255,255,255,.10);
    white-space:normal;
    overflow-wrap:anywhere;
    word-break:normal;
}
.clean-detail-table tbody tr:hover td{
    background:rgba(18,183,255,.08) !important;
}
.clean-detail-table td.num{
    text-align:right;
    white-space:nowrap !important;
    overflow-wrap:normal !important;
    word-break:keep-all !important;
    font-size:10px;
    min-width:72px;
}
.clean-detail-table th.num{
    text-align:right;
    white-space:normal;
    font-size:9.5px;
    min-width:72px;
}
.clean-detail-table tfoot td{
    background:rgba(242,140,40,.18) !important;
    color:#ffffff !important;
    font-weight:900;
    padding:8px 6px;
    border-top:2px solid #f28c28;
    border-right:1px solid rgba(255,255,255,.16);
    white-space:nowrap !important;
}
.clean-detail-table tfoot td.num{
    text-align:right;
    white-space:nowrap !important;
    overflow-wrap:normal !important;
    word-break:keep-all !important;
}

button[kind="primary"]{background:#0b74b7!important; border:1px solid #52bfff!important;}
.stButton > button{background:#0b3158; color:#fff; border:1px solid #2d8fc7; border-radius:8px;}
hr{border-color:#1c5e86; margin: .7rem 0;}
.footer-note{font-size:12px;color:#c8d8e8;text-align:center;margin-top:10px;}
label, .stMarkdown, .stTextInput, .stSelectbox, .stSlider { color: #f2f7ff !important; }
/* Campo de pesquisa com cor sólida clara, sem degradê */
div[data-testid="stTextInput"] input{
    background:#eef2f6 !important;
    background-image:none !important;
    color:#102033 !important;
    border:1px solid #cbd5df !important;
    border-radius:8px !important;
    box-shadow:none !important;
    caret-color:#102033 !important;
}
div[data-testid="stTextInput"] input:focus{
    background:#ffffff !important;
    border:1px solid #8fb3cf !important;
    box-shadow:0 0 0 1px #8fb3cf !important;
}
div[data-testid="stTextInput"] input::placeholder{
    color:#667789 !important;
}
[data-testid="stMetricValue"], [data-testid="stMetricLabel"] { color: white !important; }
[data-testid="stVerticalBlockBorderWrapper"]{
    background: linear-gradient(180deg, rgba(9,47,82,.96), rgba(5,30,55,.96)) !important;
    border:1px solid var(--border) !important;
    border-radius:12px !important;
    box-shadow: 0 8px 20px rgba(0,0,0,.22) !important;
}
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"]{ gap:.45rem !important; }
.section-title{font-weight:900; font-size:17px; margin-bottom:2px; color:#ffffff; text-transform:uppercase;}
.legend-table{width:100%; border-collapse:collapse; color:#fff !important; font-size:12px; background:transparent !important; table-layout:auto;}
.legend-table *{color:#fff !important;}
.legend-table .color-swatch, .donut-legend-grid .color-swatch{color:inherit !important;}
.legend-table th, .legend-table td{background:transparent !important;}
.legend-table th{color:#eaf6ff; text-align:left; padding:7px 6px; border-bottom:1px solid rgba(255,255,255,.18); font-size:11px; text-transform:uppercase;}
.legend-table td{padding:8px 8px; border-bottom:1px solid rgba(255,255,255,.10); vertical-align:middle; white-space:nowrap;}
.legend-table td:first-child{min-width:420px;}
.legend-dot{display:inline-block; width:12px; height:12px; border-radius:3px; margin-right:8px; vertical-align:middle;}
.chart-help{font-size:12px;color:#b8c8d9;margin-top:-4px;margin-bottom:8px;}

.legend-table-full{border:1px solid rgba(255,255,255,.16); font-size:13px;}
.legend-table-full th{padding:14px 18px; color:#9bd8ff !important; font-size:12px; border-bottom:1px solid rgba(255,255,255,.18);}
.legend-table-full td{padding:12px 18px; border-bottom:1px solid rgba(255,255,255,.12);}
.legend-table-full td:first-child{min-width:520px;}
.legend-dot-big{display:inline-block; width:18px; min-width:18px; height:18px; margin-right:14px; vertical-align:middle; border-radius:5px; box-shadow:0 0 10px rgba(18,183,255,.35); border:1px solid rgba(255,255,255,.25);}
.legend-total-row td{color:#12b7ff !important; font-size:15px; font-weight:900 !important; border-top:1px solid rgba(18,183,255,.45); border-bottom:0; padding-top:16px;}
.donut-legend-grid{display:grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap:13px 28px; padding:0 4px 8px 18px; color:#fff; font-size:12.5px;}
.donut-legend-item{display:flex; align-items:center; min-width:0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.donut-legend-item span:last-child{overflow:hidden; text-overflow:ellipsis;}
@media (max-width: 1100px){.donut-legend-grid{grid-template-columns:1fr}.legend-table-full td:first-child{min-width:260px;}}
.drill-box{background:linear-gradient(90deg, rgba(9,47,82,.96), rgba(6,32,59,.96)); border:1px solid var(--border); border-radius:14px; padding:14px 16px; margin-bottom:12px;}
.drill-title{font-size:18px; font-weight:900; color:#fff; text-transform:uppercase;}
.drill-subtitle{font-size:12px; color:#b8d6ee;}
.drill-highlight{color:#f28c28; font-weight:900;}
.status-ok{color:#7CFC9A;font-weight:900;}
.status-div{color:#ffcf66;font-weight:900;}
.status-err{color:#ff8a8a;font-weight:900;}
.conc-note{font-size:12px;color:#c8d8e8;margin-top:-4px;margin-bottom:8px;}
.stDownloadButton > button{background:#0874aa!important; color:#fff!important; border:1px solid #52bfff!important; border-radius:8px!important;}

/* Botão voltar do drill-down */

/* Uploader: remove o fundo branco do bloco e mantém o botão destacado */
div[data-testid="stFileUploaderDropzone"]{
    background:rgba(8,40,70,.96) !important;
    background-image:none !important;
    border:1px dashed #2d8fc7 !important;
    border-radius:10px !important;
    box-shadow:none !important;
}
div[data-testid="stFileUploaderDropzone"] section,
div[data-testid="stFileUploaderDropzone"] div{
    background:transparent !important;
}
div[data-testid="stFileUploaderDropzone"] span,
div[data-testid="stFileUploaderDropzone"] small,
div[data-testid="stFileUploaderDropzone"] p{
    color:#dceeff !important;
}
div[data-testid="stFileUploaderDropzone"] button,
div[data-testid="stFileUploaderDropzone"] button[disabled]{
    color:#ffffff !important;
    -webkit-text-fill-color:#ffffff !important;
    background:#d62828 !important;
    background-image:none !important;
    border:1px solid #ff6b6b !important;
    border-radius:10px !important;
    box-shadow:0 2px 8px rgba(0,0,0,.18) !important;
    opacity:1 !important;
}
div[data-testid="stFileUploaderDropzone"] button:hover{
    background:#bb1f1f !important;
    border-color:#ff8a8a !important;
}

/* Remove definitivamente o fundo claro interno do uploader */
div[data-testid="stFileUploader"]{
    background:transparent !important;
}
div[data-testid="stFileUploader"] section,
div[data-testid="stFileUploader"] section *:not(button):not(svg):not(path){
    background:transparent !important;
    background-color:transparent !important;
}
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"]{
    background:#082846 !important;
    background-color:#082846 !important;
    border:1px dashed #2d8fc7 !important;
}
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzoneInstructions"]{
    background:transparent !important;
    background-color:transparent !important;
    color:#dceeff !important;
}
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzoneInstructions"] *{
    background:transparent !important;
    background-color:transparent !important;
    color:#dceeff !important;
}
div[data-testid="stFileUploader"] small{
    color:#dceeff !important;
}
div[data-testid="stFileUploader"] button,
div[data-testid="stFileUploader"] button[disabled]{
    background:#d62828 !important;
    background-color:#d62828 !important;
    color:#ffffff !important;
    -webkit-text-fill-color:#ffffff !important;
    border:1px solid #ff6b6b !important;
    opacity:1 !important;
}
div[data-testid="stFileUploader"] button:hover{
    background:#bb1f1f !important;
    background-color:#bb1f1f !important;
}

/* Arquivo carregado no uploader: deixa nome e tamanho legíveis */
div[data-testid="stFileUploaderFile"]{
    background:rgba(8,40,70,.96) !important;
    background-color:rgba(8,40,70,.96) !important;
    border:1px solid rgba(45,143,199,.55) !important;
    border-radius:10px !important;
}
div[data-testid="stFileUploaderFile"] *{
    color:#ffffff !important;
    -webkit-text-fill-color:#ffffff !important;
}
div[data-testid="stFileUploaderFileName"],
div[data-testid="stFileUploaderFileSize"]{
    color:#ffffff !important;
    -webkit-text-fill-color:#ffffff !important;
    font-weight:700 !important;
}
div[data-testid="stFileUploaderFile"] button,
div[data-testid="stFileUploaderFile"] button:hover{
    background:#d62828 !important;
    background-color:#d62828 !important;
    color:#ffffff !important;
    -webkit-text-fill-color:#ffffff !important;
    border:1px solid #ff6b6b !important;
}

div[data-testid="stButton"] button[kind="primary"]{
    background:#f28c28 !important;
    color:#ffffff !important;
    border:1px solid #ffb067 !important;
    border-radius:8px !important;
    font-weight:800 !important;
    box-shadow:0 8px 18px rgba(0,0,0,.22) !important;
}
</style>
""",
    unsafe_allow_html=True,
)

def image_file_to_data_uri(path: Path) -> str:
    try:
        ext = path.suffix.lower().replace('.', '') or 'png'
        data = base64.b64encode(path.read_bytes()).decode('utf-8')
        return f"data:image/{ext};base64,{data}"
    except Exception:
        return ""


# =============================
# Funções utilitárias
# =============================



def render_clean_table(df_show: pd.DataFrame, height: int = 390) -> None:
    """Renderiza tabela HTML com cabeçalho branco, linhas sem preenchimento e totalizador final."""
    numeric_like = {
        "Filial", "Cadastro", "Matrícula",
        "Base FGTS", "Base FGTS Mensal", "FGTS Mensal", "FGTS 13º", "FGTS Consolidado",
        "Adic. 0,5%", "Adic. 0,5% Mensal", "Base FGTS 13º", "Adic. 0,5% 13º",
        "Base Senior Mensal", "Base eSocial Mensal", "Dif. Base Mensal",
        "FGTS Senior Mensal", "FGTS eSocial Mensal", "Dif. FGTS Mensal",
        "Base Senior 13º", "Base eSocial 13º", "Dif. Base 13º",
        "FGTS Senior 13º", "FGTS eSocial 13º", "Dif. FGTS 13º",
        "Base eSocial Outros", "FGTS eSocial Outros"
    }
    totalizable_cols = [col for col in df_show.columns if _is_totalizable_value_column(col)]

    header_cells = []
    for col in df_show.columns:
        cls = " class='num'" if col in numeric_like or col in totalizable_cols else ""
        header_cells.append(f"<th{cls}>{html.escape(str(col))}</th>")

    col_widths = {
        "Status": "58px",
        "Empresa": "130px",
        "Cadastro": "72px",
        "Matrícula": "72px",
        "Colaborador": "260px",
        "CPF": "115px",
        "Base FGTS Mensal": "95px",
        "Base FGTS": "95px",
        "FGTS Mensal": "85px",
        "Base FGTS 13º": "95px",
        "FGTS 13º": "80px",
        "FGTS Consolidado": "105px",
        "Base Senior Mensal": "92px",
        "Base eSocial Mensal": "92px",
        "Dif. Base Mensal": "88px",
        "FGTS Senior Mensal": "92px",
        "FGTS eSocial Mensal": "92px",
        "Dif. FGTS Mensal": "88px",
        "Base Senior 13º": "88px",
        "Base eSocial 13º": "88px",
        "Dif. Base 13º": "84px",
        "FGTS Senior 13º": "88px",
        "FGTS eSocial 13º": "88px",
        "Dif. FGTS 13º": "84px",
        "Base eSocial Outros": "92px",
        "FGTS eSocial Outros": "92px",
        "Descrição tipos eSocial": "135px",
        "Observação": "220px",
    }
    colgroup = "".join(
        f"<col style='width:{col_widths.get(str(col), '90px')}'>"
        for col in df_show.columns
    )

    rows = []
    for _, row in df_show.iterrows():
        cells = []
        for col, val in row.items():
            cls = " class='num'" if col in numeric_like or col in totalizable_cols else ""
            cells.append(f"<td{cls}>{html.escape(str(val))}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")

    tfoot_html = ""
    if totalizable_cols and not df_show.empty:
        total_cells = []
        label_written = False
        for col in df_show.columns:
            if col in totalizable_cols:
                total_val = sum(_parse_br_money_value(v) for v in df_show[col].tolist())
                has_currency = any(str(v).strip().startswith("R$") for v in df_show[col].tolist())
                formatted = br_money(total_val) if has_currency else br_money(total_val).replace("R$ ", "")
                total_cells.append(f"<td class='num'>{html.escape(formatted)}</td>")
            else:
                if not label_written:
                    total_cells.append("<td>TOTAL</td>")
                    label_written = True
                else:
                    total_cells.append("<td></td>")
        tfoot_html = "<tfoot><tr>" + "".join(total_cells) + "</tr></tfoot>"

    table_html = (
        f"<div class='clean-detail-wrap' style='max-height:{height}px;'>"
        "<table class='clean-detail-table'>"
        "<colgroup>" + colgroup + "</colgroup>"
        "<thead><tr>" + "".join(header_cells) + "</tr></thead>"
        "<tbody>" + "".join(rows) + "</tbody>"
        + tfoot_html +
        "</table></div>"
    )
    st.markdown(table_html, unsafe_allow_html=True)


def br_money(v: float) -> str:
    try:
        return "R$ " + f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def br_number(v: float, decimals: int = 0) -> str:
    return f"{float(v):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _is_totalizable_value_column(col: object) -> bool:
    nome = str(col).strip().lower()
    if nome in {"filial", "cadastro", "matrícula", "matricula", "cpf", "empresa", "colaborador", "status"}:
        return False
    # Colunas financeiras do dashboard/conciliação.
    palavras_valor = ("base", "fgts", "valor", "adic", "dissídio", "dissidio", "consolidado", "mensal", "13º")
    return any(p in nome for p in palavras_valor)


def _parse_br_money_value(value: object) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    txt = str(value).strip()
    if not txt:
        return 0.0
    txt = re.sub(r"[^0-9,\.\-]", "", txt)
    if not txt or txt in {"-", ",", "."}:
        return 0.0
    try:
        if "," in txt:
            txt = txt.replace(".", "").replace(",", ".")
        return float(txt)
    except Exception:
        return 0.0


def _df_com_totalizador(df_export: pd.DataFrame) -> pd.DataFrame:
    """Adiciona linha TOTAL nas abas exportadas quando houver colunas de valores."""
    if df_export is None or df_export.empty:
        return df_export
    total_cols = [col for col in df_export.columns if _is_totalizable_value_column(col)]
    if not total_cols:
        return df_export

    out = df_export.copy()
    total_row = {col: "" for col in out.columns}
    if len(out.columns) > 0:
        total_row[out.columns[0]] = "TOTAL"

    for col in total_cols:
        total_row[col] = round(sum(_parse_br_money_value(v) for v in out[col].tolist()), 2)

    return pd.concat([out, pd.DataFrame([total_row])], ignore_index=True)


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    IMPORT_DIR.mkdir(parents=True, exist_ok=True)


def _xlsx_member_name(zf: zipfile.ZipFile, wanted: str) -> str:
    """Localiza arquivos xlsx mesmo quando o exportador usa barras invertidas no ZIP."""
    wanted_norm = wanted.replace("\\", "/").lower()
    for name in zf.namelist():
        if name.replace("\\", "/").lower() == wanted_norm:
            return name
    suffix = wanted_norm.split("/")[-1]
    for name in zf.namelist():
        if name.replace("\\", "/").lower().endswith(suffix):
            return name
    raise FileNotFoundError(f"Arquivo interno não encontrado no XLSX: {wanted}")


def _xlsx_col_to_num(col: str) -> int:
    value = 0
    for ch in col:
        value = value * 26 + (ord(ch.upper()) - 64)
    return value


def _xlsx_cell_ref(ref: str) -> tuple[int, int]:
    m = re.match(r"([A-Z]+)(\d+)", str(ref))
    if not m:
        return 0, 0
    return _xlsx_col_to_num(m.group(1)), int(m.group(2))


def _maybe_number(value):
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        txt = str(value).strip()
        if txt == "":
            return None
        n = float(txt)
        return int(n) if n.is_integer() else n
    except Exception:
        return value


def _xlsx_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    """Lê sharedStrings.xml quando o Excel salva textos como índices."""
    try:
        member = _xlsx_member_name(zf, "xl/sharedStrings.xml")
    except Exception:
        return []
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    root = ET.fromstring(zf.read(member))
    strings: list[str] = []
    for si in root.findall("m:si", ns):
        strings.append("".join(si.itertext()).strip())
    return strings


def _xlsx_first_sheet_member(zf: zipfile.ZipFile) -> str:
    """Localiza a primeira planilha em exportações OOXML padrão ou simplificadas."""
    candidates = [
        "xl/sheet1.xml",
        "xl/worksheets/sheet1.xml",
    ]
    for wanted in candidates:
        try:
            return _xlsx_member_name(zf, wanted)
        except Exception:
            pass
    for name in zf.namelist():
        normalized = name.replace("\\", "/").lower()
        if normalized.startswith("xl/worksheets/") and normalized.endswith(".xml"):
            return name
    return _xlsx_member_name(zf, "sheet1.xml")


def _xlsx_cell_value(cell, ns: dict, shared_strings: list[str]):
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        inline = cell.find("m:is", ns)
        return ("".join(inline.itertext()) if inline is not None else "").strip()

    v = cell.find("m:v", ns)
    raw = v.text if v is not None else None

    if cell_type == "s":
        try:
            idx = int(float(str(raw).strip()))
            return shared_strings[idx] if 0 <= idx < len(shared_strings) else ""
        except Exception:
            return ""
    if cell_type in {"str", "b"}:
        return str(raw or "").strip()

    return _maybe_number(raw)


def parse_retorno_esocial_s5003(path: str | Path) -> pd.DataFrame:
    """Lê o relatório de retorno S-5003 do eSocial exportado em XLSX.

    Padrões aceitos:
    - XLSX simplificado com xl/sheet1.xml e textos inline;
    - XLSX padrão do Excel com xl/worksheets/sheet1.xml e sharedStrings.xml;
    - linhas complementares do mesmo colaborador, em que A/C/E/H/I vêm vazias,
      mas J/K/L possuem valores. Nesse caso, a linha pertence ao último
      trabalhador lido.
    """
    path = Path(path)
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as zf:
        sheet_name = _xlsx_first_sheet_member(zf)
        shared_strings = _xlsx_shared_strings(zf)
        root = ET.fromstring(zf.read(sheet_name))

    def _to_float_retorno(value) -> float:
        if value is None or value == "":
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        txt = str(value).strip()
        if not txt:
            return 0.0
        # Compatível tanto com "1733.42" quanto com "1.733,42".
        if "," in txt:
            txt = txt.replace(".", "").replace(",", ".")
        try:
            return float(txt)
        except Exception:
            return 0.0

    rows: dict[int, dict[int, object]] = {}
    for row in root.findall(".//m:sheetData/m:row", ns):
        row_num = int(row.attrib.get("r", "0") or 0)
        vals: dict[int, object] = {}
        for cell in row.findall("m:c", ns):
            ref = cell.attrib.get("r", "")
            col_num, _ = _xlsx_cell_ref(ref)
            vals[col_num] = _xlsx_cell_value(cell, ns, shared_strings)
        rows[row_num] = vals

    registros = []
    empresa_codigo = None
    empresa_nome = ""
    competencia = ""
    trabalhador_atual: dict[str, object] | None = None

    for row_num in sorted(rows):
        vals = rows[row_num]
        col_a = vals.get(1)
        col_b = vals.get(2)
        col_c = vals.get(3)

        if col_a is not None and str(col_b).strip() == "-" and col_c:
            try:
                empresa_codigo = int(float(str(col_a).strip()))
                empresa_nome = str(col_c).strip()
                trabalhador_atual = None
            except Exception:
                pass

        if isinstance(col_a, str) and "Folha de Pagamento" in col_a:
            m_comp = re.search(r"(\d{2})/(\d{4})", col_a)
            if m_comp:
                competencia = f"{m_comp.group(2)}-{m_comp.group(1)}"
            trabalhador_atual = None

        tipo_cad = str(col_c or "").strip()
        m_cad = re.match(r"^(\d+)\s*/\s*(\d+)$", tipo_cad)
        nome_linha = str(col_a or "").strip()
        cpf_linha = str(vals.get(8) or "").strip()
        tipo = vals.get(10)
        base = vals.get(11)
        valor = vals.get(12)
        tem_valores_fgts = tipo is not None and base is not None and valor is not None

        if m_cad and nome_linha and cpf_linha:
            trabalhador_atual = {
                "filial": int(m_cad.group(1)),
                "cadastro": int(m_cad.group(2)),
                "colaborador_esocial": nome_linha,
                "matricula_esocial": str(vals.get(5) or "").strip(),
                "cpf": cpf_linha,
                "categoria_esocial": str(vals.get(9) or "").strip(),
                "linha_principal_retorno": row_num,
            }
            trabalhador_linha = trabalhador_atual
        elif tem_valores_fgts and trabalhador_atual is not None and not nome_linha and not tipo_cad and not cpf_linha:
            trabalhador_linha = trabalhador_atual
        else:
            continue

        if not tem_valores_fgts:
            continue

        try:
            tipo_int = int(float(str(tipo).strip()))
        except Exception:
            continue

        registros.append({
            "competencia": competencia,
            "empresa_codigo": empresa_codigo,
            "empresa_nome_original": empresa_nome,
            "empresa_nome": empresa_nome_curto(empresa_nome),
            "filial": int(trabalhador_linha["filial"]),
            "cadastro": int(trabalhador_linha["cadastro"]),
            "colaborador_esocial": str(trabalhador_linha["colaborador_esocial"]),
            "matricula_esocial": str(trabalhador_linha["matricula_esocial"]),
            "cpf": str(trabalhador_linha["cpf"]),
            "categoria_esocial": str(trabalhador_linha["categoria_esocial"]),
            "tipo_valor_fgts": tipo_int,
            "tipo_valor_desc": tipo_valor_fgts_desc(tipo_int),
            "base_calculo_esocial": round(_to_float_retorno(base), 2),
            "valor_fgts_esocial": round(_to_float_retorno(valor), 2),
            "linha_retorno": row_num,
            "linha_principal_retorno": int(trabalhador_linha.get("linha_principal_retorno", row_num)),
            "linha_complementar_mesmo_trabalhador": bool(row_num != int(trabalhador_linha.get("linha_principal_retorno", row_num))),
        })

    return pd.DataFrame(registros)


def tipo_valor_fgts_desc(tipo: int) -> str:
    descricoes = {
        11: "FGTS mensal",
        12: "FGTS 13º salário",
        13: "FGTS mensal - período anterior",
        14: "FGTS 13º - período anterior",
        15: "FGTS mensal - aprendiz/CVA",
        16: "FGTS 13º - aprendiz/CVA",
        17: "FGTS mensal - aprendiz período anterior",
        18: "FGTS 13º - aprendiz período anterior",
        21: "FGTS mensal rescisório",
        22: "FGTS 13º rescisório",
        23: "FGTS aviso prévio indenizado",
        24: "FGTS mensal rescisório - período anterior",
        25: "FGTS 13º rescisório - período anterior",
        26: "FGTS aviso prévio indenizado - período anterior",
        27: "FGTS mensal rescisório - aprendiz/CVA",
        28: "FGTS 13º rescisório - aprendiz/CVA",
        29: "FGTS aviso prévio indenizado - aprendiz/CVA",
        31: "FGTS 13º rescisório - aprendiz/CVA período anterior",
        41: "FGTS mensal doméstico 3,2%",
        42: "FGTS 13º doméstico 3,2%",
        43: "FGTS mensal doméstico 3,2% período anterior",
        44: "FGTS 13º doméstico 3,2% período anterior",
        45: "FGTS mensal doméstico rescisório 3,2%",
        46: "FGTS 13º doméstico rescisório 3,2%",
        47: "FGTS aviso prévio doméstico 3,2%",
        48: "FGTS mensal doméstico rescisório 3,2% período anterior",
        49: "FGTS 13º doméstico rescisório 3,2% período anterior",
        50: "FGTS aviso prévio doméstico 3,2% período anterior",
    }
    return descricoes.get(int(tipo), f"Tipo {tipo}")


# Tipos de valor FGTS do S-5003 que são rescisórios.
# Esses valores normalmente já foram recolhidos em guia rescisória e, por isso,
# não entram na conciliação da guia mensal/13º do dashboard.
TIPOS_FGTS_RESCISORIO_DESCONSIDERAR = {
    21, 22, 23, 24, 25, 26, 27, 28, 29, 31,
    45, 46, 47, 48, 49, 50,
}


def _tipo_fgts_rescisorio_desconsiderar(tipo: int) -> bool:
    try:
        return int(tipo) in TIPOS_FGTS_RESCISORIO_DESCONSIDERAR
    except Exception:
        return False


def _tipo_bucket_fgts(tipo: int) -> str:
    mensal = {11, 13, 15, 17, 41, 43}
    decimo = {12, 14, 16, 18, 42, 44}
    if int(tipo) in mensal:
        return "mensal"
    if int(tipo) in decimo:
        return "13"
    return "outros"


@st.cache_data(show_spinner=False)
def load_retorno_esocial(path: str | Path) -> pd.DataFrame:
    df_ret = pd.read_csv(path, sep=";")
    money_cols = ["base_calculo_esocial", "valor_fgts_esocial"]
    for c in money_cols:
        if c in df_ret.columns:
            df_ret[c] = pd.to_numeric(df_ret[c], errors="coerce").fillna(0)
    for c in ["empresa_codigo", "filial", "cadastro", "tipo_valor_fgts", "linha_retorno"]:
        if c in df_ret.columns:
            df_ret[c] = pd.to_numeric(df_ret[c], errors="coerce").fillna(0).astype(int)
    if "empresa_nome_original" in df_ret.columns:
        df_ret["empresa_nome"] = df_ret["empresa_nome_original"].map(empresa_nome_curto)
    return df_ret


def salvar_retorno_esocial(df_ret: pd.DataFrame) -> None:
    ensure_data_dir()
    df_ret.to_csv(RETORNO_ESOCIAL_CSV, index=False, sep=";", encoding="utf-8-sig")
    load_retorno_esocial.clear()


def limpar_base_fgts_e_retorno() -> None:
    """Remove bases antigas antes de importar nova planilha FGTS."""
    for arquivo in [COLAB_CSV, TOTAIS_CSV, RESUMO_EMPRESA_CSV, RESUMO_FILIAL_CSV, RETORNO_ESOCIAL_CSV]:
        try:
            if arquivo.exists():
                arquivo.unlink()
        except Exception:
            pass
    load_data.clear()
    load_retorno_esocial.clear()


def limpar_retorno_esocial() -> None:
    """Remove retorno eSocial antigo antes de importar novo S-5003."""
    try:
        if RETORNO_ESOCIAL_CSV.exists():
            RETORNO_ESOCIAL_CSV.unlink()
    except Exception:
        pass
    load_retorno_esocial.clear()


def _cpf_digits(value: object) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _matricula_key(value: object) -> str:
    try:
        return str(int(float(str(value).strip())))
    except Exception:
        return re.sub(r"\D+", "", str(value or ""))


def _chave_cpf_matricula(cpf: object, matricula: object) -> str:
    return _cpf_digits(cpf) + "|" + _matricula_key(matricula)


def preparar_conciliacao_fgts(base_df: pd.DataFrame, retorno_df: pd.DataFrame, competencia: str, empresa_sel: str = "Todos", busca: str = "") -> pd.DataFrame:
    if base_df.empty or retorno_df.empty:
        return pd.DataFrame()

    ret = retorno_df[retorno_df["competencia"].astype(str) == str(competencia)].copy()
    if str(empresa_sel or "Todos") != "Todos":
        try:
            empresa_codigo_sel = int(str(empresa_sel).split(" - ")[0])
            ret = ret[ret["empresa_codigo"] == empresa_codigo_sel]
        except Exception:
            pass
    if str(busca or "").strip():
        b = str(busca).strip().upper()
        ret = ret[
            ret["colaborador_esocial"].astype(str).str.upper().str.contains(b, na=False)
            | ret["cpf"].astype(str).str.upper().str.contains(b, na=False)
            | ret["cadastro"].astype(str).str.contains(b, na=False)
        ]
    if ret.empty:
        return pd.DataFrame()

    # Chave primária principal: CPF + matrícula/cadastro do vínculo.
    # Observação importante:
    # Em alguns retornos S-5003, o eSocial pode retornar a matrícula anterior do mesmo CPF
    # enquanto o relatório Senior FGTS já traz a nova matrícula ativa. Para esse caso,
    # o dashboard faz uma segunda tentativa de conciliação APENAS quando CPF, empresa e
    # valores de base/FGTS batem exatamente. A linha fica marcada em "observacao_conciliacao".
    ret["cpf_chave"] = ret["cpf"].apply(_cpf_digits)
    ret["matricula_chave"] = ret["cadastro"].apply(_matricula_key)
    ret["chave_conciliacao"] = ret["cpf_chave"] + "|" + ret["matricula_chave"]

    ret["tipo_rescisorio_desconsiderado"] = ret["tipo_valor_fgts"].apply(_tipo_fgts_rescisorio_desconsiderar)
    ret_keys_antes_filtro = ret.groupby("chave_conciliacao", as_index=False).agg(
        possui_tipo_valido=("tipo_rescisorio_desconsiderado", lambda x: bool((~x).any())),
        possui_apenas_rescisorio=("tipo_rescisorio_desconsiderado", lambda x: bool(x.all())),
    )
    chaves_apenas_rescisorio = set(
        ret_keys_antes_filtro.loc[
            ret_keys_antes_filtro["possui_apenas_rescisorio"], "chave_conciliacao"
        ].astype(str).tolist()
    )

    # Remove do retorno os tipos rescisórios, pois eles pertencem à guia rescisória
    # e não à conciliação mensal/13º da competência.
    ret = ret[~ret["tipo_rescisorio_desconsiderado"]].copy()

    if not ret.empty:
        ret["bucket"] = ret["tipo_valor_fgts"].apply(_tipo_bucket_fgts)
        ret["ret_base_mensal"] = ret.apply(lambda r: r["base_calculo_esocial"] if r["bucket"] == "mensal" else 0, axis=1)
        ret["ret_fgts_mensal"] = ret.apply(lambda r: r["valor_fgts_esocial"] if r["bucket"] == "mensal" else 0, axis=1)
        ret["ret_base_13"] = ret.apply(lambda r: r["base_calculo_esocial"] if r["bucket"] == "13" else 0, axis=1)
        ret["ret_fgts_13"] = ret.apply(lambda r: r["valor_fgts_esocial"] if r["bucket"] == "13" else 0, axis=1)
        ret["ret_base_outros"] = ret.apply(lambda r: r["base_calculo_esocial"] if r["bucket"] == "outros" else 0, axis=1)
        ret["ret_fgts_outros"] = ret.apply(lambda r: r["valor_fgts_esocial"] if r["bucket"] == "outros" else 0, axis=1)

        ret_sum = ret.groupby("chave_conciliacao", as_index=False).agg(
            empresa_codigo_esocial=("empresa_codigo", "first"),
            empresa_nome_esocial=("empresa_nome", "first"),
            cadastro_esocial=("cadastro", "first"),
            cpf_chave=("cpf_chave", "first"),
            matricula_chave_esocial=("matricula_chave", "first"),
            colaborador_esocial=("colaborador_esocial", "first"),
            cpf_esocial=("cpf", "first"),
            categoria_esocial=("categoria_esocial", "first"),
            tipos_esocial=("tipo_valor_fgts", lambda x: ", ".join(str(int(v)) for v in sorted(set(x)))),
            tipos_desc_esocial=("tipo_valor_desc", lambda x: " | ".join(sorted(set(str(v) for v in x)))),
            ret_base_mensal=("ret_base_mensal", "sum"),
            ret_fgts_mensal=("ret_fgts_mensal", "sum"),
            ret_base_13=("ret_base_13", "sum"),
            ret_fgts_13=("ret_fgts_13", "sum"),
            ret_base_outros=("ret_base_outros", "sum"),
            ret_fgts_outros=("ret_fgts_outros", "sum"),
        )
    else:
        ret_sum = pd.DataFrame(columns=[
            "chave_conciliacao", "empresa_codigo_esocial", "empresa_nome_esocial",
            "cadastro_esocial", "cpf_chave", "matricula_chave_esocial",
            "colaborador_esocial", "cpf_esocial", "categoria_esocial",
            "tipos_esocial", "tipos_desc_esocial",
            "ret_base_mensal", "ret_fgts_mensal", "ret_base_13", "ret_fgts_13",
            "ret_base_outros", "ret_fgts_outros"
        ])

    base_cols = [
        "empresa_codigo", "empresa_nome", "empresa_label", "cadastro", "colaborador", "cpf",
        "base_fgts_mensal", "valor_fgts_mensal", "base_fgts_13", "valor_fgts_13"
    ]
    base_aux = base_df[[c for c in base_cols if c in base_df.columns]].copy()

    if not base_aux.empty:
        base_aux["cpf_chave"] = base_aux["cpf"].apply(_cpf_digits)
        base_aux["matricula_chave"] = base_aux["cadastro"].apply(_matricula_key)
        base_aux["chave_conciliacao"] = base_aux["cpf_chave"] + "|" + base_aux["matricula_chave"]

    if chaves_apenas_rescisorio and not base_aux.empty:
        base_aux = base_aux[~base_aux["chave_conciliacao"].astype(str).isin(chaves_apenas_rescisorio)].copy()

    conc = base_aux.merge(ret_sum, on="chave_conciliacao", how="outer", indicator=True)
    conc["observacao_conciliacao"] = ""

    # Segunda tentativa: CPF + empresa + valores.
    # Isso trata troca de matrícula/vínculo no Senior, sem misturar contratos indevidamente,
    # porque só une quando os valores mensais/13º estão iguais.
    tol = 0.01
    if not conc.empty:
        left_idx = conc.index[conc["_merge"] == "left_only"].tolist()
        right_idx = conc.index[conc["_merge"] == "right_only"].tolist()
        usados_right = set()
        linhas_remover = set()
        linhas_novas = []

        for li in left_idx:
            lrow = conc.loc[li]
            cpf_l = str(lrow.get("cpf_chave_x") or lrow.get("cpf_chave") or "")
            emp_l = int(lrow.get("empresa_codigo") or 0)
            candidatos = []
            for ri in right_idx:
                if ri in usados_right:
                    continue
                rrow = conc.loc[ri]
                cpf_r = str(rrow.get("cpf_chave_y") or rrow.get("cpf_chave") or "")
                emp_r = int(rrow.get("empresa_codigo_esocial") or 0)
                if cpf_l != cpf_r or emp_l != emp_r:
                    continue
                if (
                    abs(float(lrow.get("base_fgts_mensal") or 0) - float(rrow.get("ret_base_mensal") or 0)) <= tol
                    and abs(float(lrow.get("valor_fgts_mensal") or 0) - float(rrow.get("ret_fgts_mensal") or 0)) <= tol
                    and abs(float(lrow.get("base_fgts_13") or 0) - float(rrow.get("ret_base_13") or 0)) <= tol
                    and abs(float(lrow.get("valor_fgts_13") or 0) - float(rrow.get("ret_fgts_13") or 0)) <= tol
                ):
                    candidatos.append(ri)

            if len(candidatos) == 1:
                ri = candidatos[0]
                rrow = conc.loc[ri]
                nova = lrow.copy()
                for col in [
                    "empresa_codigo_esocial", "empresa_nome_esocial", "cadastro_esocial",
                    "matricula_chave_esocial", "colaborador_esocial", "cpf_esocial",
                    "categoria_esocial", "tipos_esocial", "tipos_desc_esocial",
                    "ret_base_mensal", "ret_fgts_mensal", "ret_base_13", "ret_fgts_13",
                    "ret_base_outros", "ret_fgts_outros"
                ]:
                    if col in conc.columns:
                        nova[col] = rrow.get(col)
                nova["_merge"] = "both"
                nova["observacao_conciliacao"] = (
                    f"Conciliado por CPF + valores; matrícula Senior {int(lrow.get('cadastro') or 0)} "
                    f"e matrícula eSocial {int(rrow.get('cadastro_esocial') or 0)}"
                )
                linhas_novas.append(nova)
                linhas_remover.update([li, ri])
                usados_right.add(ri)

        if linhas_novas:
            conc = pd.concat([conc.drop(index=list(linhas_remover)), pd.DataFrame(linhas_novas)], ignore_index=True)

    for c in ["base_fgts_mensal", "valor_fgts_mensal", "base_fgts_13", "valor_fgts_13", "ret_base_mensal", "ret_fgts_mensal", "ret_base_13", "ret_fgts_13", "ret_base_outros", "ret_fgts_outros"]:
        if c not in conc.columns:
            conc[c] = 0
        conc[c] = pd.to_numeric(conc[c], errors="coerce").fillna(0)

    conc["empresa"] = conc["empresa_nome"].fillna(conc["empresa_nome_esocial"]).fillna("")
    conc["cadastro_conciliacao"] = conc["cadastro"].fillna(conc["cadastro_esocial"]).fillna(0)
    conc["cadastro_conciliacao"] = pd.to_numeric(conc["cadastro_conciliacao"], errors="coerce").fillna(0).astype(int)
    conc["cadastro_esocial_conciliacao"] = pd.to_numeric(conc.get("cadastro_esocial", 0), errors="coerce").fillna(0).astype(int)
    conc["colaborador_conciliacao"] = conc["colaborador"].fillna(conc["colaborador_esocial"]).fillna("")
    conc["cpf_conciliacao"] = conc["cpf"].fillna(conc["cpf_esocial"]).fillna("")

    conc["dif_base_mensal"] = (conc["base_fgts_mensal"] - conc["ret_base_mensal"]).round(2)
    conc["dif_fgts_mensal"] = (conc["valor_fgts_mensal"] - conc["ret_fgts_mensal"]).round(2)
    conc["dif_base_13"] = (conc["base_fgts_13"] - conc["ret_base_13"]).round(2)
    conc["dif_fgts_13"] = (conc["valor_fgts_13"] - conc["ret_fgts_13"]).round(2)

    conc["divergencia_base"] = (conc["dif_base_mensal"].abs() > tol) | (conc["dif_base_13"].abs() > tol) | (conc["_merge"] != "both")
    conc["divergencia_valor"] = (conc["dif_fgts_mensal"].abs() > tol) | (conc["dif_fgts_13"].abs() > tol) | (conc["_merge"] != "both")

    def status(row) -> str:
        if row["_merge"] == "left_only":
            return "Só no Senior"
        if row["_merge"] == "right_only":
            return "Só no eSocial"
        if row["divergencia_base"] and row["divergencia_valor"]:
            return "Divergência de base e valor"
        if row["divergencia_base"]:
            return "Divergência de base"
        if row["divergencia_valor"]:
            return "Divergência de valor"
        return "OK"

    conc["status_conciliacao"] = conc.apply(status, axis=1)
    return conc.sort_values(["status_conciliacao", "empresa", "colaborador_conciliacao", "cadastro_conciliacao"]).reset_index(drop=True)

def render_conciliacao_fgts(base_df: pd.DataFrame, retorno_df: pd.DataFrame, competencia: str, empresa_sel: str = "Todos", busca: str = "") -> None:
    if retorno_df.empty:
        st.info("Relatório de retorno do eSocial ainda não importado. Use o botão **Importar retorno eSocial** para carregar o relatório S-5003.")
        return

    conc = preparar_conciliacao_fgts(base_df, retorno_df, competencia, empresa_sel, busca)
    if conc.empty:
        st.warning("Não encontrei dados do retorno eSocial para a competência filtrada.")
        return

    if "conciliacao_modo" not in st.session_state:
        st.session_state.conciliacao_modo = "todos"

    st.markdown("<div class='section-title'>CONCILIAÇÃO FGTS x eSOCIAL S-5003</div>", unsafe_allow_html=True)
    st.markdown("<div class='conc-note'>Comparação principal pela chave CPF + Matrícula/Cadastro do vínculo. Quando houver troca de matrícula do mesmo CPF, o dashboard faz conciliação auxiliar por CPF + empresa + valores iguais, deixando a observação na tabela. Tipos rescisórios do S-5003, como 21, 22 e 23, são desconsiderados por pertencerem à guia rescisória.</div>", unsafe_allow_html=True)

    total = len(conc)
    div_base = int(conc["divergencia_base"].sum())
    div_valor = int(conc["divergencia_valor"].sum())
    so_senior = int((conc["_merge"] == "left_only").sum())
    so_esocial = int((conc["_merge"] == "right_only").sum())

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Colaboradores conciliados", br_number(total))
    c2.metric("Divergência de base", br_number(div_base))
    c3.metric("Divergência de valor", br_number(div_valor))
    c4.metric("Só no Senior", br_number(so_senior))
    c5.metric("Só no eSocial", br_number(so_esocial))

    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("Exibir todos os colaboradores", use_container_width=True, key="btn_conc_todos"):
            st.session_state.conciliacao_modo = "todos"
    with b2:
        if st.button("Exibir somente divergência de base", use_container_width=True, key="btn_conc_base"):
            st.session_state.conciliacao_modo = "base"
    with b3:
        if st.button("Exibir somente divergência Valor FGTS Mensal/13º", use_container_width=True, key="btn_conc_valor"):
            st.session_state.conciliacao_modo = "valor"

    modo = st.session_state.conciliacao_modo
    if modo == "base":
        view = conc[conc["divergencia_base"]].copy()
    elif modo == "valor":
        view = conc[conc["divergencia_valor"]].copy()
    else:
        view = conc.copy()

    show = view[[
        "status_conciliacao", "empresa", "colaborador_conciliacao", "cpf_conciliacao",
        "base_fgts_mensal", "ret_base_mensal", "dif_base_mensal",
        "valor_fgts_mensal", "ret_fgts_mensal", "dif_fgts_mensal",
        "base_fgts_13", "ret_base_13", "dif_base_13",
        "valor_fgts_13", "ret_fgts_13", "dif_fgts_13",
        "ret_base_outros", "ret_fgts_outros", "tipos_desc_esocial", "observacao_conciliacao"
    ]].copy()
    money_cols = [
        "base_fgts_mensal", "ret_base_mensal", "dif_base_mensal",
        "valor_fgts_mensal", "ret_fgts_mensal", "dif_fgts_mensal",
        "base_fgts_13", "ret_base_13", "dif_base_13",
        "valor_fgts_13", "ret_fgts_13", "dif_fgts_13",
        "ret_base_outros", "ret_fgts_outros"
    ]
    for c in money_cols:
        # Na tabela de conciliação, exibe somente o número, sem o prefixo "R$".
        show[c] = show[c].map(lambda v: br_money(v).replace("R$ ", ""))
    show.columns = [
        "Status", "Empresa", "Colaborador", "CPF",
        "Base Senior Mensal", "Base eSocial Mensal", "Dif. Base Mensal",
        "FGTS Senior Mensal", "FGTS eSocial Mensal", "Dif. FGTS Mensal",
        "Base Senior 13º", "Base eSocial 13º", "Dif. Base 13º",
        "FGTS Senior 13º", "FGTS eSocial 13º", "Dif. FGTS 13º",
        "Base eSocial Outros", "FGTS eSocial Outros", "Descrição tipos eSocial", "Observação"
    ]
    # Tabela com cabeçalho branco e linhas inferiores sem preenchimento de fundo.
    render_clean_table(show, height=430)

    st.download_button(
        "📥 Exportar conciliação FGTS x eSocial",
        data=gerar_excel_download(view),
        file_name=f"conciliacao_fgts_esocial_{competencia}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )


@st.cache_data(show_spinner=False)
def load_data(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";")
    money_cols = [
        "base_fgts_mensal", "valor_fgts_mensal", "adicional_05_mensal",
        "base_fgts_13", "valor_fgts_13", "adicional_05_13",
        "dissidio_fgts_mensal", "dissidio_fgts_13", "base_fgts_total", "valor_fgts_total"
    ]
    for c in money_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    for c in ["empresa_codigo", "filial", "cadastro"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    # FGTS consolidado = FGTS mensal + FGTS 13º.
    # A partir da V9, todos os indicadores, gráficos, rankings e filtros de FGTS usam este campo.
    if "valor_fgts_mensal" in df.columns and "valor_fgts_13" in df.columns:
        df["valor_fgts_consolidado"] = df["valor_fgts_mensal"].fillna(0) + df["valor_fgts_13"].fillna(0)
    else:
        df["valor_fgts_consolidado"] = 0
    if "empresa_nome" in df.columns:
        df["empresa_nome_original"] = df["empresa_nome"].astype(str).str.strip()
        df["empresa_nome"] = df["empresa_nome_original"].map(empresa_nome_curto)
    else:
        df["empresa_nome_original"] = ""
        df["empresa_nome"] = ""
    df["empresa_label"] = df["empresa_codigo"].astype(str) + " - " + df["empresa_nome"].astype(str)
    df["filial_label"] = "Filial " + df["filial"].astype(str) + " - " + df["filial_nome"].astype(str)
    return df


def save_history(df_new: pd.DataFrame, totals_new: pd.DataFrame, replace_same_competence: bool = True) -> tuple[int, int, str]:
    ensure_data_dir()
    competencia = str(df_new["competencia"].dropna().iloc[0]) if not df_new.empty else ""

    if COLAB_CSV.exists():
        old = pd.read_csv(COLAB_CSV, sep=";")
        old_count = len(old)
        if replace_same_competence and competencia:
            old = old[old["competencia"].astype(str) != competencia]
        df_all = pd.concat([old, df_new], ignore_index=True)
    else:
        old_count = 0
        df_all = df_new.copy()

    if TOTAIS_CSV.exists() and not totals_new.empty:
        old_tot = pd.read_csv(TOTAIS_CSV, sep=";")
        if replace_same_competence and competencia:
            old_tot = old_tot[old_tot["competencia"].astype(str) != competencia]
        totals_all = pd.concat([old_tot, totals_new], ignore_index=True)
    else:
        totals_all = totals_new.copy()

    df_all.to_csv(COLAB_CSV, index=False, sep=";", encoding="utf-8-sig")
    totals_all.to_csv(TOTAIS_CSV, index=False, sep=";", encoding="utf-8-sig")

    resumo_empresa, resumo_filial = gerar_resumos(df_all)
    resumo_empresa.to_csv(RESUMO_EMPRESA_CSV, index=False, sep=";", encoding="utf-8-sig")
    resumo_filial.to_csv(RESUMO_FILIAL_CSV, index=False, sep=";", encoding="utf-8-sig")

    load_data.clear()
    return old_count, len(df_all), competencia


def bar_h(df: pd.DataFrame, x: str, y: str, title: str, color: str = "#12b7ff", top: int | None = 10):
    d = df.sort_values(x, ascending=False).copy()
    if top is not None:
        d = d.head(top)
    d = d.sort_values(x)
    altura = max(340, 110 + (len(d) * 34))
    fig = go.Figure(go.Bar(
        x=d[x], y=d[y], orientation="h", marker_color=color,
        cliponaxis=False,
        text=[br_money(v) if "valor" in x or "fgts" in x or "base" in x else br_number(v) for v in d[x]],
        textposition="outside",
        hovertemplate="%{y}<br>%{x:,.2f}<extra></extra>"
    ))
    fig.update_layout(
        title=title, title_font_color="white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white", size=11), height=altura, margin=dict(l=5, r=95, t=45, b=20),
        xaxis=dict(gridcolor="rgba(255,255,255,.12)", zeroline=False), yaxis=dict(zeroline=False),
    )
    return fig


def bar_top_colaboradores(df: pd.DataFrame, top: int = 10):
    # Mantém exatamente Top 10 e adiciona folga superior para a primeira barra não ficar cortada.
    d = df.sort_values("valor_fgts_consolidado", ascending=False).head(top).copy()
    d["colaborador_exibicao"] = d["colaborador"].astype(str) + " (" + d["cadastro"].astype(str) + ")"
    d = d.sort_values("valor_fgts_consolidado")
    altura = max(420, 150 + (len(d) * 34))
    fig = go.Figure(go.Bar(
        x=d["valor_fgts_consolidado"],
        y=d["colaborador_exibicao"],
        orientation="h",
        marker_color="#12b7ff",
        cliponaxis=False,
        text=[br_money(v) for v in d["valor_fgts_consolidado"]],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>FGTS Consolidado: R$ %{x:,.2f}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(
            text="TOP 10 COLABORADORES POR FGTS CONSOLIDADO (MENSAL + 13º)",
            font=dict(color="white", size=15),
            y=0.98,
            yanchor="top",
            x=0,
            xanchor="left",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white", size=11),
        height=altura,
        margin=dict(l=10, r=110, t=60, b=42),
        bargap=0.28,
        xaxis=dict(
            title="FGTS Consolidado (R$)",
            gridcolor="rgba(255,255,255,.12)",
            zeroline=False,
            automargin=True,
        ),
        yaxis=dict(
            zeroline=False,
            automargin=True,
            categoryorder="array",
            categoryarray=d["colaborador_exibicao"].tolist(),
        ),
    )
    return fig


def preparar_distribuicao_empresa(df_emp: pd.DataFrame):
    """Prepara a distribuição sem agrupar empresas em 'Outras'.
    A tela de distribuição deve exibir 100% das empresas da competência filtrada.
    """
    d = df_emp.sort_values("valor_fgts_consolidado", ascending=False).copy().reset_index(drop=True)
    total = float(d["valor_fgts_consolidado"].sum()) if not d.empty else 0.0
    d["participacao"] = d["valor_fgts_consolidado"].apply(lambda v: (float(v) / total * 100) if total else 0)
    cores = [
        "#12b7ff", "#a83ec8", "#ffc300", "#ff4f7b", "#00c2a8",
        "#ff8a3d", "#65c7ff", "#9b8cff", "#8ee6a3", "#ff9a91",
        "#78c6ff", "#a696f0", "#a6e8a7", "#f9d65c", "#f78fb3",
        "#85c1e9", "#ca6dff", "#2ed3b7", "#ffb86b", "#b8f2d4"
    ]
    d["cor"] = [cores[i % len(cores)] for i in range(len(d))]
    return d, total


def donut_empresa_v7(df_plot: pd.DataFrame, total: float):
    fig = go.Figure(go.Pie(
        labels=df_plot["empresa_nome"],
        values=df_plot["valor_fgts_consolidado"],
        hole=.53,
        sort=False,
        direction="clockwise",
        textinfo="percent",
        textposition="outside",
        texttemplate="%{percent:.2%}",
        textfont=dict(color="white", size=13),
        insidetextfont=dict(color="white", size=12),
        hovertemplate="<b>%{label}</b><br>Valor: R$ %{value:,.2f}<br>Participação: %{percent}<extra></extra>",
        marker=dict(colors=df_plot["cor"].tolist(), line=dict(color="rgba(255,255,255,.35)", width=1)),
        automargin=True,
        showlegend=False,
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white", size=12),
        height=560,
        margin=dict(l=75, r=75, t=30, b=10),
        annotations=[dict(
            text=f"<b>TOTAL</b><br><span style='font-size:20px'>{br_money(total)}</span><br><span style='font-size:12px'>FGTS CONSOLIDADO</span>",
            x=.5, y=.5, showarrow=False, font=dict(color="white", size=18)
        )]
    )
    return fig


def legenda_donut_html(df_plot: pd.DataFrame) -> str:
    items = []
    for _, r in df_plot.iterrows():
        nome = str(r["empresa_nome"])
        items.append(
            f"<div class='donut-legend-item'>"
            f"<span class='legend-dot-big color-swatch' style='background:{r['cor']} !important;'></span>"
            f"<span>{nome}</span>"
            f"</div>"
        )
    return f"<div class='donut-legend-grid'>{''.join(items)}</div>"


def legenda_empresa_html(df_plot: pd.DataFrame, total: float) -> str:
    rows = []
    for _, r in df_plot.iterrows():
        nome = str(r["empresa_nome"])
        rows.append(
            f"<tr>"
            f"<td><span class='legend-dot-big color-swatch' style='background:{r['cor']} !important;'></span>{nome}</td>"
            f"<td style='text-align:center;font-weight:900'>{r['participacao']:.2f}%</td>"
            f"<td style='text-align:right;font-weight:900'>{br_money(r['valor_fgts_consolidado'])}</td>"
            f"</tr>"
        )
    rows.append(
        f"<tr class='legend-total-row'>"
        f"<td>TOTAL</td>"
        f"<td style='text-align:center'>100,00%</td>"
        f"<td style='text-align:right'>{br_money(total)}</td>"
        f"</tr>"
    )
    return (
        "<table class='legend-table legend-table-full'>"
        "<thead><tr>"
        "<th>Empresa</th>"
        "<th style='text-align:center'>%</th>"
        "<th style='text-align:right'>Valor</th>"
        "</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
    )

def small_line(totals: dict):
    labels = ["FGTS Consolidado", "FGTS Mensal", "FGTS 13º"]
    values = [totals["valor_fgts_consolidado"], totals["valor_fgts_mensal"], totals["valor_fgts_13"]]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=labels, y=values, mode="lines+markers+text", line=dict(width=4, color="#12b7ff"), marker=dict(size=12), text=[br_money(v) for v in values], textposition="top center"))
    fig.update_layout(title="COMPOSIÇÃO DOS VALORES", title_font_color="white", height=300,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="white", size=11),
        margin=dict(l=10, r=10, t=45, b=20), yaxis=dict(gridcolor="rgba(255,255,255,.12)", zeroline=False))
    return fig


def line_historico(df: pd.DataFrame):
    hist = df.groupby("competencia", as_index=False).agg(
        valor_fgts_mensal=("valor_fgts_mensal", "sum"),
        valor_fgts_13=("valor_fgts_13", "sum"),
        valor_fgts_consolidado=("valor_fgts_consolidado", "sum"),
        base_fgts_mensal=("base_fgts_mensal", "sum"),
        colaboradores=("cadastro", "nunique"),
    ).sort_values("competencia")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist["competencia"], y=hist["valor_fgts_consolidado"], mode="lines+markers+text", name="FGTS Consolidado", text=[br_money(v) for v in hist["valor_fgts_consolidado"]], textposition="top center", line=dict(width=4, color="#00b050")))
    fig.add_trace(go.Scatter(x=hist["competencia"], y=hist["valor_fgts_mensal"], mode="lines+markers", name="FGTS Mensal", line=dict(width=3, color="#12b7ff")))
    fig.add_trace(go.Scatter(x=hist["competencia"], y=hist["valor_fgts_13"], mode="lines+markers", name="FGTS 13º", line=dict(width=3, color="#7b3fb5")))
    fig.update_layout(title="EVOLUÇÃO POR COMPETÊNCIA", title_font_color="white", height=360,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="white", size=11),
        margin=dict(l=10, r=10, t=45, b=20), yaxis=dict(gridcolor="rgba(255,255,255,.12)", zeroline=False), xaxis=dict(gridcolor="rgba(255,255,255,.08)"))
    return fig, hist



def gerar_excel_download(base_df: pd.DataFrame, emp_df: pd.DataFrame | None = None, fil_df: pd.DataFrame | None = None) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        _df_com_totalizador(base_df).to_excel(writer, index=False, sheet_name="colaboradores")
        if emp_df is not None:
            _df_com_totalizador(emp_df).to_excel(writer, index=False, sheet_name="resumo_empresa")
        if fil_df is not None:
            _df_com_totalizador(fil_df).to_excel(writer, index=False, sheet_name="resumo_filial")
    return output.getvalue()





def _selection_points(event) -> list:
    """Retorna os pontos selecionados do st.plotly_chart de forma compatível
    com diferentes versões/formatos do Streamlit.
    """
    try:
        if event is None:
            return []
        selection = event.get("selection", {}) if isinstance(event, dict) else getattr(event, "selection", {})
        if selection is None:
            return []
        points = selection.get("points", []) if isinstance(selection, dict) else getattr(selection, "points", [])
        return list(points or [])
    except Exception:
        return []


def get_plotly_selected_point_index(event) -> int | None:
    """Extrai o índice do ponto selecionado.

    A seleção do Streamlit/Plotly nem sempre retorna `customdata` em todos os
    ambientes. Por isso, usamos primeiro point_index/point_number e, depois,
    point_indices. Esse índice é usado para buscar a empresa/filial na mesma
    ordem em que o gráfico foi desenhado.
    """
    try:
        points = _selection_points(event)
        if points:
            point = points[0]
            if isinstance(point, dict):
                for key in ("point_index", "pointIndex", "point_number", "pointNumber", "pointNumber"):
                    if key in point and point[key] is not None:
                        return int(point[key])
                if "customdata" in point and point["customdata"] is not None:
                    # Mantém compatibilidade com versões que retornam customdata.
                    custom = point["customdata"]
                    if isinstance(custom, (list, tuple)):
                        custom = custom[0] if custom else None
                    return int(custom) if custom is not None else None
            else:
                for key in ("point_index", "pointIndex", "point_number", "pointNumber"):
                    value = getattr(point, key, None)
                    if value is not None:
                        return int(value)
        selection = event.get("selection", {}) if isinstance(event, dict) else getattr(event, "selection", {})
        point_indices = selection.get("point_indices", []) if isinstance(selection, dict) else getattr(selection, "point_indices", [])
        if point_indices:
            return int(point_indices[0])
    except Exception:
        return None
    return None


def get_plotly_selected_customdata(event) -> int | None:
    """Compatibilidade com versões anteriores do app."""
    return get_plotly_selected_point_index(event)


def bar_empresa_drill(df_emp: pd.DataFrame):
    d = df_emp.sort_values("valor_fgts_consolidado", ascending=False).copy().reset_index(drop=True)

    def wrap_empresa(qtd_colaboradores, nome, width=12):
        import textwrap
        nome = str(nome).strip()
        partes = textwrap.wrap(nome, width=width, break_long_words=False, break_on_hyphens=False)
        if not partes:
            partes = [nome]
        # Primeira linha: quantidade de funcionários da empresa.
        # Linhas seguintes: nome da empresa quebrado para evitar sobreposição visual.
        nome_quebrado = "<br>".join(partes[:5])
        # Deixa a quantidade de colaboradores e o nome da empresa em negrito no eixo X.
        return f"<b>{int(qtd_colaboradores)}</b><br>{nome_quebrado}"

    d["empresa_label"] = [wrap_empresa(q, n) for q, n in zip(d["qtd_colaboradores"], d["empresa_nome"])]
    fig = go.Figure(go.Bar(
        x=d["empresa_label"],
        y=d["valor_fgts_consolidado"],
        marker_color="#12b7ff",
        customdata=d[["empresa_codigo", "qtd_colaboradores", "empresa_nome_original", "empresa_nome"]].values,
        cliponaxis=False,
        text=[br_money(v).replace("R$ ", "") for v in d["valor_fgts_consolidado"]],
        textposition="outside",
        textfont=dict(size=7, color="#ffffff", family="Arial, sans-serif"),
        hovertemplate=(
            "<b>%{customdata[3]}</b><br>"
            "Nome completo: %{customdata[2]}<br>"
            "Colaboradores: %{customdata[1]}<br>"
            "FGTS Consolidado: R$ %{y:,.2f}<br><br>"
            "Clique para abrir colaboradores<extra></extra>"
        ),
    ))
    fig.update_layout(
        title="FGTS POR EMPRESA — CLIQUE EM UMA BARRA PARA DETALHAR",
        title_font_color="white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white", size=11),
        uniformtext_minsize=14,
        uniformtext_mode="show",
        height=650,
        bargap=0.52,
        margin=dict(l=18, r=42, t=78, b=170),
        xaxis=dict(
            title="Qtde Func. / Empresas",
            tickangle=0,
            tickfont=dict(size=10, color="#ffffff", family="Arial, sans-serif"),
            gridcolor="rgba(255,255,255,.08)",
            zeroline=False,
            automargin=True,
        ),
        yaxis=dict(title="Valor FGTS Consolidado (R$)", gridcolor="rgba(255,255,255,.12)", zeroline=False),
        clickmode="event+select",
    )
    return fig


def bar_filial_drill(df_filial: pd.DataFrame):
    d = df_filial.sort_values("valor_fgts_consolidado", ascending=True).copy()
    d["filial_nome_completo"] = "Filial " + d["filial"].astype(str) + " - " + d["filial_nome"].astype(str)
    altura = max(360, 120 + len(d) * 38)
    fig = go.Figure(go.Bar(
        x=d["valor_fgts_consolidado"],
        y=d["filial_nome_completo"],
        orientation="h",
        marker_color="#ff8a3d",
        customdata=d[["filial"]].values,
        cliponaxis=False,
        text=[br_money(v) for v in d["valor_fgts_consolidado"]],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>FGTS Consolidado: R$ %{x:,.2f}<br><br>Clique para abrir colaboradores da filial<extra></extra>",
    ))
    fig.update_layout(
        title="EMPRESA → FILIAL — CLIQUE EM UMA BARRA PARA DETALHAR",
        title_font_color="white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white", size=11),
        height=altura,
        margin=dict(l=5, r=105, t=55, b=45),
        xaxis=dict(title="Valor FGTS Consolidado (R$)", gridcolor="rgba(255,255,255,.12)", zeroline=False),
        yaxis=dict(zeroline=False),
        clickmode="event+select",
    )
    return fig


def breadcrumb_html(*parts: str) -> str:
    safe = " &nbsp;→&nbsp; ".join(parts)
    return f"<div class='drill-subtitle' style='margin-top:4px'>Hierarquia: <b>{safe}</b></div>"




def render_drilldown_filial(base_df: pd.DataFrame, empresa_codigo: int, filial_codigo: int, competencia: str) -> None:
    d_emp = base_df[base_df["empresa_codigo"] == int(empresa_codigo)].copy()
    d = d_emp[d_emp["filial"] == int(filial_codigo)].copy()
    if d.empty:
        st.warning("Filial não encontrada nos filtros atuais.")
        if st.button("← Voltar para empresa", type="primary"):
            st.session_state.selected_filial_codigo = None
            st.rerun()
        return

    empresa_nome = str(d["empresa_nome"].iloc[0])
    filial_nome = str(d["filial_nome"].iloc[0])
    st.markdown(
        f"""
        <div class='drill-box'>
            <div class='drill-title'>Drill-through: Empresa → Filial → Colaborador</div>
            <div class='drill-subtitle'>Empresa: <b>{empresa_nome}</b> | Filial: <b>{filial_codigo} - {filial_nome}</b> | Competência: {competencia[5:7]}/{competencia[0:4]}</div>
            {breadcrumb_html('Visão geral', empresa_nome, 'Filial ' + str(filial_codigo), 'Colaboradores')}
        </div>
        """,
        unsafe_allow_html=True,
    )
    b1, b2 = st.columns([1, 5])
    with b1:
        if st.button("← Voltar", type="primary", use_container_width=True):
            st.session_state.selected_filial_codigo = None
            st.rerun()
    with b2:
        if st.button("🏠 Visão geral", use_container_width=False):
            st.session_state.selected_filial_codigo = None
            st.session_state.selected_empresa_codigo = None
            st.rerun()

    kpis_filial = [
        ("Colaboradores", br_number(d["cadastro"].nunique()), "Ativos na filial", "kpi-blue"),
        ("Base FGTS", br_money(d["base_fgts_mensal"].sum()), "Base mensal", "kpi-cyan"),
        ("FGTS Mensal", br_money(d["valor_fgts_mensal"].sum()), "Valor mensal", "kpi-green"),
        ("FGTS 13º", br_money(d["valor_fgts_13"].sum()), "Décimo terceiro", "kpi-purple"),
        ("FGTS Consolidado", br_money(d["valor_fgts_consolidado"].sum()), "Mensal + 13º", "kpi-orange"),
        ("Adicional 0,5%", br_money(d["adicional_05_mensal"].sum()), "Separado do consolidado", "kpi-blue"),
    ]
    kpi_html = "<div class='kpi-grid'>"
    for title, val, foot, cls in kpis_filial:
        kpi_html += f"<div class='kpi-card {cls}'><div class='kpi-title'>{title}</div><div class='kpi-value'>{val}</div><div class='kpi-foot'>{foot}</div></div>"
    kpi_html += "</div>"
    st.markdown(kpi_html, unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown("<div class='section-title'>Colaboradores da filial</div>", unsafe_allow_html=True)
        busca = st.text_input("Pesquisar por Nome / CPF / Matrícula", key="busca_drilldown_filial")
        d_view = d.copy()
        if busca.strip():
            b = busca.strip().upper()
            d_view = d_view[
                d_view["colaborador"].astype(str).str.upper().str.contains(b, na=False)
                | d_view["cpf"].astype(str).str.upper().str.contains(b, na=False)
                | d_view["cadastro"].astype(str).str.contains(b, na=False)
            ]

        if not d_view.empty:
            st.plotly_chart(bar_top_colaboradores(d_view, top=10), use_container_width=True)
        detalhe = d_view[[
            "cadastro", "colaborador", "cpf",
            "base_fgts_mensal", "valor_fgts_mensal", "valor_fgts_13", "valor_fgts_consolidado"
        ]].copy()
        for c in ["base_fgts_mensal", "valor_fgts_mensal", "valor_fgts_13", "valor_fgts_consolidado"]:
            detalhe[c] = detalhe[c].map(br_money)
        detalhe.columns = ["Matrícula", "Colaborador", "CPF", "Base FGTS", "FGTS Mensal", "FGTS 13º", "FGTS Consolidado"]
        render_clean_table(detalhe, height=430)
        st.download_button(
            "📥 Exportar filial para Excel",
            data=gerar_excel_download(d_view),
            file_name=f"fgts_filial_{empresa_codigo}_{filial_codigo}_{competencia}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
        )


def render_drilldown_empresa(base_df: pd.DataFrame, empresa_codigo: int, competencia: str) -> None:
    """Drill-down direto: Empresa → Colaborador."""
    d = base_df[base_df["empresa_codigo"] == int(empresa_codigo)].copy()
    if d.empty:
        st.warning("Empresa não encontrada nos filtros atuais.")
        if st.button("← Voltar para visão geral", use_container_width=False):
            st.session_state.selected_empresa_codigo = None
            st.rerun()
        return

    empresa_nome = str(d["empresa_nome"].iloc[0])

    st.markdown(
        f"""
        <div class='drill-box'>
            <div class='drill-title'>Empresa selecionada: <span class='drill-highlight'>{empresa_nome} | Competência: {competencia[5:7]}/{competencia[0:4]}</span></div>
            {breadcrumb_html('Visão geral', empresa_nome, 'Colaboradores')}
        </div>
        """,
        unsafe_allow_html=True,
    )
    qtd_colaboradores = d["cadastro"].nunique()
    base_fgts_total = d["base_fgts_mensal"].sum() + d["base_fgts_13"].sum()
    kpi = {
        "colaboradores": qtd_colaboradores,
        "base_total": base_fgts_total,
        "fgts_mensal_total": d["base_fgts_13"].sum(),
        "fgts_13_total": d["valor_fgts_13"].sum(),
        "consolidado": d["valor_fgts_consolidado"].sum(),
        "media_base": (base_fgts_total / qtd_colaboradores) if qtd_colaboradores else 0,
    }
    kpis_drill = [
        ("Colaboradores", br_number(kpi["colaboradores"]), "Ativos na empresa", "kpi-blue"),
        ("Base FGTS Total", br_money(kpi["base_total"]), "Mensal + 13º", "kpi-blue"),
        ("FGTS Total Consolidado", br_money(kpi["consolidado"]), "Mensal + 13º", "kpi-green"),
        ("FGTS Mensal Total", br_money(kpi["fgts_mensal_total"]), "Empresa selecionada | Fgts Mensal", "kpi-orange"),
        ("FGTS 13º Total", br_money(kpi["fgts_13_total"]), "Empresa selecionada | Fgts 13º", "kpi-purple"),
        ("Média Base FGTS / Colab.", br_money(kpi["media_base"]), "Base média mensal", "kpi-cyan"),
    ]
    with st.container(border=True):
        busca_local = str(st.session_state.get("busca_drilldown_empresa", ""))
        d_view = d.copy()
        if busca_local.strip():
            b = busca_local.strip().upper()
            d_view = d_view[
                d_view["colaborador"].astype(str).str.upper().str.contains(b, na=False)
                | d_view["cpf"].astype(str).str.upper().str.contains(b, na=False)
                | d_view["cadastro"].astype(str).str.contains(b, na=False)
            ]

        if not d_view.empty:
            st.plotly_chart(bar_top_colaboradores(d_view, top=10), use_container_width=True)
        else:
            st.info("Nenhum colaborador encontrado para a pesquisa informada.")

        # Botão real do Streamlit: volta para a tela anterior sem perder/carregar dados novamente.
        voltar_cols = st.columns([5, 1])
        with voltar_cols[1]:
            if st.button("← Voltar", key="btn_voltar_empresa", type="primary", use_container_width=True):
                st.session_state.selected_empresa_codigo = None
                st.session_state.selected_filial_codigo = None
                st.rerun()

        st.text_input("Pesquisar por Nome / CPF / Matrícula", key="busca_drilldown_empresa")

        detalhe = d_view[[
            "cadastro", "colaborador", "cpf",
            "base_fgts_mensal", "valor_fgts_mensal", "valor_fgts_13", "valor_fgts_consolidado"
        ]].copy()
        for c in ["base_fgts_mensal", "valor_fgts_mensal", "valor_fgts_13", "valor_fgts_consolidado"]:
            detalhe[c] = detalhe[c].map(br_money)
        detalhe.columns = ["Matrícula", "Colaborador", "CPF", "Base FGTS", "FGTS Mensal", "FGTS 13º", "FGTS Consolidado"]
        render_clean_table(detalhe, height=470)

        st.download_button(
            "📥 Exportar colaboradores da empresa para Excel",
            data=gerar_excel_download(d_view),
            file_name=f"fgts_empresa_colaboradores_{empresa_codigo}_{competencia}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
        )

# =============================
# App
# =============================
ensure_data_dir()

if "mostrar_filtros" not in st.session_state:
    st.session_state.mostrar_filtros = True
if "mostrar_importacao" not in st.session_state:
    st.session_state.mostrar_importacao = False
if "mostrar_importacao_retorno" not in st.session_state:
    st.session_state.mostrar_importacao_retorno = False
if "mostrar_historico" not in st.session_state:
    st.session_state.mostrar_historico = False
if "dados_carregados" not in st.session_state:
    # O dashboard deve iniciar em branco. Os dados só aparecem após importar uma planilha
    # ou clicar em Carregar histórico existente.
    st.session_state.dados_carregados = False
if "selected_empresa_codigo" not in st.session_state:
    st.session_state.selected_empresa_codigo = None
if "selected_filial_codigo" not in st.session_state:
    st.session_state.selected_filial_codigo = None

# Botão Voltar em HTML usa query param para limpar o drill-down.
try:
    if st.query_params.get("voltar") == "1":
        st.session_state.selected_empresa_codigo = None
        st.session_state.selected_filial_codigo = None
        st.query_params.clear()
        st.rerun()
except Exception:
    pass

# Carrega dados somente quando o usuário solicitar.
if st.session_state.dados_carregados and COLAB_CSV.exists():
    df = load_data(COLAB_CSV)
else:
    df = pd.DataFrame()

if RETORNO_ESOCIAL_CSV.exists():
    retorno_esocial_df = load_retorno_esocial(RETORNO_ESOCIAL_CSV)
else:
    retorno_esocial_df = pd.DataFrame()


st.markdown("<div class='filter-panel'><div class='panel-title'>⚙️ AÇÕES DO DASHBOARD</div>", unsafe_allow_html=True)
a1, a2, a3 = st.columns([1.3, 1.3, 1.3])
with a1:
    if st.button("📥 Importar planilha", use_container_width=True, type="primary"):
        st.session_state.mostrar_importacao = not st.session_state.mostrar_importacao
        st.rerun()
with a2:
    if st.button("📤 Importar retorno eSocial", use_container_width=True, key="btn_importar_retorno_esocial_acoes"):
        st.session_state.mostrar_importacao_retorno = not st.session_state.mostrar_importacao_retorno
        st.rerun()
with a3:
    if st.button("🙈 Ocultar filtros" if st.session_state.mostrar_filtros else "👁️ Mostrar filtros", use_container_width=True):
        st.session_state.mostrar_filtros = not st.session_state.mostrar_filtros
        st.rerun()
st.markdown("</div>", unsafe_allow_html=True)

# =============================
# Painel de importação visível no topo
# =============================
if st.session_state.mostrar_importacao or df.empty:
    st.markdown("<div class='panel'><div class='panel-title'>📥 IMPORTAR NOVA PLANILHA FGTS</div>", unsafe_allow_html=True)
    st.write("Envie a nova planilha do FGTS exportada do sistema. O dashboard vai ler **somente a aba Plan1**, tratar os dados e gravar a competência no histórico.")
    up = st.file_uploader("Selecione o arquivo Excel do FGTS", type=["xlsx", "xlsm"], key="upload_fgts_topo")
    cimp1, cimp2, cimp3, cimp4 = st.columns([1.2, 1.25, 1.55, 2.2])
    with cimp1:
        replace = st.checkbox("Substituir competência já existente", value=True)
    with cimp2:
        processar = st.button("🚀 Processar planilha", type="primary", disabled=up is None, use_container_width=True)
    with cimp3:
        if st.button("📤 Importar retorno eSocial", use_container_width=True, key="btn_importar_retorno_esocial_tela_importacao"):
            st.session_state.mostrar_importacao_retorno = True
            st.rerun()
    with cimp4:
        st.caption("Use o retorno eSocial S-5003 para conciliar bases e valores de FGTS mensal/13º com o relatório do Senior.")

    if processar and up is not None:
        try:
            safe_name = up.name.replace("/", "_").replace("\\", "_")
            target = IMPORT_DIR / safe_name
            target.write_bytes(up.getvalue())
            # Nova planilha FGTS começa uma análise limpa, sem vestígios de competências/retornos anteriores.
            limpar_base_fgts_e_retorno()
            with st.spinner("Lendo Plan1 e tratando os dados..."):
                df_new, totals_new = parse_plan1(target)
            if df_new.empty:
                st.error("A Plan1 foi lida, mas nenhum colaborador foi identificado. Confira se o layout da planilha é o mesmo do modelo original.")
            else:
                old_count, new_count, comp = save_history(df_new, totals_new, replace_same_competence=replace)
                st.success(f"Competência {comp} importada com sucesso. Registros no histórico: {new_count} colaboradores.")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Colaboradores importados", len(df_new))
                m2.metric("Empresas", df_new["empresa_codigo"].nunique())
                m3.metric("Filiais", df_new[["empresa_codigo", "filial"]].drop_duplicates().shape[0])
                m4.metric("FGTS consolidado", br_money((df_new["valor_fgts_mensal"].sum() + df_new["valor_fgts_13"].sum())))
                st.info("A base foi atualizada. O dashboard será recarregado automaticamente.")
                load_data.clear()
                st.session_state.dados_carregados = True
                st.session_state.mostrar_importacao = False
                st.rerun()
        except Exception as e:
            st.error(f"Erro ao importar a planilha: {e}")
    st.markdown("</div>", unsafe_allow_html=True)

if st.session_state.mostrar_importacao_retorno:
    st.markdown("<div class='panel'><div class='panel-title'>📤 IMPORTAR RETORNO eSOCIAL S-5003</div>", unsafe_allow_html=True)
    st.write("Envie o relatório de retorno do eSocial gerado após o fechamento da competência. O dashboard vai identificar o padrão S-5003 e preparar a conciliação das bases e valores de FGTS.")
    up_ret = st.file_uploader("Selecione o relatório de retorno do eSocial", type=["xlsx", "xlsm"], key="upload_retorno_esocial")
    r1, r2 = st.columns([1.2, 3.6])
    with r1:
        processar_ret = st.button("🚀 Processar retorno", type="primary", disabled=up_ret is None, use_container_width=True)
    with r2:
        st.caption("Padrão esperado: relatório S-5003 - Informações do FGTS por Trabalhador, com Nome, Tipo/Cad, CPF, Tipo, Base Cálculo e Valor FGTS.")

    if processar_ret and up_ret is not None:
        try:
            safe_name = up_ret.name.replace("/", "_").replace("\\", "_")
            target = IMPORT_DIR / safe_name
            target.write_bytes(up_ret.getvalue())
            # Novo retorno eSocial substitui totalmente o retorno anterior usado na conciliação.
            limpar_retorno_esocial()
            with st.spinner("Lendo retorno S-5003 do eSocial..."):
                df_ret = parse_retorno_esocial_s5003(target)
            if df_ret.empty:
                st.error("Não consegui identificar linhas de trabalhadores no padrão S-5003. Confira se o arquivo é o relatório de retorno correto.")
            else:
                salvar_retorno_esocial(df_ret)
                st.session_state.mostrar_importacao_retorno = False
                st.success(f"Retorno eSocial importado com sucesso: {len(df_ret)} linhas de FGTS identificadas.")
                st.rerun()
        except Exception as e:
            st.error(f"Erro ao importar retorno eSocial: {e}")
    st.markdown("</div>", unsafe_allow_html=True)

if df.empty:
    st.markdown("<div class='panel'><div class='panel-title'>📊 DASHBOARD EM BRANCO</div>", unsafe_allow_html=True)
    st.info("O dashboard inicia sem dados carregados. Importe a planilha FGTS do Senior e, quando necessário, use o botão **📤 Importar retorno eSocial** para carregar o S-5003 da conciliação.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# =============================
# Filtros horizontais
# =============================
competencias = sorted(df["competencia"].dropna().astype(str).unique().tolist(), reverse=True)
base_filtragem = df.copy()

# Mantém os filtros aplicados mesmo quando o painel é ocultado.
# Sem isso, o Streamlit faz aquela gracinha de esconder o widget e fingir que nada foi selecionado.
if "persist_competencia" not in st.session_state or st.session_state.persist_competencia not in competencias:
    st.session_state.persist_competencia = competencias[0]
if "persist_empresa" not in st.session_state:
    st.session_state.persist_empresa = "Todos"
if "persist_busca" not in st.session_state:
    st.session_state.persist_busca = ""

empresa_sel = st.session_state.persist_empresa
busca = st.session_state.persist_busca
competencia = st.session_state.persist_competencia

if st.session_state.mostrar_filtros:
    st.markdown("<div class='filter-panel'><div class='panel-title'>🔎 FILTROS DE ANÁLISE</div>", unsafe_allow_html=True)
    f1, f2, f4 = st.columns([0.95, 1.9, 1.55])

    comp_index = competencias.index(st.session_state.persist_competencia) if st.session_state.persist_competencia in competencias else 0
    competencia = f1.selectbox("Competência", competencias, index=comp_index, key="filtro_competencia")
    st.session_state.persist_competencia = competencia

    base_tmp = base_filtragem[base_filtragem["competencia"].astype(str) == competencia].copy()

    empresas = ["Todos"] + sorted(base_tmp["empresa_label"].unique().tolist())
    if st.session_state.persist_empresa not in empresas:
        st.session_state.persist_empresa = "Todos"
    emp_index = empresas.index(st.session_state.persist_empresa) if st.session_state.persist_empresa in empresas else 0
    empresa_sel = f2.selectbox("Empresa", empresas, index=emp_index, key="filtro_empresa")
    st.session_state.persist_empresa = empresa_sel

    if empresa_sel != "Todos":
        base_tmp = base_tmp[base_tmp["empresa_label"] == empresa_sel]

    busca = f4.text_input("Colaborador / CPF / cadastro", value=st.session_state.persist_busca, key="filtro_busca")
    st.session_state.persist_busca = busca

    if busca.strip():
        b = busca.strip().upper()
        base_tmp = base_tmp[
            base_tmp["colaborador"].astype(str).str.upper().str.contains(b, na=False)
            | base_tmp["cpf"].astype(str).str.upper().str.contains(b, na=False)
            | base_tmp["cadastro"].astype(str).str.contains(b, na=False)
        ]

    st.markdown("</div>", unsafe_allow_html=True)
    base = base_tmp.copy()
else:
    competencia = st.session_state.persist_competencia if st.session_state.persist_competencia in competencias else competencias[0]
    base_tmp = base_filtragem[base_filtragem["competencia"].astype(str) == competencia].copy()

    empresas = ["Todos"] + sorted(base_tmp["empresa_label"].unique().tolist())
    empresa_sel = st.session_state.persist_empresa if st.session_state.persist_empresa in empresas else "Todos"
    if empresa_sel != "Todos":
        base_tmp = base_tmp[base_tmp["empresa_label"] == empresa_sel]

    busca = st.session_state.persist_busca
    if str(busca).strip():
        b = str(busca).strip().upper()
        base_tmp = base_tmp[
            base_tmp["colaborador"].astype(str).str.upper().str.contains(b, na=False)
            | base_tmp["cpf"].astype(str).str.upper().str.contains(b, na=False)
            | base_tmp["cadastro"].astype(str).str.contains(b, na=False)
        ]

    base = base_tmp.copy()

if base.empty:
    st.warning("Nenhum registro encontrado para os filtros selecionados.")
    st.stop()

# =============================
# Cálculos
# =============================
# Card BASE FGTS TOTAL:
# - com empresa selecionada: mostra a base total somente daquela empresa na competência;
# - sem empresa selecionada: mostra a base total de todas as empresas na competência.
# Regra correta: BASE FGTS TOTAL = Base FGTS Mensal + Base FGTS 13º.
# Esse card não é reduzido pelos filtros de colaborador, CPF ou matrícula.
base_kpi_empresa = df[df["competencia"].astype(str) == competencia].copy()
if empresa_sel != "Todos":
    base_kpi_empresa = base_kpi_empresa[base_kpi_empresa["empresa_label"] == empresa_sel]
base_fgts_total_card = (
    base_kpi_empresa["base_fgts_mensal"].sum() + base_kpi_empresa["base_fgts_13"].sum()
) if not base_kpi_empresa.empty else 0
base_fgts_13_card = base_kpi_empresa["base_fgts_13"].sum() if not base_kpi_empresa.empty else 0
base_fgts_total_foot = ("Empresa selecionada" if empresa_sel != "Todos" else "Todas as empresas") + " | Mensal + 13º"
base_fgts_13_foot = ("Empresa selecionada" if empresa_sel != "Todos" else "Todas as empresas") + " | Fgts Mensal"

totals = {
    "empresas": base["empresa_codigo"].nunique(),
    "filiais": base[["empresa_codigo", "filial"]].drop_duplicates().shape[0],
    "colaboradores": base["cadastro"].nunique(),
    "base_fgts_mensal": base["base_fgts_mensal"].sum(),
    "valor_fgts_mensal": base["valor_fgts_mensal"].sum(),
    "valor_fgts_13": base["valor_fgts_13"].sum(),
    "valor_fgts_consolidado": base["valor_fgts_consolidado"].sum(),
    "adicional_05_mensal": base["adicional_05_mensal"].sum(),
    "media_fgts": base["valor_fgts_consolidado"].mean(),
    # Média correta: Base FGTS Total (mensal + 13º) / quantidade de colaboradores filtrados.
    "media_base": ((base["base_fgts_mensal"].sum() + base["base_fgts_13"].sum()) / base["cadastro"].nunique()) if base["cadastro"].nunique() else 0,
}

emp = base.groupby(["empresa_codigo", "empresa_nome"], as_index=False).agg(
    empresa_nome_original=("empresa_nome_original", "first"),
    qtd_colaboradores=("cadastro", "nunique"),
    base_fgts_mensal=("base_fgts_mensal", "sum"),
    valor_fgts_mensal=("valor_fgts_mensal", "sum"),
    valor_fgts_13=("valor_fgts_13", "sum"),
    valor_fgts_consolidado=("valor_fgts_consolidado", "sum"),
    adicional_05_mensal=("adicional_05_mensal", "sum"),
)
fil = base.groupby(["empresa_codigo", "empresa_nome", "filial", "filial_nome"], as_index=False).agg(
    empresa_nome_original=("empresa_nome_original", "first"),
    qtd_colaboradores=("cadastro", "nunique"),
    base_fgts_mensal=("base_fgts_mensal", "sum"),
    valor_fgts_mensal=("valor_fgts_mensal", "sum"),
    valor_fgts_13=("valor_fgts_13", "sum"),
    valor_fgts_consolidado=("valor_fgts_consolidado", "sum"),
)
fil["filial_exibicao"] = "Filial " + fil["filial"].astype(str) + " | " + fil["empresa_nome"].str.slice(0, 28)

# =============================
# Cabeçalho executivo da competência filtrada
# =============================
logo_uri = image_file_to_data_uri(LOGO_PATH)
st.markdown(f"""
<div class="header-hero">
  <div class="header-hero-box header-hero-logo">
    {f'<img src="{logo_uri}" alt="Grupo Equatorial Energia">' if logo_uri else '<div class="header-hero-main" style="font-size:18px;">GRUPO<br>EQUATORIAL</div>'}
  </div>
  <div class="header-hero-box header-hero-title">
    <div class="header-hero-main">FGTS</div>
    <div class="header-hero-sub">Dashboard de Recolhimento</div>
  </div>
  <div class="header-hero-box">
    <div class="header-hero-stat-icon">🏢</div>
    <div class="header-hero-stat-text">
      <div class="header-hero-stat-value">{totals['empresas']}</div>
      <div class="header-hero-stat-label">Empresas</div>
    </div>
  </div>
  <div class="header-hero-box">
    <div class="header-hero-stat-icon">👥</div>
    <div class="header-hero-stat-text">
      <div class="header-hero-stat-value">{totals['colaboradores']}</div>
      <div class="header-hero-stat-label">Colaboradores</div>
    </div>
  </div>
  <div class="header-hero-box">
    <div class="header-hero-stat-icon">📅</div>
    <div class="header-hero-stat-text">
      <div class="header-hero-stat-value">{competencia[5:7]}/{competencia[0:4]}</div>
      <div class="header-hero-stat-label">Competência</div>
    </div>
  </div>
  <div class="header-hero-box">
    <div class="header-hero-stat-icon">🕒</div>
    <div class="header-hero-stat-text">
      <div class="header-hero-stat-value">{datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
      <div class="header-hero-stat-label">Última atualização</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

kpis = [
    ("BASE FGTS TOTAL", br_money(base_fgts_total_card), base_fgts_total_foot, "kpi-blue"),
    ("FGTS TOTAL CONSOLIDADO", br_money(totals["valor_fgts_consolidado"]), "Mensal + 13º", "kpi-green"),
    ("FGTS MENSAL TOTAL", br_money(base_fgts_13_card), base_fgts_13_foot, "kpi-orange"),
    ("FGTS 13º TOTAL", br_money(totals["valor_fgts_13"]), ("Empresa selecionada" if empresa_sel != "Todos" else "Todas as empresas") + " | Fgts 13º", "kpi-purple"),
    ("MÉDIA BASE FGTS / COLAB.", br_money(totals["media_base"]), "Base média mensal", "kpi-blue"),
    ("MÉDIA FGTS / COLAB.", br_money(totals["media_fgts"]), "Média consolidada", "kpi-cyan"),
]

kpi_html = "<div class='kpi-grid'>"
for title, val, foot, cls in kpis:
    kpi_html += f"<div class='kpi-card {cls}'><div class='kpi-title'>{title}</div><div class='kpi-value'>{val}</div><div class='kpi-foot'>{foot}</div></div>"
kpi_html += "</div>"
st.markdown(kpi_html, unsafe_allow_html=True)

with st.container(border=True):
    render_conciliacao_fgts(base, retorno_esocial_df, competencia, empresa_sel, busca)

# Drill-down Empresa → Colaborador
if st.session_state.selected_empresa_codigo is not None:
    render_drilldown_empresa(base, int(st.session_state.selected_empresa_codigo), competencia)
    st.stop()

# Gráfico principal interativo: Empresa → Colaborador.
# O gráfico de rosca/distribuição foi removido conforme solicitado.
with st.container(border=True):
    fig_emp_drill = bar_empresa_drill(emp)
    emp_ordem = emp.sort_values("valor_fgts_consolidado", ascending=False).reset_index(drop=True)

    empresa_selecionada = None

    # Usa o recurso nativo do Streamlit para seleção por clique no Plotly.
    # Isso mantém o gráfico em barras VERTICAIS e evita o componente externo
    # streamlit-plotly-events, que pode redesenhar o gráfico como horizontal.
    evt_emp = st.plotly_chart(
        fig_emp_drill,
        use_container_width=True,
        key="chart_empresa_drill_vertical",
        on_select="rerun",
        selection_mode="points",
    )
    empresa_sel_idx = get_plotly_selected_point_index(evt_emp)
    if empresa_sel_idx is not None and 0 <= int(empresa_sel_idx) < len(emp_ordem):
        empresa_selecionada = int(emp_ordem.iloc[int(empresa_sel_idx)]["empresa_codigo"])

    if empresa_selecionada is not None:
        st.session_state.selected_empresa_codigo = empresa_selecionada
        st.session_state.selected_filial_codigo = None
        st.rerun()


# Gráfico FGTS por Filial removido conforme solicitado.

with st.container(border=True):
    st.plotly_chart(bar_top_colaboradores(base, top=10), use_container_width=True)

# Histórico aparece no próprio dashboard, ao clicar no botão da barra superior
if st.session_state.mostrar_historico:
    with st.container(border=True):
        st.markdown("<div class='section-title'>📈 HISTÓRICO / COMPARATIVO DE COMPETÊNCIAS</div>", unsafe_allow_html=True)
        h1, h2 = st.columns([1.4, 1], gap="medium")
        with h1:
            fig_hist, hist = line_historico(df)
            st.plotly_chart(fig_hist, use_container_width=True)
        with h2:
            hist_show = hist.copy()
            hist_show["valor_fgts_consolidado"] = hist_show["valor_fgts_consolidado"].map(br_money)
            hist_show["valor_fgts_mensal"] = hist_show["valor_fgts_mensal"].map(br_money)
            hist_show["valor_fgts_13"] = hist_show["valor_fgts_13"].map(br_money)
            hist_show["base_fgts_mensal"] = hist_show["base_fgts_mensal"].map(br_money)
            hist_show = hist_show[["competencia", "valor_fgts_consolidado", "valor_fgts_mensal", "valor_fgts_13", "base_fgts_mensal", "colaboradores"]]
            hist_show.columns = ["Competência", "FGTS Consolidado", "FGTS Mensal", "FGTS 13º", "Base FGTS", "Colaboradores"]
            st.dataframe(hist_show, use_container_width=True, hide_index=True, height=360)

with st.container(border=True):
    st.markdown("<div class='section-title'>DETALHAMENTO DOS COLABORADORES</div>", unsafe_allow_html=True)
    detalhe = base[[
        "empresa_label", "cadastro", "colaborador", "cpf",
        "base_fgts_mensal", "valor_fgts_mensal", "base_fgts_13", "valor_fgts_13", "valor_fgts_consolidado"
    ]].copy()
    for c in ["base_fgts_mensal", "valor_fgts_mensal", "base_fgts_13", "valor_fgts_13", "valor_fgts_consolidado"]:
        detalhe[c] = detalhe[c].map(br_money)
    detalhe.columns = ["Empresa", "Cadastro", "Colaborador", "CPF", "Base FGTS Mensal", "FGTS Mensal", "Base FGTS 13º", "FGTS 13º", "FGTS Consolidado"]
    render_clean_table(detalhe, height=390)

    st.download_button("📥 Exportar base filtrada para Excel", data=gerar_excel_download(base, emp, fil), file_name=f"fgts_dashboard_filtrado_{competencia}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")

st.markdown(f"<div class='footer-note'>Fonte: Plan1 | Competência: {competencia} | Valores em reais | Dashboard gerado em Python + Streamlit</div>", unsafe_allow_html=True)
