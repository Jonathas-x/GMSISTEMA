import os
from pathlib import Path
import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_FILE = BASE_DIR / "base_financeira_template.xlsx"
DATA_FILE = Path(os.getenv("FINANCE_FILE", DEFAULT_FILE))

COLUNAS = [
    "Data",
    "Descrição",
    "Cartão",
    "Parcela",
    "Valor (R$)",
    "Mês da fatura",
    "Pago",
]

CARTOES_PADRAO = ["CARREFOUR", "ITAU", "MERCADO PAGO", "NUBANK", "SANTANDER M", "SANTANDER V"]
STATUS_PADRAO = ["Não", "Sim"]


def criar_base_vazia(caminho: Path) -> None:
    df = pd.DataFrame(columns=COLUNAS)
    resumo = gerar_resumo(df)
    config = pd.DataFrame({"Cartões": CARTOES_PADRAO, "Pago": ["Sim", "Não", None, None, None, None]})
    with pd.ExcelWriter(caminho, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Lançamentos", index=False)
        resumo.to_excel(writer, sheet_name="Resumo Mensal", index=False)
        config.to_excel(writer, sheet_name="Config", index=False)


def garantir_base() -> None:
    if not DATA_FILE.exists():
        criar_base_vazia(DATA_FILE)


def normalizar_pago(valor) -> str:
    texto = str(valor).strip().lower()
    if texto in ["sim", "s", "true", "1"]:
        return "Sim"
    return "Não"


def validar_mes_fatura(valor: str) -> bool:
    valor = str(valor).strip()
    return bool(pd.Series([valor]).str.match(r"^\d{4}-\d{2}$").iloc[0])


def formatar_parcela(valor) -> str:
    texto = str(valor).strip()

    if texto in ["", "nan", "None"]:
        return ""

    texto = texto.replace(" ", "").replace("\\", "/").replace("-", "/")

    if "/" in texto:
        partes = texto.split("/")
        if len(partes) == 2:
            try:
                atual = int(float(partes[0]))
                total = int(float(partes[1]))
                return f"{atual:02d}/{total:02d}"
            except ValueError:
                return texto

    try:
        numero = int(float(texto))
        return f"{numero:02d}/{numero:02d}"
    except ValueError:
        return texto


def resumo_linha_lancamento(row) -> str:
    cartao = row["Cartão"] or "-"
    fatura = row["Mês da fatura"] or "-"
    parcela = formatar_parcela(row["Parcela"])
    pago = row["Pago"] or "Não"

    itens = [f"💳 {cartao}", f"📅 {fatura}"]
    if parcela:
        itens.append(f"🔢 {parcela}")
    itens.append(f"✅ {pago}")

    return " • ".join(itens)


def carregar_dados() -> tuple[pd.DataFrame, pd.DataFrame]:
    garantir_base()
    try:
        lanc = pd.read_excel(DATA_FILE, sheet_name="Lançamentos")
    except Exception:
        lanc = pd.DataFrame(columns=COLUNAS)

    for col in COLUNAS:
        if col not in lanc.columns:
            lanc[col] = None

    lanc = lanc[COLUNAS].copy()
    lanc["Descrição"] = lanc["Descrição"].fillna("").astype(str)
    lanc["Cartão"] = lanc["Cartão"].fillna("").astype(str)
    lanc["Parcela"] = lanc["Parcela"].fillna("").apply(formatar_parcela)
    lanc["Mês da fatura"] = lanc["Mês da fatura"].fillna("").astype(str)
    lanc["Pago"] = lanc["Pago"].apply(normalizar_pago)
    lanc["Valor (R$)"] = pd.to_numeric(lanc["Valor (R$)"], errors="coerce").fillna(0.0)
    lanc["Data"] = lanc["Data"].astype(str).replace({"NaT": "", "nan": ""}).fillna("")

    lanc = lanc[(lanc["Descrição"].str.strip() != "") | (lanc["Valor (R$)"] != 0)].copy()
    resumo = gerar_resumo(lanc)
    return lanc, resumo


def gerar_resumo(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        meses = pd.period_range("2026-01", periods=12, freq="M").astype(str)
        return pd.DataFrame({
            "Mês": meses,
            "Total gasto": 0.0,
            "Total pago": 0.0,
            "Total pendente": 0.0,
        })

    tmp = df.copy()
    tmp["Pago"] = tmp["Pago"].apply(normalizar_pago)
    meses_validos = tmp["Mês da fatura"].astype(str).str.match(r"^\d{4}-\d{2}$")
    tmp = tmp[meses_validos].copy()

    if tmp.empty:
        return pd.DataFrame(columns=["Mês", "Total gasto", "Total pago", "Total pendente"])

    gasto = (
        tmp.groupby("Mês da fatura", as_index=False)["Valor (R$)"]
        .sum()
        .rename(columns={"Mês da fatura": "Mês", "Valor (R$)": "Total gasto"})
    )

    pago = (
        tmp[tmp["Pago"] == "Sim"]
        .groupby("Mês da fatura", as_index=False)["Valor (R$)"]
        .sum()
        .rename(columns={"Mês da fatura": "Mês", "Valor (R$)": "Total pago"})
    )

    resumo = gasto.merge(pago, on="Mês", how="left").fillna(0)
    resumo["Total pendente"] = resumo["Total gasto"] - resumo["Total pago"]
    resumo = resumo.sort_values("Mês").reset_index(drop=True)
    return resumo


def salvar_dados(df: pd.DataFrame) -> None:
    df = df.copy()

    for col in COLUNAS:
        if col not in df.columns:
            df[col] = ""

    df = df[COLUNAS].copy()
    df["Descrição"] = df["Descrição"].fillna("").astype(str)
    df["Cartão"] = df["Cartão"].fillna("").astype(str)
    df["Parcela"] = df["Parcela"].fillna("").apply(formatar_parcela)
    df["Mês da fatura"] = df["Mês da fatura"].fillna("").astype(str)
    df["Pago"] = df["Pago"].apply(normalizar_pago)
    df["Valor (R$)"] = pd.to_numeric(df["Valor (R$)"], errors="coerce").fillna(0.0)
    df["Data"] = df["Data"].fillna("").astype(str)

    df = df[(df["Descrição"].str.strip() != "") | (df["Valor (R$)"] != 0)].copy()

    resumo = gerar_resumo(df)
    config = pd.DataFrame({"Cartões": CARTOES_PADRAO, "Pago": ["Sim", "Não", None, None, None, None]})

    with pd.ExcelWriter(DATA_FILE, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Lançamentos", index=False)
        resumo.to_excel(writer, sheet_name="Resumo Mensal", index=False)
        config.to_excel(writer, sheet_name="Config", index=False)


def moeda(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def eh_mobile() -> bool:
    return st.session_state.get("mobile_view", True)


st.set_page_config(
    page_title="Controle Financeiro",
    page_icon="💳",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
.block-container {
    padding-top: 1rem;
    padding-bottom: 2rem;
    max-width: 780px;
}
div[data-testid="stMetric"] {
    padding: 10px 12px;
    border-radius: 12px;
    background: rgba(255,255,255,0.03);
}
div.stButton > button {
    width: 100%;
    border-radius: 10px;
    height: 44px;
}
div[data-testid="stDownloadButton"] > button {
    width: 100%;
    border-radius: 10px;
    height: 44px;
}
.linha-resumo {
    font-size: 0.95rem;
    line-height: 1.5;
    word-break: normal;
    overflow-wrap: break-word;
}
.valor-direita {
    text-align: right;
    font-weight: 700;
    white-space: nowrap;
    margin-top: 4px;
}
</style>
""", unsafe_allow_html=True)

st.title("💳 Controle Financeiro")
st.caption("Sistema com base em Excel")

lancamentos, resumo = carregar_dados()

with st.sidebar:
    st.header("Opções")
    st.checkbox("Modo mobile", value=True, key="mobile_view")
    st.write(f"Arquivo: `{DATA_FILE.name}`")
    if st.button("Recarregar dados"):
        st.rerun()

mobile = eh_mobile()

aba1, aba2, aba3 = st.tabs(["Dashboard", "Lançamentos", "Novo"])

with aba1:
    total_gasto = float(lancamentos["Valor (R$)"].sum()) if not lancamentos.empty else 0.0
    total_pago = float(lancamentos.loc[lancamentos["Pago"] == "Sim", "Valor (R$)"].sum()) if not lancamentos.empty else 0.0
    total_pendente = total_gasto - total_pago

    if mobile:
        st.metric("Total gasto", moeda(total_gasto))
        st.metric("Total pago", moeda(total_pago))
        st.metric("Total pendente", moeda(total_pendente))
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total gasto", moeda(total_gasto))
        c2.metric("Total pago", moeda(total_pago))
        c3.metric("Total pendente", moeda(total_pendente))

    st.subheader("Filtros")

    if mobile:
        filtro_cartao = st.selectbox(
            "Cartão",
            ["Todos"] + sorted([c for c in lancamentos["Cartão"].dropna().unique().tolist() if str(c).strip()])
        )
        filtro_mes = st.selectbox(
            "Mês",
            ["Todos"] + sorted([m for m in lancamentos["Mês da fatura"].dropna().unique().tolist() if str(m).strip()])
        )
        filtro_pago = st.selectbox("Status", ["Todos", "Sim", "Não"])
    else:
        fc1, fc2, fc3 = st.columns(3)
        filtro_cartao = fc1.selectbox(
            "Cartão",
            ["Todos"] + sorted([c for c in lancamentos["Cartão"].dropna().unique().tolist() if str(c).strip()])
        )
        filtro_mes = fc2.selectbox(
            "Mês",
            ["Todos"] + sorted([m for m in lancamentos["Mês da fatura"].dropna().unique().tolist() if str(m).strip()])
        )
        filtro_pago = fc3.selectbox("Status", ["Todos", "Sim", "Não"])

    filtrado = lancamentos.copy()
    if filtro_cartao != "Todos":
        filtrado = filtrado[filtrado["Cartão"] == filtro_cartao]
    if filtro_mes != "Todos":
        filtrado = filtrado[filtrado["Mês da fatura"] == filtro_mes]
    if filtro_pago != "Todos":
        filtrado = filtrado[filtrado["Pago"] == filtro_pago]

    st.subheader("Resumo mensal")
    st.dataframe(
        resumo.style.format({
            "Total gasto": lambda x: moeda(x),
            "Total pago": lambda x: moeda(x),
            "Total pendente": lambda x: moeda(x),
        }),
        use_container_width=True,
        hide_index=True,
    )

    if not resumo.empty:
        grafico = resumo.set_index("Mês")[["Total gasto", "Total pago", "Total pendente"]]
        st.bar_chart(grafico, use_container_width=True)

    st.subheader("Lançamentos")
    if filtrado.empty:
        st.info("Nenhum lançamento encontrado.")
    else:
        for _, row in filtrado.reset_index(drop=True).iterrows():
            descricao = row["Descrição"] or "Sem descrição"
            data_txt = row["Data"] or "-"
            linha_resumo = resumo_linha_lancamento(row)
            valor_formatado = moeda(float(row["Valor (R$)"]))

            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"**{descricao}**")
                    st.caption(data_txt)
                    st.markdown(
                        f"<div class='linha-resumo'>{linha_resumo}</div>",
                        unsafe_allow_html=True,
                    )
                with c2:
                    st.markdown(
                        f"<div class='valor-direita'>{valor_formatado}</div>",
                        unsafe_allow_html=True,
                    )

with aba2:
    st.subheader("Editar e apagar lançamentos")

    if lancamentos.empty:
        st.info("Ainda não há lançamentos cadastrados.")
    else:
        tabela_edicao = lancamentos.copy()
        tabela_edicao["Excluir"] = False

        editado = st.data_editor(
            tabela_edicao,
            use_container_width=True,
            num_rows="dynamic",
            hide_index=True,
            column_order=["Data", "Descrição", "Cartão", "Parcela", "Valor (R$)", "Mês da fatura", "Pago", "Excluir"],
            column_config={
                "Data": st.column_config.TextColumn("Data", width="small"),
                "Descrição": st.column_config.TextColumn("Descrição", width="medium"),
                "Cartão": st.column_config.SelectboxColumn(
                    "Cartão",
                    options=sorted(set(CARTOES_PADRAO + lancamentos["Cartão"].astype(str).tolist()))
                ),
                "Parcela": st.column_config.TextColumn("Parcela", help="Formato: 01/01", width="small"),
                "Valor (R$)": st.column_config.NumberColumn("Valor (R$)", format="%.2f", min_value=0.0),
                "Mês da fatura": st.column_config.TextColumn("Mês da fatura", help="Formato: AAAA-MM", width="small"),
                "Pago": st.column_config.SelectboxColumn("Pago", options=STATUS_PADRAO, required=True),
                "Excluir": st.column_config.CheckboxColumn("Excluir", help="Marque para apagar"),
            },
        )

        if st.button("Salvar alterações", type="primary"):
            excluir_marcados = editado["Excluir"].fillna(False)
            df_final = editado.loc[~excluir_marcados, COLUNAS].copy()
            df_final["Parcela"] = df_final["Parcela"].fillna("").apply(formatar_parcela)

            meses_invalidos = df_final["Mês da fatura"].astype(str).str.strip()
            meses_invalidos = meses_invalidos[(meses_invalidos != "") & (~meses_invalidos.str.match(r"^\d{4}-\d{2}$"))]

            if not meses_invalidos.empty:
                st.error("Existem meses inválidos. Use AAAA-MM.")
            else:
                salvar_dados(df_final)
                st.success("Alterações salvas com sucesso.")
                st.rerun()

        with open(DATA_FILE, "rb") as f:
            st.download_button(
                label="Baixar Excel atualizado",
                data=f.read(),
                file_name=DATA_FILE.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

with aba3:
    st.subheader("Adicionar lançamento")

    with st.form("novo_lancamento"):
        data = st.text_input("Data", placeholder="Ex.: 08/04/2026")
        descricao = st.text_input("Descrição")
        cartao = st.selectbox("Cartão", CARTOES_PADRAO)
        parcela = st.text_input("Parcela", placeholder="Ex.: 01/03")
        valor = st.number_input("Valor (R$)", min_value=0.0, step=1.0, format="%.2f")
        mes_fatura = st.text_input("Mês da fatura", placeholder="AAAA-MM")
        pago = st.selectbox("Pago", STATUS_PADRAO)

        enviar = st.form_submit_button("Adicionar lançamento")

    if enviar:
        if not descricao.strip():
            st.error("Preencha a descrição.")
        elif not mes_fatura.strip():
            st.error("Preencha o mês da fatura.")
        elif not validar_mes_fatura(mes_fatura):
            st.error("Mês da fatura inválido. Use AAAA-MM.")
        else:
            novo = pd.DataFrame([
                {
                    "Data": data.strip(),
                    "Descrição": descricao.strip(),
                    "Cartão": cartao,
                    "Parcela": formatar_parcela(parcela),
                    "Valor (R$)": float(valor),
                    "Mês da fatura": mes_fatura.strip(),
                    "Pago": pago,
                }
            ])
            atualizado = pd.concat([lancamentos, novo], ignore_index=True)
            salvar_dados(atualizado)
            st.success("Lançamento adicionado com sucesso.")
            st.rerun()