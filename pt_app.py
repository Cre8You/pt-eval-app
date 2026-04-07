import streamlit as st
import google.generativeai as genai

# ページ設定
st.set_page_config(page_title="理学療法評価AIアシスタント", layout="wide")

# 関節ごとの評価項目定義
JOINT_CONFIG = {
    "頸部": {
        "rom": {"屈曲": 60, "伸展": 50, "右側屈": 50, "左側屈": 50, "右回旋": 60, "左回旋": 60, "CV角": 50},
        "mmt": ["頸部伸筋群", "僧帽筋上部", "肩甲挙筋", "前鋸筋", "上腕二頭筋", "上腕三頭筋", "上腕筋", "腕橈骨筋"],
        "sensory": ["C5", "C6", "C7", "C8", "Th1"],
        "special": ["Cervical Flexion-Rotation Test", "Spurlingテスト", "Jacksonテスト", "頸椎牽引テスト", "Hoffmann反射", "Trener反射", "足クローヌス", "Babisnki反射", "Adsonテスト", "Wrightテスト", "Edenテスト"],
        "check": ["前方頭位(FHP)", "胸椎後弯・肩甲骨外転位"]
    },
    "腰部": {
        "rom": {"屈曲": 45, "伸展": 30, "右側屈": 20, "左側屈": 20, "右回旋": 45, "左回旋": 45},
        "mmt": ["体幹屈筋群", "体幹伸筋群", "腹斜筋群", "腸腰筋", "大殿筋"],
        "sensory": ["L1", "L2", "L3", "L4", "L5", "S1", "S2"],
        "special": ["SLRテスト", "FNSテスト", "Kempテスト", "Newtonテスト", "Thomasテスト", "Valsalvaテスト", "叩打痛"],
        "check": ["寝返り困難", "起き上がり困難", "立ち上がり困難", "長時間の座位困難", "間欠性跛行", "体幹の側方偏移"]
    },
    "肩関節": {
        "rom": {"屈曲": 180, "伸展": 50, "外転": 180, "内転": 0, "外旋(1st)": 60, "外旋(2nd)": 90, "外旋(3rd)": 90, "内旋(結帯)": None},
        "mmt": ["棘上筋", "棘下筋", "小円筋", "肩甲下筋", "三角筋(前・中・後)", "前鋸筋", "僧帽筋(上・中・下)"],
        "sensory": [],
        "special": ["Neerテスト", "Hawkins-Kennedy", "Drop Arm", "Painful arc(60-120°)", "Apprehension(前方)", "Apprehension(後方)", "Sulcus sign", "Speedテスト", "Yergasonテスト", "O'Brienテスト"],
        "check": ["洗濯物を干す困難", "着替え困難", "洗髪・洗体困難"]
    },
    "肘関節": {
        "rom": {"屈曲": 145, "伸展": 5, "回外": 90, "回内": 90, "外反": 15},
        "mmt": ["上腕二頭筋", "上腕三頭筋", "上腕筋", "腕橈骨筋", "円回内筋", "方形回内筋", "回外筋", "手関節伸筋", "手関節屈筋"],
        "sensory": [],
        "special": ["Thomsenテスト", "内側上顆炎テスト", "MCLストレス", "LCLストレス", "ピアノキーサイン", "Tinelサイン(肘部管)"],
        "check": ["食事困難", "洗顔困難", "洗髪困難", "生理的外反の左右差"]
    },
    "手関節": {
        "rom": {"掌屈": 90, "背屈": 70, "橈屈": 25, "尺屈": 55, "母指橈側外転": 60, "母指掌側外転": 90, "母指対立": 0},
        "mmt": ["手関節屈筋", "手関節伸筋"],
        "sensory": [],
        "special": ["Phalenテスト", "逆Phalenテスト", "Tinelサイン(手根管)", "Tinelサイン(ギヨン管)", "Finkelsteinテスト", "Watsonテスト", "TFCC負荷テスト", "Allenテスト", "Fromentサイン"],
        "check": ["食事困難", "洗顔困難", "洗髪困難", "創部の癒着"]
    },
    "手指": {
        "rom": {"MP屈曲": 90, "MP伸展": 0, "PIP屈曲": 100, "PIP伸展": 0, "DIP屈曲": 80, "DIP伸展": 0},
        "mmt": ["骨間筋", "虫様筋"],
        "sensory": [],
        "special": ["Elsonテスト", "Bunnel-Littlerテスト", "Tinelサイン(指神経)", "Fromentサイン", "側方動揺性(MP/PIP/DIP)"],
        "check": ["ばね指(A1圧痛・弾発)", "マレット変形", "スワンネック変形", "ボタン穴変形", "ヘバーデン結節", "ブシャール結節", "浮腫・熱感", "食事困難", "書字困難"]
    },
    "股関節": {
        "rom": {"屈曲": 125, "伸展": 15, "外転": 45, "内転": 20, "外旋": 45, "内旋": 45},
        "mmt": ["腸腰筋", "大殿筋", "中殿筋", "大腿筋膜張筋", "ハムストリングス"],
        "sensory": [],
        "special": ["FADIR", "後方インピンジメント", "FABER(Patrick)", "トレンドレンブルグ徴候", "デュシェンヌ徴候", "スクイーズテスト", "シットアップテスト", "アリスサイン", "テレスコーピング", "クレイグテスト"],
        "check": ["逃避性歩行", "跛行", "分回し歩行", "靴下の着脱困難", "爪切り困難", "脚長差", "骨盤代償"]
    },
    "膝関節": {
        "rom": {"屈曲": 130, "伸展": 0, "足関節背屈": 20, "足関節底屈": 45},
        "mmt": ["大腿四頭筋", "ハムストリングス", "大腿筋膜張筋", "中殿筋"],
        "sensory": [],
        "special": ["前方引き出し", "後方引き出し", "Lachman", "ピボットシフト", "内側側方動揺", "外側側方動揺", "McMurray", "Apley", "膝蓋跳動", "Grindテスト", "Apprehension", "Wilsonテスト"],
        "check": ["伸展ラグ", "Knee-in(スクワット)", "Knee-in(歩行)", "Lateral thrust", "階段昇降(下り)困難", "和式トイレ困難", "浮腫・熱感"]
    },
    "足関節": {
        "rom": {"背屈": 20, "底屈": 45},
        "mmt": ["前脛骨筋", "長腓骨筋", "短腓骨筋", "第三腓骨筋", "下腿三頭筋", "足趾屈筋", "足趾伸筋"],
        "sensory": [],
        "special": ["前方引き出し(ATFL)", "内反ストレス(CFL)", "外反ストレス(三角靭帯)", "トンプソンテスト", "スクイーズ(脛腓)", "衝突試験", "Tinelサイン(足根管)", "モートンテスト"],
        "check": ["蹴り出しの弱さ", "扁平足", "外反母趾", "内反小趾", "Toe-out", "階段下り困難", "しゃがみ込み困難"]
    }
}

