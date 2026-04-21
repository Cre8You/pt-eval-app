import streamlit as st
import google.generativeai as genai
import datetime

# ページ設定
st.set_page_config(page_title="理学療法評価AIアシスタント", layout="wide")

# 関節ごとの評価項目定義
JOINT_CONFIG = {
    "頸部": {
        "rom": {"屈曲": 60, "伸展": 50, "右側屈": 50, "左側屈": 50, "右回旋": 60, "左回旋": 60, "CV角": 50},
        "mmt": ["頸部伸筋群", "僧帽筋上部", "肩甲挙筋", "前鋸筋", "上腕二頭筋", "上腕三頭筋", "上腕筋", "腕橈骨筋"],
        "sensory": ["C5", "C6", "C7", "C8", "Th1"],
        "special": ["Cervical Flexion-Rotation Test", "Spurlingテスト(右)", "Spurlingテスト(左)", "Jacksonテスト(右)", "Jacksonテスト(左)", "頸椎牽引テスト", "Hoffmann反射", "Trener反射", "足クローヌス", "Babisnki反射", "Adsonテスト", "Wrightテスト", "Edenテスト"],
        "check": ["前方頭位(FHP)", "胸椎後弯・肩甲骨外転位"]
    },
    "腰部": {
        "rom": {
            "屈曲": 45, "伸展": 30, "右側屈": 20, "左側屈": 20, "右回旋": 45, "左回旋": 45,
            "股関節屈曲": 125, "股関節伸展": 15, "股関節外転": 45, "股関節内転": 20, "股関節外旋": 45, "股関節内旋": 45,
            "膝関節屈曲": 130, "膝関節伸展": 0, "足関節背屈": 20, "足関節底屈": 45
        },
        "mmt": ["体幹屈筋群", "体幹伸筋群", "腹斜筋群", "腸腰筋", "大殿筋", "中殿筋", "大腿筋膜張筋"],
        "sensory": ["L1", "L2", "L3", "L4", "L5", "S1", "S2"],
        "special": ["SLRテスト", "Active-SLR", "FNSテスト", "Kempテスト", "Newtonテスト", "Thomasテスト", "Valsalvaテスト", "叩打痛"],
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
        "rom": {"屈曲": 125, "伸展": 15, "外転": 45, "内転": 20, "外旋": 45, "内旋": 45, "SLR": 70},
        "mmt": ["腸腰筋", "大殿筋", "中殿筋", "大腿筋膜張筋", "ハムストリングス"],
        "sensory": [],
        "special": ["FADIR", "後方インピンジメント", "FABER(Patrick)", "トレンドレンブルグ徴候", "デュシェンヌ徴候", "スクイーズテスト", "シットアップテスト", "アリスサイン", "テレスコーピング", "クレイグテスト"],
        "check": ["逃避性歩行", "跛行", "分回し歩行", "靴下の着脱困難", "爪切り困難", "脚長差", "骨盤代償"]
    },
    "膝関節": {
        "rom": {"屈曲": 130, "伸展": 0, "足関節背屈": 20, "足関節底屈": 45, "SLR": 70},
        "mmt": ["大腿四頭筋", "ハムストリングス", "大腿筋膜張筋", "中殿筋"],
        "sensory": [],
        "special": ["前方引き出し", "後方引き出し", "Lachman", "ピボットシフト", "内側側方動揺", "外側側方動揺", "McMurray", "Apley", "膝蓋跳動", "Grindテスト", "Apprehension", "Wilsonテスト"],
        "check": ["伸展ラグ", "Knee-in(スクワット)", "Knee-in(歩行)", "Lateral thrust", "階段昇降(下り)困難", "和式トイレ困難", "浮腫・熱感"]
    },
    "足関節": {
        "rom": {"背屈": 20, "底屈": 45, "膝関節屈曲": 130, "膝関節伸展": 0, "SLR": 70},
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
    
    # 💡【修正箇所】latestを廃止し、確実に1日1500回使える「1.5-flash」を指名！
    MODEL_OPTIONS = {
        "gemini-1.5-flash（1日1500回・基本）": "gemini-1.5-flash",
        "gemini-3.0-flash（1日20回・最新鋭！）": "gemini-3.0-flash",
        "gemini-2.5-flash（1日20回・高性能！）": "gemini-2.5-flash",
        "gemini-1.5-pro（1日50回・推論特化）": "gemini-1.5-pro"
    }
    
    st.divider()
    st.header("🧠 モデル設定")
    selected_label = st.selectbox("使用するAIモデル", list(MODEL_OPTIONS.keys()), index=0)
    selected_model = MODEL_OPTIONS[selected_label]
    
    # 安心のための確認用テキストを表示
    st.caption(f"現在の接続先: {selected_model}")
            
    st.divider()
    st.header("📋 基本設定")
    patient_id = st.text_input("患者ID", "000000")
    joint = st.selectbox("評価する部位を選択", list(JOINT_CONFIG.keys()))
    diagnosis = st.text_input("病名を入力", "腰椎椎間板ヘルニア")
    
    onset_date = st.date_input("発症日", datetime.date.today())
    rehab_start_date = st.date_input("リハ開始日", datetime.date.today())
    
    if joint in ["頸部"]:
        side = "正中"
        sides_to_eval = ["正中"]
    elif joint == "腰部":
        side = "両側"
        sides_to_eval = ["右", "左", "正中"]
    else:
        side = "両側"
        sides_to_eval = ["右", "左"]

    st.divider()
    st.header("🔄 計画書更新（再評価）")
    patient_change = st.text_area("先月から今月の変化（任意）", placeholder="例：安静時痛は軽減したが、右下肢のしびれが残存。", height=120)

# --- メインエリア：評価入力 ---
st.header(f"【{joint}】の評価入力")

# 疼痛（NRS）
st.subheader("⚡ 疼痛 (NRS 0-10)")
c_nrs1, c_nrs2, c_nrs3 = st.columns(3)
nrs_options = list(range(11))
with c_nrs1: nrs_rest = st.selectbox("安静時NRS", nrs_options, index=0)
with c_nrs2: nrs_night = st.selectbox("夜間時NRS", nrs_options, index=0)
with c_nrs3: nrs_move = st.selectbox("動作時NRS", nrs_options, index=0)

pain_notes = st.text_area("疼痛に関する特記事項（部位、性質、放散痛など）", height=80, placeholder="例：右L5領域から下腿外側にかけての放散痛あり。")

st.divider()

rom_results = {s: {} for s in sides_to_eval}
rom_pain_results = {s: {} for s in sides_to_eval}
mmt_results = {s: {} for s in sides_to_eval}
sensory_results = {s: {} for s in sides_to_eval}
special_results = {s: {} for s in sides_to_eval}
check_results = {s: {} for s in sides_to_eval}

# ROM入力（整数化・SLR追加）
st.subheader("📐 関節可動域 (ROM)")
for item, ref in JOINT_CONFIG[joint]["rom"].items():
    is_median_item = (joint == "腰部" and item in ["屈曲", "伸展", "右側屈", "左側屈", "右回旋", "左回旋"]) or joint == "頸部"
    
    if is_median_item:
        c_val, c_pain = st.columns([3, 1])
        with c_val: rom_results["正中"][item] = st.number_input(f"【正中】{item}", value=None, step=1, format="%d", placeholder=str(ref), key=f"c_{item}")
        with c_pain:
            st.markdown("<div style='margin-top: 32px;'></div>", unsafe_allow_html=True)
            rom_pain_results["正中"][item] = st.checkbox("疼痛あり", key=f"cpain_{item}")
    elif side == "両側":
        cr_val, cr_pain, cl_val, cl_pain = st.columns([3, 1, 3, 1])
        if item == "内旋(結帯)":
            opts = ["Th4-8", "Th9-12", "L1-5", "仙骨", "腸骨"]
            with cr_val: rom_results["右"][item] = st.selectbox(f"【右】{item}", opts, index=None, key=f"r_{item}")
            with cl_val: rom_results["左"][item] = st.selectbox(f"【左】{item}", opts, index=None, key=f"l_{item}")
        else:
            with cr_val: rom_results["右"][item] = st.number_input(f"【右】{item}", value=None, step=1, format="%d", placeholder=str(ref), key=f"r_{item}")
            with cl_val: rom_results["左"][item] = st.number_input(f"【左】{item}", value=None, step=1, format="%d", placeholder=str(ref), key=f"l_{item}")
        with cr_pain:
            st.markdown("<div style='margin-top: 32px;'></div>", unsafe_allow_html=True)
            rom_pain_results["右"][item] = st.checkbox("疼痛あり", key=f"rpain_{item}")
        with cl_pain:
            st.markdown("<div style='margin-top: 32px;'></div>", unsafe_allow_html=True)
            rom_pain_results["左"][item] = st.checkbox("疼痛あり", key=f"lpain_{item}")

st.divider()

# MMT入力
st.subheader("💪 徒手筋力テスト (MMT)")
mmt_opts = ["0", "1", "2", "3-", "3", "3+", "4", "5"]
for item in JOINT_CONFIG[joint]["mmt"]:
    is_median_item = (joint == "腰部" and item in ["体幹屈筋群", "体幹伸筋群", "腹斜筋群"]) or joint == "頸部"
    if is_median_item:
        mmt_results["正中"][item] = st.selectbox(f"【正中】{item}", mmt_opts, index=None, key=f"mc_{item}")
    elif side == "両側":
        c1, c2 = st.columns(2)
        with c1: mmt_results["右"][item] = st.selectbox(f"【右】{item}", mmt_opts, index=None, key=f"mr_{item}")
        with c2: mmt_results["左"][item] = st.selectbox(f"【左】{item}", mmt_opts, index=None, key=f"ml_{item}")

st.divider()

# --- 感覚検査 ---
if "sensory" in JOINT_CONFIG[joint] and JOINT_CONFIG[joint]["sensory"]:
    st.subheader("🪡 感覚検査（表在感覚異常など）")
    if joint == "頸部":
        with st.expander("📖 頸部のデルマトーム（知覚領域）を開く"):
            try: st.image("dermatome1.jpg", width=400)
            except: pass
    elif joint == "腰部":
        with st.expander("📖 腰部のデルマトーム（知覚領域）を開く"):
            try: st.image("dermatome2.jpg", width=400)
            except: pass

    st.caption("感覚異常がある領域にチェックを入れてください。")
    sensory_sides = ["右", "左"] if side == "両側" else ["正中"]
    for s in sensory_sides:
        prefix = f"【{s}】" if side == "両側" else ""
        c_sens = st.columns(4)
        for i, sens in enumerate(JOINT_CONFIG[joint]["sensory"]):
            with c_sens[i % 4]:
                sensory_results[s][sens] = st.checkbox(f"{prefix}{sens}", key=f"sens_{s}_{sens}")
    st.divider()

# --- スペシャルテスト ---
st.subheader("🧪 スペシャルテスト")
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

# --- 動作観察（腰・股・膝・足関節のみ） ---
motion_kito = motion_slr_pronation = motion_slr_post = motion_slr_toe = motion_slr_arch = False
motion_walking = ""
if joint in ["腰部", "股関節", "膝関節", "足関節"]:
    st.subheader("👀 動作観察 (立ち上がり・片脚立位・歩行)")
    c_m1, c_m2 = st.columns(2)
    with c_m1:
        st.write("『立ち上がり』")
        motion_kito = st.checkbox("Knee-in Toe-out (KITO)")
    with c_m2:
        st.write("『片脚立位』")
        motion_slr_pronation = st.checkbox("足部回内")
        motion_slr_post = st.checkbox("後方重心")
        motion_slr_toe = st.checkbox("足趾への荷重不足")
        motion_slr_arch = st.checkbox("内側アーチの低下")
    
    motion_walking = st.text_area("『歩行』に関する観察・特記事項", height=80, placeholder="例：歩行時に股関節伸展代償としての腰椎前弯増強が見られる。")
    st.divider()

# --- ADL評価・観察項目 ---
st.subheader("🚶 ADL評価・観察項目")
if side == "両側" and joint != "腰部":
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

adl_notes = st.text_area("ADLに関する特記事項（その他の詳細など）", height=80)

st.divider()

# PT考察
st.subheader("🧠 PT考察")
pt_observation = st.text_area("PTの臨床推論・原因の仮説", height=120)

st.divider()

# 実行ボタン
if st.button("🚀 生成開始", use_container_width=True):
    if not gemini_key:
        st.error("APIキーを入力してください")
    else:
        std_deadline = onset_date + datetime.timedelta(days=149)
        rehab_deadline = rehab_start_date + datetime.timedelta(days=149)
        std_deadline_str = std_deadline.strftime("%Y/%m/%d")
        rehab_deadline_str = rehab_deadline.strftime("%Y/%m/%d")

        # データ変換
        pain_str = f"安静時{nrs_rest}, 夜間時{nrs_night}, 動作時{nrs_move}"
        if pain_notes: pain_str += f"（特記：{pain_notes}）"

        def fmt_val(v): return str(int(v)) if isinstance(v, (int, float)) else str(v)

        rom_list = []
        for item in JOINT_CONFIG[joint]["rom"]:
            for s in sides_to_eval:
                val = rom_results[s].get(item)
                if val is not None:
                    p = "（疼痛あり）" if rom_pain_results[s].get(item) else ""
                    rom_list.append(f"{item}({s}{fmt_val(val)}{p})")
                    
        special_pos = [f"{k}" if s == "正中" else f"{k}({s})" for s in sides_to_eval for k, v in special_results[s].items() if v]
        check_pos = [f"{k}" if s == "正中" else f"{k}({s})" for s in sides_to_eval for k, v in check_results[s].items() if v]
        adl_str = "、".join(check_pos) if check_pos else "特記なし"
        if adl_notes: adl_str += f" / 特記：{adl_notes}"

        motion_prompt_line = ""
        if joint in ["腰部", "股関節", "膝関節", "足関節"]:
            m_parts = []
            if motion_kito: m_parts.append("立ち上がり:KITO")
            slr_issues = [txt for cond, txt in zip([motion_slr_pronation, motion_slr_post, motion_slr_toe, motion_slr_arch], ["足部回内", "後方重心", "足趾荷重不足", "内側アーチ低下"]) if cond]
            if slr_issues: m_parts.append("片脚立位:" + "、".join(slr_issues))
            if motion_walking: m_parts.append(f"歩行:{motion_walking}")
            if m_parts: motion_prompt_line = f"\n・動作観察：{'、'.join(m_parts)}"

        common_data = f"""
【データ】
・病名：{diagnosis} / 部位：{joint}
・疼痛：{pain_str}
・ROM：{"、".join(rom_list) if rom_list else "特記なし"}{motion_prompt_line}
・陽性テスト：{"、".join(special_pos) if special_pos else "特記なし"}
・動作/制限(ADL)：{adl_str}
・PT考察：{pt_observation if pt_observation else "特記なし"}
"""
        
        if patient_change:
            prompt = f"""
あなたは19年の経験を持つベテラン理学療法士です。以下の評価データと【先月から今月の変化】をもとに、指定された【条件】を厳格に守って文章を作成してください。

{common_data}
・先月から今月の変化：{patient_change}

【条件】
今回は「計画書の更新」です。以下の【５項目】のみを出力してください。挨拶や前置きは不要です。文章中での強調記号（カッコやアスタリスク等）は一切使用しないでください（指定した項目名のみ【】を使用可）。
・【短期目標】（100文字以内。変化の経過を踏まえて記載）
・【長期目標】（50文字以内。変化の経過を踏まえて記載）
・【治療方針】（120文字以内。変化の経過とPT考察を踏まえて記載）
・【参加制限に対する具体的な対応方針】（200文字以内、簡潔な「です・ます調」。文脈に合わせて適宜改行を入れ、読みやすく整理すること）
・【機能障害に対する具体的な対応方針】（200文字以内、簡潔な「です・ます調」。文脈に合わせて適宜改行を入れ、読みやすく整理すること）
"""
        else:
            prompt = f"""
あなたは19年の経験を持つベテラン理学療法士です。以下のデータを元に電子カルテと計画書を作成してください。

{common_data}

【条件】
以下の構成と文字数制限を必ず遵守して出力してください。挨拶や前置きは不要です。いきなり【電子カルテ用】から出力してください。文章中での強調記号（カッコやアスタリスク等）は一切使用しないでください（指定した項目名のみ【】を使用可）。

【電子カルテ用】
・実施した評価結果を、項目ごとに改行や箇条書きを用いて視覚的にスッキリとしたレイアウトで記載。
・優先順位が高い問題点を３つ、改行して箇条書きで挙げます（改善が見込める、かつPT考察から導き出される視点から判断。※長くなりすぎないよう、1項目につき30文字程度で簡潔にまとめてください）。
・最後に必ず以下の期限をそのまま記載してください：
  【標準算定期限】：{std_deadline_str}
  【リハビリ期限】：{rehab_deadline_str}

【計画書用】
・【疼痛について】（20文字以内）
・【筋力について】（20文字以内）
・【感覚異常について】（20文字以内）
・【可動域について】（20文字以内。疼痛を伴う制限がある場合はその旨を記載）
・【短期目標】（100文字以内）
・【長期目標】（50文字以内）
・【治療方針】（120文字以内）
・【治療内容】（必要な治療プログラムを箇条書きで列挙、最大6行）
・【参加制限に対する具体的な対応方針】（200文字以内、簡潔な「です・ます調」。文脈に合わせて適宜改行を入れ、読みやすく整理すること）
・【機能障害に対する具体的な対応方針】（200文字以内、簡潔な「です・ます調」。文脈に合わせて適宜改行を入れ、読みやすく整理すること）
"""

        try:
            with st.spinner(f"Gemini（{selected_label}）がカルテ・計画書を作成中です... 少々お待ちください！✨"):
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel(selected_model)
                response = model.generate_content(prompt)
                
            st.subheader("✨ 出力結果")
            st.text_area("Copy & Paste", response.text, height=600)
        except Exception as e:
            st.error(f"エラー: {e}")
