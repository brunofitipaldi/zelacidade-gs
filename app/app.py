"""Interface do ZelaCidade (Streamlit).

Rodar a partir da raiz do projeto:
    streamlit run app/app.py
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from PIL import Image

import dados

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "genai"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "visao"))
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


@st.cache_resource
def carregar_classificador():
    from classificador import Classificador
    return Classificador()


@st.cache_data(max_entries=20)
def classificar_foto(conteudo: bytes) -> dict:
    return carregar_classificador().classificar(Image.open(io.BytesIO(conteudo)))


@st.cache_data
def carregar_testes_iot() -> pd.DataFrame:
    caminho = Path(__file__).resolve().parent.parent / "iot" / "testes_ao_vivo.csv"
    return pd.read_csv(caminho) if caminho.exists() else pd.DataFrame()


st.title("ZelaCidade")
st.caption("Reporte problemas da sua rua e acompanhe os chamados. Protótipo acadêmico – FIAP GS 2026.2.")

aba_reportar, aba_painel, aba_assistente, aba_alertas = st.tabs(
    ["📷 Reportar problema", "📊 Painel de chamados", "💬 Assistente", "🔔 Alertas sonoros"]
)

# --- Reportar ---------------------------------------------------------------
with aba_reportar:
    st.subheader("Reportar um problema")
    foto = st.file_uploader("Foto do problema", type=["jpg", "jpeg", "png"])
    sugestao = None
    if foto:
        col_foto, col_ia = st.columns([1, 1])
        col_foto.image(foto, width=360, caption="Foto enviada")
        with col_ia:
            with st.spinner("Analisando a foto..."):
                sugestao = classificar_foto(foto.getvalue())
            nome = dados.TIPOS[sugestao["tipo"]]
            if sugestao["revisao_humana"]:
                st.warning(
                    f"A IA acha que é **{nome}**, mas com pouca confiança ({sugestao['confianca']:.0%}). "
                    "Confira o tipo abaixo: o chamado vai passar por revisão humana."
                )
            else:
                st.success(f"A IA identificou: **{nome}** (confiança {sugestao['confianca']:.0%}).")
            probs = (
                pd.DataFrame({"Tipo": [dados.TIPOS[t] for t in sugestao["probabilidades"]],
                              "Probabilidade": list(sugestao["probabilidades"].values())})
                .sort_values("Probabilidade")
            )
            st.plotly_chart(
                px.bar(probs, x="Probabilidade", y="Tipo", orientation="h", text_auto=".0%",
                       range_x=[0, 1], height=200).update_layout(margin=dict(l=0, r=0, t=10, b=0)),
                width="stretch",
            )
            st.caption("A IA reconhece buraco, rachadura e desgaste do asfalto. "
                       "Para calçada quebrada, escolha o tipo manualmente.")

    opcoes = list(dados.TIPOS)
    tipo = st.selectbox(
        "Tipo do problema", opcoes, format_func=dados.TIPOS.get,
        index=opcoes.index(sugestao["tipo"]) if sugestao else 0,
        key=f"tipo_{foto.file_id if foto else 'manual'}",
    )
    endereco = st.text_input("Endereço (rua e número)")
    bairro = st.text_input("Bairro")
    confirmo = st.checkbox("Confirmo que as informações estão corretas")

    if st.button("Enviar chamado", type="primary", disabled=not confirmo):
        # Se o cidadão trocou o tipo sugerido, a decisão é dele: não guarda a confiança da IA.
        confianca = sugestao["confianca"] if sugestao and tipo == sugestao["tipo"] else None
        try:
            novo_id = dados.registrar_chamado(tipo, endereco, bairro, confianca)
        except ValueError as erro:
            st.error(str(erro))
        else:
            carregar.clear()
            status = "em revisão humana" if confianca is not None and confianca < dados.LIMIAR_REVISAO else "aberto"
            st.success(f"Chamado {novo_id} registrado ({status}). Você pode acompanhar no Painel.")

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
    st.caption(
        "Um modelo treinado no Edge Impulse ouve o microfone e reconhece sirene, buzina e ruído do "
        "ambiente. Quando ouve sirene ou buzina, o celular avisa a pessoa surda por vibração e alerta na tela."
    )
    testes = carregar_testes_iot()
    if testes.empty:
        st.warning("Resultados dos testes não encontrados em iot/testes_ao_vivo.csv.")
    else:
        acertos = int((testes["acertou"] == "sim").sum())
        m1, m2, m3 = st.columns(3)
        perdidos = int(((testes["som_tocado"] != "ruido") & (testes["modelo_respondeu"] == "ruido")).sum())
        m1.metric("Acerto nos testes ao vivo", f"{acertos / len(testes):.1%}".replace(".", ","),
                  help=f"{acertos} de {len(testes)} testes")
        m2.metric("Acerto no conjunto de teste", "76,84%", help="Model testing do Edge Impulse")
        com_alerta = int((testes["som_tocado"] != "ruido").sum())
        m3.metric("Alertas perdidos", f"{perdidos} de {com_alerta}",
                  help="Testes de sirene ou buzina em que o modelo respondeu ruído")

        nomes = {"buzina": "Buzina", "ruido": "Ruído", "sirene": "Sirene"}
        matriz = (
            pd.crosstab(testes["som_tocado"].map(nomes), testes["modelo_respondeu"].map(nomes))
            .reindex(index=list(nomes.values()), columns=list(nomes.values()), fill_value=0)
        )
        g1, g2 = st.columns([1, 1])
        g1.plotly_chart(
            px.imshow(matriz, text_auto=True, color_continuous_scale="Blues",
                      labels={"x": "Modelo respondeu", "y": "Som tocado", "color": "Testes"},
                      title="Matriz de confusão – 15 testes ao vivo"),
            width="stretch",
        )
        tabela = testes.assign(
            som_tocado=testes["som_tocado"].map(nomes),
            modelo_respondeu=testes["modelo_respondeu"].map(nomes),
            acertou=testes["acertou"].map({"sim": "✅ Sim", "nao": "❌ Não"}),
        )
        g2.dataframe(
            tabela, hide_index=True, width="stretch",
            column_config={"teste": "Nº", "som_tocado": "Som tocado",
                           "modelo_respondeu": "Modelo respondeu", "acertou": "Acertou?"},
        )
        st.warning(
            "**Limitação:** o erro mais comum foi sirene ou buzina reconhecida como ruído, ou seja, um "
            "alerta que não chega. Para uma pessoa surda esse erro é mais grave que um alarme falso, por "
            "isso o app não deve ser a única forma de aviso."
        )