st.title("🦴 Yudai式：AI理学療法アシスタント")

# --- サイドバー ---
with st.sidebar:
    st.header("🔑 AI設定")
    gemini_key = st.text_input("Gemini APIキーを入力", type="password")
    
    st.divider()
    st.header("📋 基本設定")
    patient_id = st.text_input("患者IDまたは氏名", "A様")
    diagnosis = st.text_input("病名を入力", "頸椎症性神経根症")
    joint = st.selectbox("評価する部位を選択", list(JOINT_CONFIG.keys()))
    
    # 頸部・腰部の場合は正中（単一入力）、それ以外は強制的に両側入力にする
    if joint in ["頸部", "腰部"]:
        side = "正中"
        sides_to_eval = ["正中"]
    else:
        side = "両側"
        sides_to_eval = ["右", "左"]

    st.divider()
    # 計画書変更
    st.header("🔄 計画書変更")
    st.caption("※ここに入力すると、治療方針と対応方針の３項目のみを更新して出力します。")
    patient_change = st.text_area("先月から今月の変化（任意）", placeholder="例：安静時痛は軽減したが、右下肢のしびれが残存。歩行距離は延びている。", height=120)

# --- メインエリア：評価入力 ---
st.header(f"【{joint}】の評価入力")

# 疼痛（NRS）入力
st.subheader("⚡ 疼痛 (NRS 0から10)")
c_nrs1, c_nrs2, c_nrs3 = st.columns(3)
nrs_options = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
with c_nrs1: nrs_rest = st.selectbox("安静時NRS", nrs_options, index=0)
with c_nrs2: nrs_night = st.selectbox("夜間時NRS", nrs_options, index=0)
with c_nrs3: nrs_move = st.selectbox("動作時NRS", nrs_options, index=0)

