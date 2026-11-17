"""Interface do ZelaCidade (Streamlit).

Rodar a partir da raiz do projeto:
    streamlit run app/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

import dados

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "genai"))
from assistente import Assistente  # noqa: E402

st.set_page_config(page_title="ZelaCidade", page_icon="🏙️", layout="wide")

# Paleta segura para daltonismo (Okabe-Ito). Cada cor sempre vem com um rótulo em texto.
CORES_STATUS = {"Aberto": "#E69F00", "Revisão humana": "#0072B2", "Resolvido": "#009E73"}


@st.cache_data(ttl=30)
def carregar() -> "dados.pd.DataFrame":
    return dados.listar_chamados()


@st.cache_resource
def carregar_assistente() -> Assistente:
    return Assistente()


st.title("ZelaCidade")
st.caption("Reporte problemas da sua rua e acompanhe os chamados. Protótipo acadêmico – FIAP GS 2026.2.")

aba_reportar, aba_painel, aba_assistente, aba_alertas = st.tabs(
    ["📷 Reportar problema", "📊 Painel de chamados", "💬 Assistente", "🔔 Alertas sonoros"]
)

# --- Reportar ---------------------------------------------------------------
with aba_reportar:
    st.subheader("Reportar um problema")
    foto = st.file_uploader("Foto do problema", type=["jpg", "jpeg", "png"])
    if foto:
        st.image(foto, width=360, caption="Foto enviada")

    st.info(
        "A classificação automática pela visão computacional ainda não está ligada. "
        "Por enquanto, escolha o tipo do problema abaixo."
    )
    tipo = st.selectbox("Tipo do problema", list(dados.TIPOS), format_func=dados.TIPOS.get)
    endereco = st.text_input("Endereço (rua e número)")
    bairro = st.text_input("Bairro")
    confirmo = st.checkbox("Confirmo que as informações estão corretas")

    if st.button("Enviar chamado", type="primary", disabled=not confirmo):
        try:
            novo_id = dados.registrar_chamado(tipo, endereco, bairro)
        except ValueError as erro:
            st.error(str(erro))
        else:
            carregar.clear()
            st.success(f"Chamado {novo_id} registrado. Você pode acompanhar no Painel.")

# --- Painel -----------------------------------------------------------------
with aba_painel:
    df = carregar()
    if df.empty:
        st.warning("Nenhum chamado ainda. Rode `python rpa/rpa_chamados.py` ou reporte um problema.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Chamados", len(df))
        c2.metric("Abertos", int((df["status"] == "aberto").sum()))
        c3.metric("Em revisão humana", int((df["status"] == "revisao_humana").sum()))

        filtro = st.multiselect(
            "Filtrar por status", list(CORES_STATUS), default=list(CORES_STATUS)
        )
        vis = df[df["status_nome"].isin(filtro)]

        g1, g2 = st.columns(2)
        por_tipo = vis.groupby(["tipo_nome", "status_nome"]).size().reset_index(name="chamados")
        g1.plotly_chart(
            px.bar(por_tipo, x="tipo_nome", y="chamados", color="status_nome",
                   color_discrete_map=CORES_STATUS, text="chamados",
                   labels={"tipo_nome": "Tipo", "chamados": "Chamados", "status_nome": "Status"},
                   title="Chamados por tipo"),
            width="stretch",
        )
        por_bairro = vis.groupby("bairro").size().reset_index(name="chamados").sort_values("chamados")
        g2.plotly_chart(
            px.bar(por_bairro, x="chamados", y="bairro", orientation="h", text="chamados",
                   labels={"bairro": "Bairro", "chamados": "Chamados"},
                   title="Chamados por bairro"),
            width="stretch",
        )

        st.dataframe(
            vis[["id_foto", "data_hora", "tipo_nome", "confianca", "endereco", "bairro", "status_nome"]],
            hide_index=True,
            column_config={
                "id_foto": "ID", "data_hora": "Data", "tipo_nome": "Tipo",
                "confianca": st.column_config.NumberColumn("Confiança", format="%.2f"),
                "endereco": "Endereço", "bairro": "Bairro", "status_nome": "Status",
            },
            width="stretch",
        )

        st.markdown("**Revisão humana**: chamados com confiança baixa precisam de alguém conferir a foto.")
        pendentes = df[df["status"] == "revisao_humana"]
        if pendentes.empty:
            st.caption("Nada pendente.")
        for r in pendentes.itertuples():
            col_a, col_b, col_c = st.columns([3, 1, 1])
            col_a.write(f"{r.id_foto} · {r.tipo_nome} · {r.endereco} (confiança {r.confianca:.2f})")
            if col_b.button("Aprovar", key=f"ok_{r.id_foto}"):
                dados.atualizar_status(r.id_foto, "aberto")
                carregar.clear()
                st.rerun()
            if col_c.button("Descartar", key=f"no_{r.id_foto}"):
                dados.atualizar_status(r.id_foto, "resolvido")
                carregar.clear()
                st.rerun()

# --- Assistente -------------------------------------------------------------
with aba_assistente:
    st.subheader("Assistente de serviços públicos")
    st.caption(
        "Responde com base na Cartilha de Calçadas 2026, em páginas da Prefeitura de SP e no FAQ do "
        "ZelaCidade. Quando não encontra a resposta nos documentos, ele avisa em vez de inventar. "
        "Não substitui o atendimento oficial do SP156."
    )
    assistente = carregar_assistente()
    if "conversa" not in st.session_state:
        st.session_state.conversa = []
    for papel, texto, meta in st.session_state.conversa:
        with st.chat_message(papel):
            st.markdown(texto)
            if meta:
                st.caption(meta)
    pergunta = st.chat_input("Ex.: Qual a largura mínima da calçada?")
    if pergunta:
        r = assistente.perguntar(pergunta)
        meta = f"Modo: {r['modo']} · relevância do trecho: {r['score']}"
        st.session_state.conversa += [("user", pergunta, ""), ("assistant", r["resposta"], meta)]
        st.rerun()

# --- Alertas ----------------------------------------------------------------
with aba_alertas:
    st.subheader("Alertas sonoros para pessoas surdas")
    st.info("Em construção: aqui vão aparecer os sons reconhecidos pelo dispositivo IoT (Edge Impulse).")
