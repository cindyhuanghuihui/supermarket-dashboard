import hashlib
import hmac
import os

import streamlit as st
import pandas as pd
import plotly.express as px

# ── 頁面基本設定 ──────────────────────────────────────────────
st.set_page_config(
    page_title="超市銷售儀表板",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 認證函式 ──────────────────────────────────────────────────
def _verify(password: str, stored_hash: str) -> bool:
    h = hashlib.sha256(password.encode()).hexdigest()
    return hmac.compare_digest(h, stored_hash)

def require_login():
    if st.session_state.get("authenticated"):
        return
    st.title("🛒 超市銷售儀表板")
    st.markdown("#### 請登入以查看公司數據")
    with st.form("login_form"):
        username = st.text_input("帳號")
        password = st.text_input("密碼", type="password")
        submitted = st.form_submit_button("登入", use_container_width=True)
    if submitted:
        users = st.secrets.get("users", {})
        if username in users and _verify(password, users[username]["password_hash"]):
            st.session_state["authenticated"] = True
            st.session_state["username"] = username
            st.session_state["display_name"] = users[username].get("name", username)
            st.rerun()
        else:
            st.error("帳號或密碼錯誤，請重新輸入。")
    st.stop()

require_login()

# ── 側邊欄：使用者資訊 + 登出 ────────────────────────────────
with st.sidebar:
    st.markdown(f"### 👋 歡迎，{st.session_state['display_name']}！")
    if st.button("登出", use_container_width=True):
        st.session_state.clear()
        st.rerun()
    st.divider()

# ── 資料載入（快取） ──────────────────────────────────────────
@st.cache_data
def load_data() -> pd.DataFrame:
    path = os.path.join(os.path.dirname(__file__), "data", "supermarket_sales.csv")
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Hour"] = pd.to_datetime(df["Time"], format="%H:%M").dt.hour
    return df

df_all = load_data()

# ── 側邊欄篩選器 ──────────────────────────────────────────────
with st.sidebar:
    st.subheader("篩選條件")

    date_min, date_max = df_all["Date"].min().date(), df_all["Date"].max().date()
    date_range = st.date_input("日期範圍", value=(date_min, date_max),
                               min_value=date_min, max_value=date_max)
    if len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = date_min, date_max

    branches = st.multiselect("分店", options=sorted(df_all["Branch"].unique()),
                              default=sorted(df_all["Branch"].unique()))

    product_lines = st.multiselect("產品類別",
                                   options=sorted(df_all["Product line"].unique()),
                                   default=sorted(df_all["Product line"].unique()))

# ── 套用篩選 ──────────────────────────────────────────────────
df = df_all[
    (df_all["Date"].dt.date >= start_date) &
    (df_all["Date"].dt.date <= end_date) &
    (df_all["Branch"].isin(branches)) &
    (df_all["Product line"].isin(product_lines))
].copy()

# ── 標題 ──────────────────────────────────────────────────────
st.title("🛒 超市銷售儀表板")
st.caption(f"資料範圍：{start_date} ～ {end_date}　｜　共 {len(df):,} 筆交易")
st.divider()

# ── KPI 卡片 ──────────────────────────────────────────────────
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("💰 總營收", f"${df['Total'].sum():,.0f}")
kpi2.metric("🧾 交易筆數", f"{len(df):,}")
kpi3.metric("🛍️ 平均客單價", f"${df['Total'].mean():,.1f}")
kpi4.metric("📈 總毛利", f"${df['gross income'].sum():,.0f}")

st.divider()

# ── 第一列：銷售趨勢 + 分店比較 ──────────────────────────────
col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("每日銷售趨勢")
    daily = df.groupby("Date")["Total"].sum().reset_index()
    fig_trend = px.line(daily, x="Date", y="Total",
                        labels={"Total": "營收 ($)", "Date": "日期"},
                        template="plotly_white")
    fig_trend.update_traces(line_color="#1f77b4", line_width=2)
    st.plotly_chart(fig_trend, use_container_width=True)

with col_right:
    st.subheader("各分店營收")
    branch_rev = df.groupby("Branch")["Total"].sum().reset_index()
    fig_branch = px.bar(branch_rev, x="Branch", y="Total", color="Branch",
                        labels={"Total": "營收 ($)", "Branch": "分店"},
                        template="plotly_white",
                        color_discrete_sequence=px.colors.qualitative.Set2)
    fig_branch.update_layout(showlegend=False)
    st.plotly_chart(fig_branch, use_container_width=True)

# ── 第二列：產品類別 ──────────────────────────────────────────
st.subheader("產品類別分析")
col_pie, col_bar = st.columns(2)

with col_pie:
    prod_rev = df.groupby("Product line")["Total"].sum().reset_index()
    fig_pie = px.pie(prod_rev, names="Product line", values="Total",
                     title="各品類營收佔比",
                     template="plotly_white",
                     color_discrete_sequence=px.colors.qualitative.Pastel)
    st.plotly_chart(fig_pie, use_container_width=True)

with col_bar:
    prod_qty = df.groupby("Product line")["Quantity"].sum().reset_index().sort_values("Quantity")
    fig_qty = px.bar(prod_qty, y="Product line", x="Quantity", orientation="h",
                     title="各品類銷售數量",
                     labels={"Quantity": "數量", "Product line": ""},
                     template="plotly_white",
                     color_discrete_sequence=["#2ca02c"])
    st.plotly_chart(fig_qty, use_container_width=True)

# ── 第三列：顧客洞察 ──────────────────────────────────────────
st.subheader("顧客洞察")
col_a, col_b, col_c = st.columns(3)

with col_a:
    cust_type = df["Customer type"].value_counts().reset_index()
    cust_type.columns = ["type", "count"]
    fig_cust = px.pie(cust_type, names="type", values="count",
                      title="會員 vs 一般顧客",
                      template="plotly_white",
                      color_discrete_sequence=["#ff7f0e", "#1f77b4"])
    st.plotly_chart(fig_cust, use_container_width=True)

with col_b:
    gender = df["Gender"].value_counts().reset_index()
    gender.columns = ["gender", "count"]
    fig_gender = px.pie(gender, names="gender", values="count",
                        title="性別分佈",
                        template="plotly_white",
                        color_discrete_sequence=["#9467bd", "#e377c2"])
    st.plotly_chart(fig_gender, use_container_width=True)

with col_c:
    payment = df["Payment"].value_counts().reset_index()
    payment.columns = ["method", "count"]
    fig_pay = px.pie(payment, names="method", values="count",
                     title="付款方式分佈",
                     template="plotly_white",
                     color_discrete_sequence=px.colors.qualitative.Set1)
    st.plotly_chart(fig_pay, use_container_width=True)

# ── 第四列：評分分析 + 分店詳細比較 ──────────────────────────
st.subheader("詳細比較")
col_rating, col_detail = st.columns(2)

with col_rating:
    fig_rating = px.histogram(df, x="Rating", nbins=20,
                              title="顧客評分分佈",
                              labels={"Rating": "評分", "count": "次數"},
                              template="plotly_white",
                              color_discrete_sequence=["#d62728"])
    fig_rating.update_layout(bargap=0.1)
    st.plotly_chart(fig_rating, use_container_width=True)

with col_detail:
    branch_detail = df.groupby("Branch").agg(
        營收=("Total", "sum"),
        交易數=("Invoice ID", "count"),
        平均評分=("Rating", "mean"),
        平均客單價=("Total", "mean"),
    ).round(2).reset_index()
    st.write("**各分店綜合比較**")
    st.dataframe(branch_detail, use_container_width=True, hide_index=True)

# ── 底部：原始資料預覽 ────────────────────────────────────────
with st.expander("查看原始資料"):
    st.dataframe(df, use_container_width=True, height=300)
    st.caption(f"顯示 {len(df):,} 筆（篩選後）")