st.divider()

rom_results = {s: {} for s in sides_to_eval}
mmt_results = {s: {} for s in sides_to_eval}
sensory_results = {s: {} for s in sides_to_eval}
special_results = {s: {} for s in sides_to_eval}
check_results = {s: {} for s in sides_to_eval}

# ROM入力
st.subheader("📐 関節可動域 (ROM)")
st.caption("入力した項目のみカルテに反映されます。")
for item, ref in JOINT_CONFIG[joint]["rom"].items():
    if side == "両側":
        c1, c2 = st.columns(2)
        if item == "内旋(結帯)":
            opts = ["Th4から8", "Th9から12", "L1から5", "仙骨", "腸骨"]
            with c1: rom_results["右"][item] = st.selectbox(f"【右】{item}", opts, index=None, placeholder="未測定", key=f"r_{item}")
            with c2: rom_results["左"][item] = st.selectbox(f"【左】{item}", opts, index=None, placeholder="未測定", key=f"l_{item}")
        else:
            with c1: rom_results["右"][item] = st.number_input(f"【右】{item}", min_value=-50, max_value=200, value=None, step=1, placeholder=str(ref), key=f"r_{item}")
            with c2: rom_results["左"][item] = st.number_input(f"【左】{item}", min_value=-50, max_value=200, value=None, step=1, placeholder=str(ref), key=f"l_{item}")
    else:
        if item == "内旋(結帯)":
            opts = ["Th4から8", "Th9から12", "L1から5", "仙骨", "腸骨"]
            rom_results[side][item] = st.selectbox(f"【{side}】{item}", opts, index=None, placeholder="未測定", key=f"s_{item}")
        else:
            rom_results[side][item] = st.number_input(f"【{side}】{item}", min_value=-50, max_value=200, value=None, step=1, placeholder=str(ref), key=f"s_{item}")

st.divider()

# MMT入力
st.subheader("💪 徒手筋力テスト (MMT)")
st.caption("入力した項目のみ反映されます。")
mmt_opts = ["0", "1", "2", "3-", "3", "3+", "4", "5"]
for item in JOINT_CONFIG[joint]["mmt"]:
    if side == "両側":
        c1, c2 = st.columns(2)
        with c1: mmt_results["右"][item] = st.selectbox(f"【右】{item}", mmt_opts, index=None, placeholder="未実施", key=f"mr_{item}")
        with c2: mmt_results["左"][item] = st.selectbox(f"【左】{item}", mmt_opts, index=None, placeholder="未実施", key=f"ml_{item}")
    else:
        mmt_results[side][item] = st.selectbox(f"【{side}】{item}", mmt_opts, index=None, placeholder="未実施", key=f"ms_{item}")

st.divider()

# --- 感覚検査の独立セクション ---
if "sensory" in JOINT_CONFIG[joint] and JOINT_CONFIG[joint]["sensory"]:
    st.subheader("🪡 感覚検査（表在感覚異常など）")
    
    if joint == "頸部":
        with st.expander("📖 頸部のデルマトーム（知覚領域）を開く"):
            try:
                st.image("dermatome1.jpg", width=400)
            except Exception:
                st.info("💡 GitHubに「dermatome1.jpg」という名前で画像をアップロードすると、ここに図が表示されます！")
                
    elif joint == "腰部":
        with st.expander("📖 腰部のデルマトーム（知覚領域）を開く"):
            try:
                st.image("dermatome2.jpg", width=400)
            except Exception:
                st.info("💡 GitHubに「dermatome2.jpg」という名前で画像をアップロードすると、ここに図が表示されます！")

    st.caption("感覚異常がある領域にチェックを入れてください。")
    for s in sides_to_eval:
        prefix = f"【{s}】" if side == "両側" else ""
        c_sens = st.columns(4)
        for i, sens in enumerate(JOINT_CONFIG[joint]["sensory"]):
            with c_sens[i % 4]:
                sensory_results[s][sens] = st.checkbox(f"{prefix}{sens}", key=f"sens_{s}_{sens}")
    st.divider()

