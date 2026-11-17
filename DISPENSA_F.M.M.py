import streamlit as st
import json
import os
from datetime import datetime, date, timedelta
import urllib.parse

# ==========================================
# CONFIGURAÇÕES GERAIS E SENHA PRIVADA
# ==========================================
st.set_page_config(
    page_title="Dispensa F.M.M — Casa Açaizal",
    page_icon="🛒",
    layout="wide"
)

SENHA_LISTA_PRIVADA = "2040"  # <--Senha pessoal 

# ==========================================
# SELETOR DE LISTA (BARRA LATERAL)
# ==========================================
with st.sidebar:
    st.header("📂 Selecionar Dispensa")
    modo_lista = st.radio(
        "Escolha qual lista deseja acessar:",
        ["🏠 Compartilhada (Casa Açaizal)", "🔒 Privada (Só Minha)"]
    )

    if "Privada" in modo_lista:
        st.divider()
        senha_digitada = st.text_input("Digite sua senha pessoal:", type="password")
        if senha_digitada != SENHA_LISTA_PRIVADA:
            st.warning("🔒 Acesso restrito. Digite a senha correta para ver sua lista privada.")
            st.stop()
        else:
            st.success("🔓 Lista privada desbloqueada!")
            ARQUIVO_DADOS = "dispensa_privada.json"
            TITULO_ATUAL = "Dispensa F.M.M — Lista Privada"
            SUBTITULO_ATUAL = "Controle pessoal exclusivo (Acesso protegido)"
    else:
        ARQUIVO_DADOS = "dispensa_compartilhada.json"
        TITULO_ATUAL = "Dispensa F.M.M — Casa Açaizal"
        SUBTITULO_ATUAL = "Controle inteligente e compartilhado de compras e estoque"

