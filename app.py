"""
価格弾力性分析ツール
UbunBASEの価格弾力性データからASIN別の折れ線グラフを生成

使い方:
1. streamlit run price_elasticity_analyzer.py
2. UbunBASEからエクスポートしたCSVをアップロード or コピペ
3. グラフ生成 → HTMLダウンロード

機能:
- ASIN別 値引き率 vs 新規弾力性 折れ線グラフ
- 3パターン分類（閾値突破型/軽値引き反応型/低空飛行型）
- エントリー推奨の自動判定
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import io

st.set_page_config(
    page_title="価格弾力性分析ツール",
    page_icon="📊",
    layout="wide"
)

# セッション状態の初期化
if 'fig' not in st.session_state:
    st.session_state.fig = None
if 'df_result' not in st.session_state:
    st.session_state.df_result = None
if 'graph_generated' not in st.session_state:
    st.session_state.graph_generated = False

st.title("📊 価格弾力性分析ツール")
st.markdown("UbunBASEの価格弾力性データから「どのASINを何%オフで入れるか」を判断")

# サンプルデータ（ダミー）
sample_data = """ASIN,値引き率,定価,需要の変化,価格弾力性
B0SAMPLE01,-0.09,1500,-0.884,-9.825
B0SAMPLE01,-0.06,1500,-0.837,-13.954
B0SAMPLE01,-0.05,1500,-0.9,-17.992
B0SAMPLE01,-0.2,1500,3.552,17.758
B0SAMPLE02,-0.2,3000,8.105,40.525
B0SAMPLE03,-0.06,1800,1.008,16.804
B0SAMPLE03,-0.07,1800,0.774,11.051
B0SAMPLE04,-0.12,1539,-0.694,-5.784
B0SAMPLE04,-0.05,1545,-0.773,-15.459"""

# サイドバー設定
with st.sidebar:
    st.header("⚙️ 設定")

    # 閾値設定
    st.subheader("判定閾値")
    threshold_high = st.number_input("推奨ゾーン閾値（弾力性）", value=10.0, step=1.0)
    threshold_low = st.number_input("逆効果ゾーン閾値（弾力性）", value=0.0, step=1.0)

    # 値引き率帯の定義
    st.subheader("値引き率帯の定義")
    light_discount_max = st.number_input("軽値引きの上限（%）", value=10, step=1)
    deep_discount_min = st.number_input("深値引きの下限（%）", value=20, step=1)

# メインエリア
st.subheader("1️⃣ データ入力")

input_method = st.radio(
    "入力方法",
    ["CSVファイルをアップロード", "テキストで貼り付け"],
    horizontal=True
)

df = None

if input_method == "CSVファイルをアップロード":
    uploaded_file = st.file_uploader(
        "UbunBASEからエクスポートしたCSVをアップロード",
        type=['csv']
    )
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
else:
    data_input = st.text_area(
        "CSVデータ（ヘッダー行含む）",
        value=sample_data,
        height=200,
        help="UbunBASEからコピーしたデータをそのまま貼り付けてください"
    )
    if data_input:
        try:
            df = pd.read_csv(io.StringIO(data_input))
        except:
            st.error("データの形式が正しくありません")


def classify_asin(asin_data, threshold_high, light_max, deep_min):
    """ASINを3パターンに分類"""
    # 20%オフ時の弾力性
    deep_data = asin_data[asin_data['値引き率_pct'] >= deep_min]
    deep_elasticity = deep_data['価格弾力性'].max() if len(deep_data) > 0 else None

    # 5-12%オフ時の弾力性
    light_data = asin_data[(asin_data['値引き率_pct'] >= 5) & (asin_data['値引き率_pct'] <= light_max)]
    light_elasticity_max = light_data['価格弾力性'].max() if len(light_data) > 0 else None
    light_elasticity_avg = light_data['価格弾力性'].mean() if len(light_data) > 0 else None

    # 分類ロジック
    if deep_elasticity is not None and deep_elasticity > threshold_high:
        # 20%オフで弾力性が高い
        if light_elasticity_avg is not None and light_elasticity_avg < 0:
            return "A", "閾値突破型", "20%オフ推奨", "#2ca02c"
        else:
            return "A", "閾値突破型", "20%オフ推奨", "#2ca02c"

    if light_elasticity_max is not None and light_elasticity_max > threshold_high / 2:
        # 軽値引きで既に反応している
        return "B", "軽値引き反応型", "5-10%オフ推奨", "#1f77b4"

    if light_elasticity_avg is not None and light_elasticity_avg < 0:
        # 軽値引きで逆効果
        if deep_elasticity is None or deep_elasticity < threshold_high:
            return "C", "低空飛行型", "セール見送り", "#d62728"

    return "D", "検証必要", "データ不足", "#7f7f7f"


def generate_graph(df, asin_names_dict, threshold_high, threshold_low):
    """Plotlyグラフを生成"""
    fig = go.Figure()

    # ASINリストを取得
    asins = df['ASIN'].unique()

    # カラーパレット
    colors = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
    ]

    # ゾーン塗りつぶし
    fig.add_hrect(y0=threshold_high, y1=50, fillcolor="green", opacity=0.1,
                  layer="below", line_width=0)
    fig.add_hrect(y0=-30, y1=threshold_low, fillcolor="red", opacity=0.1,
                  layer="below", line_width=0)

    # 基準線
    fig.add_hline(y=threshold_low, line_dash="solid", line_color="gray", line_width=1.5)
    fig.add_hline(y=threshold_high, line_dash="dash", line_color="green", line_width=2,
                  annotation_text=f"推奨ゾーン (弾力性>{threshold_high})",
                  annotation_position="top right")

    # ASINごとに折れ線
    results = []
    for i, asin in enumerate(asins):
        asin_data = df[df['ASIN'] == asin].sort_values('値引き率_pct')
        if len(asin_data) == 0:
            continue

        color = colors[i % len(colors)]

        # ASIN名を取得（マッピングがあれば使う、なければASIN）
        display_name = asin_names_dict.get(asin, asin)

        # 分類
        pattern, pattern_name, recommendation, _ = classify_asin(
            asin_data, threshold_high, 12, 15
        )

        results.append({
            'ASIN': asin,
            '商品名': display_name if display_name != asin else "",
            'パターン': f"{pattern}. {pattern_name}",
            '推奨': recommendation,
            '定価': asin_data['定価'].iloc[0]
        })

        # 折れ線を追加
        fig.add_trace(go.Scatter(
            x=asin_data['値引き率_pct'],
            y=asin_data['価格弾力性'],
            mode='lines+markers',
            name=f"{display_name} ({pattern})",
            line=dict(color=color, width=2.5),
            marker=dict(size=8),
            hovertemplate=(
                f"<b>{display_name}</b><br>"
                "値引き率: %{x:.0f}%<br>"
                "弾力性: %{y:.1f}<br>"
                "<extra></extra>"
            )
        ))

    # レイアウト設定
    fig.update_layout(
        title=dict(
            text="ASIN別 値引き率 vs 価格弾力性",
            font=dict(size=20)
        ),
        xaxis_title="値引き率 (%)",
        yaxis_title="価格弾力性",
        hovermode='closest',
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=1.02,
            font=dict(size=11)
        ),
        margin=dict(r=250),
        template='plotly_white',
        height=600
    )

    # 軸設定
    fig.update_xaxes(
        tickvals=[5, 10, 15, 20, 25],
        gridcolor='lightgray',
        gridwidth=0.5,
        range=[3, 25]
    )
    fig.update_yaxes(
        gridcolor='lightgray',
        gridwidth=0.5,
        range=[-25, 50]
    )

    return fig, pd.DataFrame(results)


# ASIN名マッピング（オプション）
st.subheader("2️⃣ ASIN名マッピング（オプション）")
asin_name_input = st.text_area(
    "スプレッドシートからASINと商品名をコピペ（タブ区切り）",
    value="",
    height=100,
    placeholder="B0XXXXXXXX\t商品名A\nB0YYYYYYYY\t商品名B",
    help="スプレッドシートからそのままコピペできます。空欄の場合はASINがそのまま表示されます"
)

# グラフ生成ボタン
if df is not None:
    if st.button("📊 グラフ生成", type="primary"):
        try:
            # 値引き率を正の数に変換
            df['値引き率_pct'] = df['値引き率'].abs() * 100

            # ASIN名マッピングをパース（TSV形式対応）
            asin_names_dict = {}
            if asin_name_input and asin_name_input.strip():
                for line in asin_name_input.strip().split('\n'):
                    # タブ区切りまたはカンマ区切りに対応
                    if '\t' in line:
                        parts = line.split('\t', 1)
                    elif ',' in line:
                        parts = line.split(',', 1)
                    else:
                        continue
                    if len(parts) == 2:
                        asin_names_dict[parts[0].strip()] = parts[1].strip()

            # グラフ生成
            st.session_state.fig, st.session_state.df_result = generate_graph(
                df, asin_names_dict, threshold_high, threshold_low
            )
            st.session_state.graph_generated = True

        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
            import traceback
            st.code(traceback.format_exc())

# グラフ表示
if st.session_state.graph_generated and st.session_state.fig is not None:
    st.success(f"✅ {len(st.session_state.df_result)}件のASINを分析しました")

    st.subheader("3️⃣ グラフプレビュー")

    # タブで表示
    tab1, tab2 = st.tabs(["📈 グラフ", "📋 判定結果"])

    with tab1:
        st.plotly_chart(st.session_state.fig, width="stretch")

    with tab2:
        st.subheader("ASIN別 エントリー推奨")

        # パターン別に色分け表示
        df_result = st.session_state.df_result

        # パターン説明
        st.markdown("""
        | パターン | 特徴 | 推奨アクション |
        |---------|------|--------------|
        | **A. 閾値突破型** | 5-12%で逆効果、20%で爆発 | 20%オフでエントリー |
        | **B. 軽値引き反応型** | 5-10%で既に反応 | 5-10%オフで十分 |
        | **C. 低空飛行型** | どの値引き率でも低い | セール見送り |
        | **D. 検証必要** | データ不足 | 小規模テスト |
        """)

        st.dataframe(
            df_result,
            width="stretch",
            hide_index=True
        )

    # HTMLダウンロード
    st.subheader("4️⃣ ダウンロード")

    col1, col2 = st.columns(2)

    with col1:
        html_content = st.session_state.fig.to_html(include_plotlyjs=True, full_html=True)
        st.download_button(
            label="📥 グラフ (HTML)",
            data=html_content,
            file_name="price_elasticity_analysis.html",
            mime="text/html"
        )

    with col2:
        csv_content = st.session_state.df_result.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 判定結果 (CSV)",
            data=csv_content,
            file_name="elasticity_recommendation.csv",
            mime="text/csv"
        )

    st.info("💡 HTMLファイルはブラウザで開くとインタラクティブに操作できます（ホバーで詳細表示、凡例クリックでON/OFF）")

# 使い方
with st.expander("📖 使い方・考え方"):
    st.markdown("""
    ### データ準備
    1. UbunBASE > リテールレポート > 価格弾力性分析
    2. 新規ユーザーに限定したい場合はチェックを入れる
    3. CSVエクスポート

    ### 価格弾力性とは
    - **1%の値引きに対して需要が何%変化するか**を示す指標
    - プラス = 値引きで需要増加、マイナス = 値引きで需要減少（逆効果）
    - 広告強化や季節性など他の要因も含まれるため、ASIN間の相対比較として活用

    ### 3パターンの特徴

    #### A. 閾値突破型
    - **グラフの特徴**: 軽値引きでは反応薄い/逆効果、深値引きで緑ゾーンへジャンプ
    - **示唆**: 心理的価格帯を割り込むと購買意欲が上がる可能性

    #### B. 軽値引き反応型
    - **グラフの特徴**: 軽値引きで既に緑ゾーンに入っている
    - **示唆**: 小さな値引きでも需要が反応しやすい

    #### C. 低空飛行型
    - **グラフの特徴**: どの値引き率でも赤ゾーン〜ゼロ付近
    - **示唆**: 値引き以外の施策（認知拡大等）を検討する余地あり

    #### D. 検証必要
    - データポイントが少なく判断材料不足
    """)