# 膝関節アライメント入力
nwb_kk = nwb_aa = wb_kk = wb_aa = None
hallux_valgus_r = hallux_valgus_l = arch_drop_r = arch_drop_l = weight_bearing_r = weight_bearing_l = None
if joint == "膝関節":
    st.subheader("🦵 アライメント・足部評価 (O脚・X脚など)")
    st.caption("K-K(膝間距離)、A-A(内果間距離)を横指で入力してください。")
    c_align1, c_align2 = st.columns(2)
    with c_align1:
        st.write("『非荷重位』")
        nwb_kk = st.number_input("【非荷重位】 K-K (横指)", min_value=0, max_value=20, value=None, step=1, key="nwb_kk")
        nwb_aa = st.number_input("【非荷重位】 A-A (横指)", min_value=0, max_value=20, value=None, step=1, key="nwb_aa")
    with c_align2:
        st.write("『荷重位』")
        wb_kk = st.number_input("【荷重位】 K-K (横指)", min_value=0, max_value=20, value=None, step=1, key="wb_kk")
        wb_aa = st.number_input("【荷重位】 A-A (横指)", min_value=0, max_value=20, value=None, step=1, key="wb_aa")
    
    st.write("『足部・荷重評価』")
    c_foot_r, c_foot_l = st.columns(2)
    with c_foot_r:
        hallux_valgus_r = st.selectbox("【右】外反母趾", ["あり", "なし"], index=None, placeholder="未評価", key="hallux_valgus_r")
        arch_drop_r = st.selectbox("【右】アーチの低下", ["あり", "なし"], index=None, placeholder="未評価", key="arch_drop_r")
        weight_bearing_r = st.selectbox("【右】荷重", ["前方", "後方"], index=None, placeholder="未評価", key="weight_bearing_r")
    with c_foot_l:
        hallux_valgus_l = st.selectbox("【左】外反母趾", ["あり", "なし"], index=None, placeholder="未評価", key="hallux_valgus_l")
        arch_drop_l = st.selectbox("【左】アーチの低下", ["あり", "なし"], index=None, placeholder="未評価", key="arch_drop_l")
        weight_bearing_l = st.selectbox("【左】荷重", ["前方", "後方"], index=None, placeholder="未評価", key="weight_bearing_l")
    st.divider()

# --- スペシャルテストの独立セクション ---
st.subheader("🧪 スペシャルテスト")
st.caption("該当する陽性テストにチェックを入れてください。")
if side == "両側":
    c_sp_r, c_sp_l = st.columns(2)
    with c_sp_r:
        st.write("『右』")
        for test in JOINT_CONFIG[joint]["special"]:
            special_results["右"][test] = st.checkbox(f"【右】{test}", key=f"sp_右_{test}")
    with c_sp_l:
        st.write("『左』")
        for test in JOINT_CONFIG[joint]["special"]:
            special_results["左"][test] = st.checkbox(f"【左】{test}", key=f"sp_左_{test}")
else:
    c_sp = st.columns(3)
    for i, test in enumerate(JOINT_CONFIG[joint]["special"]):
        with c_sp[i % 3]:
            special_results["正中"][test] = st.checkbox(f"{test}", key=f"sp_正中_{test}")
st.divider()

# --- ADL評価・観察項目の独立セクション ---
st.subheader("🚶 ADL評価・観察項目")
st.caption("該当する制限や観察項目にチェックを入れてください。")
if side == "両側":
    c_ch_r, c_ch_l = st.columns(2)
    with c_ch_r:
        st.write("『右』")
        for chk in JOINT_CONFIG[joint]["check"]:
            check_results["右"][chk] = st.checkbox(f"【右】{chk}", key=f"ch_右_{chk}")
    with c_ch_l:
        st.write("『左』")
        for chk in JOINT_CONFIG[joint]["check"]:
            check_results["左"][chk] = st.checkbox(f"【左】{chk}", key=f"ch_左_{chk}")
else:
    c_ch = st.columns(3)
    for i, chk in enumerate(JOINT_CONFIG[joint]["check"]):
        with c_ch[i % 3]:
            check_results["正中"][chk] = st.checkbox(f"{chk}", key=f"ch_正中_{chk}")
st.divider()

free_text = st.text_area("備考・自由入力（エンドフィールなど）", height=100)