# ==========================================
# FUNÇÕES DE ARMAZENAMENTO E CÁLCULO
# ==========================================
def load_products():
    if os.path.exists(ARQUIVO_DADOS):
        with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_products(products):
    with open(ARQUIVO_DADOS, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

def format_num(n):
    return str(int(n)) if n == int(n) else f"{n:.2f}".rstrip('0').rstrip('.')

def format_date_br(date_str):
    if not date_str:
        return "-"
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return date_str

def calcular_consumo(item):
    history = item.get("history", [])
    withdrawals = [h for h in history if h.get("type") == "withdrawal"]
    total_withdrawn = sum(h.get("amount", 0) for h in withdrawals)

    if total_withdrawn == 0:
        return 0.0, None

    all_dates = [datetime.strptime(h["date"], "%Y-%m-%d").date() for h in history if h.get("date")]
    if not all_dates:
        return 0.0, None

    earliest = min(all_dates)
    today = date.today()
    days_elapsed = max(1, (today - earliest).days)
    effective_days = max(30, days_elapsed)

    monthly_avg = (total_withdrawn / effective_days) * 30
    daily_rate = monthly_avg / 30

    days_left = int(item["quantity"] / daily_rate) if daily_rate > 0 and item["quantity"] > 0 else 0
    return monthly_avg, days_left

# ==========================================
# INTERFACE PRINCIPAL
# ==========================================
products = load_products()

st.title(f"🛒 {TITULO_ATUAL}")
st.caption(SUBTITULO_ATUAL)

# Alertas de estoque baixo
low_stock = [p for p in products if p["quantity"] <= p["minStock"]]

if low_stock:
    st.warning(f"⚠️ **Atenção! {len(low_stock)} item(ns) precisando de reposição nesta lista:**")
    nomes_alerta = [f"• **{p['name']}** (Resta: {format_num(p['quantity'])} {p['unit']} | Mín: {format_num(p['minStock'])})" for p in low_stock]
    st.markdown("\n".join(nomes_alerta))

    texto_wpp = f"🛒 *Lista de Compras - {TITULO_ATUAL}*\n\n" + "\n".join(
        [f"- {p['name']} (Atual: {format_num(p['quantity'])} {p['unit']})" for p in low_stock]
    )
    link_wpp = f"https://wa.me/?text={urllib.parse.quote(texto_wpp)}"
    st.link_button("📲 Enviar Lista de Compras no WhatsApp", link_wpp)

st.divider()

# ==========================================
# CADASTRO / REABASTECIMENTO
# ==========================================
with st.expander("➕ Registrar Compra / Novo Produto", expanded=(len(products) == 0)):
    with st.form("form_compra", clear_on_submit=True):
        col1, col2, col3 = st.columns([3, 1, 1])
        nome = col1.text_input("Nome do Produto (ex: Arroz, Café, Sabão)")
        qtd = col2.number_input("Quantidade Comprada", min_value=0.1, value=1.0, step=0.5)
        unidade = col3.selectbox("Unidade", ["un", "pct", "kg", "g", "L", "ml", "cx", "frasco"])

        col4, col5 = st.columns(2)
        min_estoque = col4.number_input("Avisar quando chegar em (Estoque Mínimo)", min_value=0.0, value=1.0, step=0.5)
        data_compra = col5.date_input("Data da Compra", value=date.today())

        submitted = st.form_submit_button("💾 Salvar Compra", use_container_width=True)
        if submitted and nome.strip():
            nome_limpo = nome.strip()
            data_str = data_compra.strftime("%Y-%m-%d")
            existente = next((p for p in products if p["name"].lower() == nome_limpo.lower()), None)

            if existente:
                existente["quantity"] += qtd
                existente["minStock"] = min_estoque
                existente["unit"] = unidade
                existente["lastPurchaseDate"] = data_str
                existente["history"].append({"type": "purchase", "amount": qtd, "date": data_str})
                st.success(f"Estoque de **{nome_limpo}** atualizado!")
            else:
                novo_id = str(int(datetime.now().timestamp() * 1000))
                products.append({
                    "id": novo_id,
                    "name": nome_limpo,
                    "quantity": qtd,
                    "unit": unidade,
                    "minStock": min_estoque,
                    "lastPurchaseDate": data_str,
                    "history": [{"type": "purchase", "amount": qtd, "date": data_str}]
                })
                st.success(f"**{nome_limpo}** adicionado à lista!")

            save_products(products)
            st.rerun()

# ==========================================
# LISTAGEM E BAIXA DE PRODUTOS
# ==========================================
st.subheader(f"📦 Produtos Cadastrados ({len(products)})")

if not products:
    st.info("Nenhum produto cadastrado nesta lista ainda. Use o formulário acima para começar.")
else:
    busca = st.text_input("🔍 Filtrar produto pelo nome:", placeholder="Digite para buscar...")
    filtrados = [p for p in products if busca.lower() in p["name"].lower()]

    cols = st.columns(3)
    for idx, item in enumerate(filtrados):
        with cols[idx % 3]:
            with st.container(border=True):
                is_zero = item["quantity"] <= 0
                is_low = item["quantity"] <= item["minStock"]

                status_badge = "🔴 ACABOU" if is_zero else ("🟡 ACABANDO" if is_low else "🟢 OK")
                st.markdown(f"### {item['name']}")
                st.caption(f"Status: {status_badge} | Última compra: {format_date_br(item.get('lastPurchaseDate'))}")

                st.metric(
                    label="Estoque Atual",
                    value=f"{format_num(item['quantity'])} {item['unit']}",
                    delta=f"Mínimo: {format_num(item['minStock'])} {item['unit']}",
                    delta_color="off"
                )

                monthly_avg, days_left = calcular_consumo(item)
                if monthly_avg > 0:
                    st.info(f"📊 Gasto médio: **{format_num(monthly_avg)} {item['unit']}/mês**\n\n⏳ Duração est.: **~{days_left} dias**")
                else:
                    st.caption("📊 Dê baixa nos itens para calcular o gasto mensal.")

                # Botão de Baixa Rápida (-1)
                c_btn1, c_btn2 = st.columns(2)
                if c_btn1.button("➖ Retirar 1", key=f"ret1_{item['id']}", disabled=is_zero, use_container_width=True):
                    retirada = min(1.0, item["quantity"])
                    item["quantity"] = round(item["quantity"] - retirada, 3)
                    item["history"].append({
                        "type": "withdrawal",
                        "amount": retirada,
                        "date": date.today().strftime("%Y-%m-%d")
                    })
                    save_products(products)
                    st.rerun()

                with c_btn2.popover("⚙️ Opções", use_container_width=True):
                    qtd_custom = st.number_input("Qtd retirada:", min_value=0.1, max_value=float(max(0.1, item["quantity"])), value=min(1.0, float(max(0.1, item["quantity"]))), step=0.1, key=f"num_{item['id']}")
                    if st.button("Confirmar Retirada", key=f"conf_{item['id']}", disabled=is_zero):
                        item["quantity"] = round(item["quantity"] - qtd_custom, 3)
                        item["history"].append({
                            "type": "withdrawal",
                            "amount": qtd_custom,
                            "date": date.today().strftime("%Y-%m-%d")
                        })
                        save_products(products)
                        st.rerun()

                    st.divider()
                    st.caption("Últimas movimentações:")
                    for mov in reversed(item.get("history", [])[-5:]):
                        sinal = "🟢 +" if mov["type"] == "purchase" else "🔴 -"
                        st.text(f"{sinal}{format_num(mov['amount'])} {item['unit']} em {format_date_br(mov['date'])}")

                    if st.button("🗑️ Excluir produto", key=f"del_{item['id']}", use_container_width=True):
                        products = [p for p in products if p["id"] != item["id"]]
                        save_products(products)
                        st.rerun()