# --- 実行ボタンとGemini連携ロジック ---
if st.button("🚀 AIによるカルテ・計画書の自動生成", use_container_width=True):
    if not gemini_key:
        st.error("左のサイドバーにAPIキーを入力してください！")
    else:
        pain_str = f"安静時{nrs_rest}, 夜間時{nrs_night}, 動作時{nrs_move}"
        
        mmt_list = []
        for item in JOINT_CONFIG[joint]["mmt"]:
            if side == "両側":
                r_val = mmt_results["右"][item]
                l_val = mmt_results["左"][item]
                if r_val or l_val:
                    mmt_list.append(f"{item}(右{r_val or '未実施'} / 左{l_val or '未実施'})")
            else:
                s = sides_to_eval[0]
                val = mmt_results[s][item]
                if val:
                    mmt_list.append(f"{item}({val})")
        mmt_str = "、\n".join(mmt_list) if mmt_list else "特記なし"

        sensory_pos = []
        if "sensory" in JOINT_CONFIG[joint]:
            sensory_pos = [f"{k}({s})" for s in sides_to_eval for k, v in sensory_results[s].items() if v]
        sensory_str = "、".join(sensory_pos) if sensory_pos else "特記なし"
        
        rom_list = []
        for item, ref in JOINT_CONFIG[joint]["rom"].items():
            if item == "内旋(結帯)":
                if side == "両側":
                    r_val = rom_results["右"][item]
                    l_val = rom_results["左"][item]
                    if r_val or l_val:
                        rom_list.append(f"{item}(右{r_val or '-'} / 左{l_val or '-'})")
                else:
                    s = sides_to_eval[0]
                    val = rom_results[s][item]
                    if val:
                        rom_list.append(f"{item}({val})")
            else:
                if side == "両側":
                    r_val = rom_results["右"][item]
                    l_val = rom_results["左"][item]
                    if r_val is not None or l_val is not None:
                        rom_list.append(f"{item}(右{r_val if r_val is not None else '-'}° / 左{l_val if l_val is not None else '-'}°)")
                else:
                    s = sides_to_eval[0]
                    val = rom_results[s][item]
                    if val is not None:
                        rom_list.append(f"{item}({val}°)")
        rom_str = "、\n".join(rom_list) if rom_list else "特記なし"

        knee_align_str = ""
        if joint == "膝関節":
            align_parts = []
            if nwb_kk is not None or nwb_aa is not None:
                align_parts.append(f"非荷重位：K-K {nwb_kk if nwb_kk is not None else '-'}横指 / A-A {nwb_aa if nwb_aa is not None else '-'}横指")
            if wb_kk is not None or wb_aa is not None:
                align_parts.append(f"荷重位：K-K {wb_kk if wb_kk is not None else '-'}横指 / A-A {wb_aa if wb_aa is not None else '-'}横指")
            
            foot_parts = []
            if hallux_valgus_r or hallux_valgus_l:
                foot_parts.append(f"外反母趾(右{hallux_valgus_r or '-'} / 左{hallux_valgus_l or '-'})")
            if arch_drop_r or arch_drop_l:
                foot_parts.append(f"アーチの低下(右{arch_drop_r or '-'} / 左{arch_drop_l or '-'})")
            if weight_bearing_r or weight_bearing_l:
                foot_parts.append(f"荷重(右{weight_bearing_r or '-'} / 左{weight_bearing_l or '-'})")
            
            if foot_parts:
                align_parts.append("足部・荷重：" + "、".join(foot_parts))

            if align_parts:
                knee_align_str = "\n・アライメント・足部評価：\n  " + "\n  ".join(align_parts)

        special_pos = [f"{k}({s})" for s in sides_to_eval for k, v in special_results[s].items() if v]
        check_pos = [f"{k}({s})" for s in sides_to_eval for k, v in check_results[s].items() if v]

        if patient_change:
            prompt = f"""
あなたは19年の経験を持つベテラン理学療法士です。以下の評価データと【先月から今月の変化】をもとに、指定された【文字数制限】と【条件】を厳格に守って文章を作成してください。

【データ】
・患者：{patient_id}（病名：{diagnosis}）
・部位：{joint} ({side})
・先月から今月の変化：{patient_change}
・疼痛：{pain_str}
・筋力低下・MMT：
{mmt_str}
・感覚異常：{sensory_str}
・可動域制限・ROM：
{rom_str}{knee_align_str}
・陽性テスト：{"、".join(special_pos) if special_pos else "特記なし"}
・動作/制限：{"、".join(check_pos) if check_pos else "特記なし"}
・備考：{free_text}

【出力形式・条件】
今回は「計画書の更新」です。以下の３項目【のみ】を出力してください。
※重要：出力の冒頭や末尾に挨拶や前置きは一切不要です。いきなり【治療方針】の見出しから出力してください。
※重要：出力する文章にはアスタリスク記号を一切使用しないでください。強調する場合は「【】」を使用してください。

・治療方針（120文字以内。変化の経過を踏まえて記載）
・参加制限に対する具体的な対応方針（200文字以内、簡潔な「です・ます調」。変化の経過を踏まえて記載）
・機能障害に対する具体的な対応方針（200文字以内、簡潔な「です・ます調」。変化の経過を踏まえて記載）

※定型文の羅列ではなく、この患者の具体的な症状と生活背景を推察した自然な専門用語で作成すること。
※【具体的な対応方針】の2項目は「敬体（です・ます調）」を使用してください。その際、過剰な敬語や話し言葉は厳禁です。シンプルな「〜していきます」「〜を行います」といった表現を使い、かつ文末が「ます」で連続しすぎないよう人間らしい自然なリズムで記載してください。
"""
        else:
            prompt = f"""
あなたは19年の経験を持つベテラン理学療法士です。以下の評価データから、指定された【文字数制限】と【条件】を厳格に守って文章を作成してください。

【データ】
・患者：{patient_id}（病名：{diagnosis}）
・部位：{joint} ({side})
・疼痛：{pain_str}
・筋力低下・MMT：
{mmt_str}
・感覚異常：{sensory_str}
・可動域制限・ROM：
{rom_str}{knee_align_str}
・陽性テスト：{"、".join(special_pos) if special_pos else "特記なし"}
・動作/制限：{"、".join(check_pos) if check_pos else "特記なし"}
・備考：{free_text}

【出力形式・条件】
以下の構成と文字数制限を必ず遵守して出力してください。
※重要：出力の冒頭や末尾に挨拶や前置きは一切不要です。いきなり【電子カルテ用】の見出しから出力してください。
※重要：出力する文章にはアスタリスク記号を一切使用しないでください。強調する場合は「【】」を使用してください。

【電子カルテ用】
・実施した評価結果を、項目ごとに【改行】や【箇条書き（・）】を用いて、視覚的にスッキリとしたレイアウトにしてください。
・優先順位が高い問題点を３つ、改行して箇条書きで挙げます（改善が見込める、かつ時間がかからない視点から判断）。

【計画書用】
・疼痛について（20文字以内）
・筋力について（20文字以内）
・感覚異常について（20文字以内）
・可動域について（20文字以内）
・短期目標（100文字以内）
・長期目標（50文字以内）
・治療方針（120文字以内）
・治療内容（必要な治療プログラムを箇条書きで列挙、最大6行）
・参加制限に対する具体的な対応方針（200文字以内、簡潔な「です・ます調」）
・機能障害に対する具体的な対応方針（200文字以内、簡潔な「です・ます調」）

※定型文の羅列ではなく、この患者の具体的な症状と生活背景を推察した自然な専門用語で作成すること。
※【具体的な対応方針】の2項目のみ「敬体（です・ます調）」を使用してください。その際、過剰な敬語や話し言葉は厳禁です。シンプルな「〜していきます」「〜を行います」といった表現を使い、かつ文末が「ます」で連続しすぎないよう人間らしい自然なリズムで記載してください。
"""

        try:
            with st.spinner("Geminiが文章を構成しています..."):
                genai.configure(api_key=gemini_key)
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                if not available_models:
                    st.error("モデルが見つかりませんでした。")
                else:
                    target_model_name = next((m for m in available_models if 'flash' in m), available_models[0])
                    model = genai.GenerativeModel(target_model_name)
                    response = model.generate_content(prompt)
                    st.subheader("✨ Geminiが作成した個別カルテ・計画書")
                    st.success("以下のテキストエリア内をクリックし、Command+Aで全選択してコピーしてください。")
                    st.text_area("出力結果", response.text, height=600)
                    
        except Exception as e:
            st.error(f"エラーが発生しました：{e}")
