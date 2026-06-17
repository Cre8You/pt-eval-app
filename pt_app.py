import streamlit as st
import google.generativeai as genai
import datetime

# ページ設定
st.set_page_config(page_title="理学療法評価AIアシスタント", layout="wide")

# 関節ごとの評価項目定義
JOINT_CONFIG = {
    "頸部": {
        "rom": {"屈曲": 60, "伸展": 50, "右側屈": 50, "左側屈": 50, "右回旋": 60, "左回旋": 60, "CV角": 50},
        "mmt": ["頚部伸筋群", "僧帽筋上部", "肩甲挙筋", "前鋸筋", "上腕二頭筋", "肩甲下筋", "上腕筋", "腕橈骨筋"],
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
        "special": ["Active-SLR", "FNSテスト", "Kempテスト", "Newtonテスト", "Valsalvaテスト", "叩打痛"],
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

# スペシャルテストの説明文
SPECIAL_TEST_HELP = {
    # 頸部
    "Cervical Flexion-Rotation Test": "【方法】最大屈曲位で左右に回旋させる。【陽性】回旋角度の減少や頭痛誘発（上位頸椎障害）。",
    "Spurlingテスト(右)": "【方法】頭部を右側に側屈・伸展させ、下方に圧迫。【陽性】右側の上肢への放散痛（神経根症状）。",
    "Spurlingテスト(左)": "【方法】頭部を左側に側屈・伸展させ、下方に圧迫。【陽性】左側の上肢への放散痛（神経根症状）。",
    "Jacksonテスト(右)": "【方法】頭部を伸展位で下方に圧迫。【陽性】上肢への放散痛（神経根症状）。",
    "Jacksonテスト(左)": "【方法】頭部を伸展位で下方に圧迫。【陽性】上肢への放散痛（神経根症状）。",
    "頸椎牽引テスト": "【方法】頭部を上方に牽引する。【陽性】上肢の痛みやしびれが軽減。",
    "Hoffmann反射": "【方法】中指のDIP関節を掌屈させて弾く。【陽性】母指や示指が屈曲（病的反射）。",
    "Trener反射": "【方法】中指の掌側からタッピングする。【陽性】母指などの屈曲（病的反射）。",
    "足クローヌス": "【方法】足関節を急に背屈させる。【陽性】律動的な底屈運動が続く（病的反射）。",
    "Babisnki反射": "【方法】足底の外側から母指球に向けて擦過する。【陽性】母指の背屈と他趾の扇状開脚（病的反射）。",
    "Adsonテスト": "【方法】患側へ回旋・伸展し深吸気で息止め。【陽性】橈骨動脈の拍動減弱（斜角筋症候群）。",
    "Wrightテスト": "【方法】両上肢を挙上・外旋位にする。【陽性】橈骨動脈の拍動減弱（小胸筋症候群）。",
    "Edenテスト": "【方法】両肩を下方に引き下げる（胸を張る）。【陽性】橈骨動脈の拍動減弱（肋鎖症候群）。",
    # 腰部
    "Active-SLR": "【方法】背臥位で自力で下肢を挙上させる。【陽性】挙上困難や疼痛（骨盤帯の不安定性など）。",
    "FNSテスト": "【方法】腹臥位で膝90度屈曲し股関節を伸展。【陽性】大腿前面の放散痛（L2-L4神経根障害）。",
    "Kempテスト": "【方法】体幹を斜め後方に伸展・回旋させ圧迫。【陽性】下肢放散痛（神経根）または局所痛（椎間関節）。",
    "Newtonテスト": "【方法】腹臥位で仙腸関節部を圧迫する。【陽性】仙腸関節部の疼痛（仙腸関節障害）。",
    "Valsalvaテスト": "【方法】息をこらえて腹圧を高める（いきむ）。【陽性】腰痛や下肢の放散痛増悪（髄腔内圧上昇）。",
    "叩打痛": "【方法】棘突起などを軽く叩く。【陽性】局所の強い疼痛（圧迫骨折、感染などを疑う）。",
    # 肩関節
    "Neerテスト": "【方法】肩甲骨を固定し上肢を強制挙上。【陽性】肩峰下インピンジメントによる疼痛。",
    "Hawkins-Kennedy": "【方法】肩関節90度屈曲位で内旋を強制。【陽性】インピンジメントによる疼痛。",
    "Drop Arm": "【方法】他動で90度外転させ、ゆっくり下ろさせる。【陽性】保持できず腕が落ちる（腱板断裂）。",
    "Painful arc(60-120°)": "【方法】自動外転を行わせる。【陽性】60〜120度で痛みが出現（インピンジメント症候群）。",
    "Apprehension(前方)": "【方法】背臥位で肩関節外転・外旋を強制。【陽性】脱臼への不安感や抵抗（前方不安定性）。",
    "Apprehension(後方)": "【方法】屈曲・内旋位から後方に圧を加える。【陽性】不安感や抵抗（後方不安定性）。",
    "Sulcus sign": "【方法】上肢を下方に牽引する。【陽性】肩峰下に陥凹が出現（下方不安定性）。",
    "Speedテスト": "【方法】肘伸展・前腕回外位で屈曲に抵抗。【陽性】結節間溝部の疼痛（上腕二頭筋長頭腱炎）。",
    "Yergasonテスト": "【方法】肘90度屈曲位で回外と外旋に抵抗。【陽性】結節間溝部の疼痛（上腕二頭筋長頭腱炎）。",
    "O'Brienテスト": "【方法】90度屈曲・10度水平内転位で下方に抵抗。【陽性】内旋位のみで疼痛誘発（SLAP損傷など）。",
    # 肘関節
    "Thomsenテスト": "【方法】肘伸展位で手関節背屈に抵抗。【陽性】外側上顆部の疼痛（テニス肘）。",
    "内側上顆炎テスト": "【方法】肘伸展・前腕回外位で手関節掌屈に抵抗。【陽性】内側上顆部の疼痛（ゴルフ肘）。",
    "MCLストレス": "【方法】肘軽度屈曲位で外反ストレスを加える。【陽性】内側靭帯部の疼痛や動揺性。",
    "LCLストレス": "【方法】肘軽度屈曲位で内反ストレスを加える。【陽性】外側靭帯部の疼痛や動揺性。",
    "ピアノキーサイン": "【方法】尺骨頭を掌側へ押圧する。【陽性】浮き上がるような動揺性（遠位橈尺関節不安定性）。",
    "Tinelサイン(肘部管)": "【方法】肘部管（内側上顆の後方）を叩打。【陽性】尺骨神経領域への放散痛やしびれ。",
    # 手関節
    "Phalenテスト": "【方法】両手関節を最大掌屈位で約1分間保持。【陽性】正中神経領域のしびれ増悪（手根管症候群）。",
    "逆Phalenテスト": "【方法】両手関節を最大背屈位で約1分間保持。【陽性】正中神経領域のしびれ増悪（手根管症候群）。",
    "Tinelサイン(手根管)": "【方法】手関節の手根管部を叩打。【陽性】正中神経領域への放散痛やしびれ。",
    "Tinelサイン(ギヨン管)": "【方法】手関節の豆状骨橈側を叩打。【陽性】尺骨神経領域への放散痛やしびれ。",
    "Finkelsteinテスト": "【方法】母指を握り込み、手関節を尺屈させる。【陽性】橈骨茎状突起部の疼痛（ドケルバン病）。",
    "Watsonテスト": "【方法】舟状骨を圧迫しながら手関節を尺屈から橈屈。【陽性】クリック音や疼痛（舟状月状骨間の不安定性）。",
    "TFCC負荷テスト": "【方法】手関節を尺屈させ圧迫しながら回旋ストレス。【陽性】尺側部の疼痛やクリック（TFCC損傷）。",
    "Allenテスト": "【方法】橈尺両動脈を圧迫後、片方ずつ解除する。【陽性】血流の回復が遅延（動脈閉塞）。",
    "Fromentサイン": "【方法】紙を母指と示指で強くつまませる。【陽性】母指IP関節が屈曲する（尺骨神経麻痺）。",
    # 手指
    "Elsonテスト": "【方法】PIPを90度屈曲させPIP伸展に抵抗。【陽性】DIP関節が剛直になる（中央索断裂）。",
    "Bunnel-Littlerテスト": "【方法】MP伸展位と屈曲位でPIPを他動屈曲。【陽性】MP伸展位でPIP屈曲制限が強まる（内在筋拘縮）。",
    "Tinelサイン(指神経)": "【方法】指神経に沿って叩打する。【陽性】指先への放散痛やしびれ。",
    "側方動揺性(MP/PIP/DIP)": "【方法】各関節を伸展・屈曲位で側方へストレス。【陽性】動揺性がある（側副靭帯損傷）。",
    # 股関節
    "FADIR": "【方法】股関節屈曲・内転・内旋を強制。【陽性】鼠径部痛やクリック（前方インピンジメント）。",
    "後方インピンジメント": "【方法】股関節伸展・外旋を強制。【陽性】臀部痛やクリック（後方インピンジメント）。",
    "FABER(Patrick)": "【方法】屈曲・外転・外旋（あぐら）で膝を下方に押す。【陽性】股関節痛や仙腸関節痛。",
    "トレンドレンブルグ徴候": "【方法】片脚立位をとらせる。【陽性】遊脚側の骨盤が下がる（中殿筋の機能不全）。",
    "デュシェンヌ徴候": "【方法】歩行時または片脚立位を観察。【陽性】立脚側に体幹を傾斜させる（中殿筋機能低下）。",
    "スクイーズテスト": "【方法】両下肢の間に拳を挟み内転させる。【陽性】鼠径部や恥骨部の疼痛（グロインペインなど）。",
    "シットアップテスト": "【方法】背臥位から上体を起こす。【陽性】脚の長さの左右差が変化する（骨盤の傾斜・ねじれ）。",
    "アリスサイン": "【方法】背臥位で両膝を立てる。【陽性】膝の高さに左右差がある（脚長差や脱臼）。",
    "テレスコーピング": "【方法】背臥位で大腿骨を長軸方向に押し引きする。【陽性】大腿骨頭が浮き上がる異常な動き。",
    "クレイグテスト": "【方法】腹臥位膝90度屈曲で大転子が突出する内外旋角度を測定。【陽性】前捻角の異常。",
    # 膝関節
    "前方引き出し": "【方法】膝90度屈曲位で脛骨を前方に引き出す。【陽性】前方移動量が増大（ACL損傷）。",
    "後方引き出し": "【方法】膝90度屈曲位で脛骨を後方に押し込む。【陽性】後方移動量が増大（PCL損傷）。",
    "Lachman": "【方法】膝20〜30度屈曲位で脛骨を前方に引き出す。【陽性】前方移動量増大・終末感消失（ACL損傷）。",
    "ピボットシフト": "【方法】伸展位から内旋・外反ストレスを加え屈曲。【陽性】20〜30度で整復音やショック（ACL損傷）。",
    "内側側方動揺": "【方法】膝伸展・30度屈曲位で外反ストレスを加える。【陽性】内側裂隙の開大や疼痛（MCL損傷）。",
    "外側側方動揺": "【方法】膝伸展・30度屈曲位で内反ストレスを加える。【陽性】外側裂隙の開大や疼痛（LCL損傷）。",
    "McMurray": "【方法】膝最大屈曲から回旋ストレスを加え伸展。【陽性】クリック音や疼痛（半月板損傷）。",
    "Apley": "【方法】腹臥位膝90度屈曲で下腿を押し込みながら回旋。【陽性】膝関節痛の誘発（半月板損傷）。",
    "膝蓋跳動": "【方法】膝蓋上嚢から液を絞り込み膝蓋骨を押し込む。【陽性】膝蓋骨が大腿骨に当たる（関節内水腫）。",
    "Grindテスト": "【方法】膝伸展位で膝蓋骨を押し付け大腿四頭筋を収縮。【陽性】膝蓋大腿関節の疼痛。",
    "Apprehension": "【方法】膝軽度屈曲位で膝蓋骨を外側に押す。【陽性】脱臼への不安感や防御性収縮（膝蓋骨脱臼）。",
    "Wilsonテスト": "【方法】座位で下腿を内旋のまま自動伸展。【陽性】30度で疼痛が生じ外旋で消失（離断性骨軟骨炎）。",
    # 足関節
    "前方引き出し(ATFL)": "【方法】踵部を前方に引き出す。【陽性】距骨の前方移動量の増大（前距腓靭帯損傷）。",
    "内反ストレス(CFL)": "【方法】足関節底屈・中間位で内反ストレス。【陽性】外側靭帯部の疼痛や動揺性。",
    "外反ストレス(三角靭帯)": "【方法】足関節に外反ストレスを加える。【陽性】内側の疼痛や動揺性（三角靭帯損傷）。",
    "トンプソンテスト": "【方法】腹臥位で下腿三頭筋の筋腹をつまむ。【陽性】足関節の底屈が起こらない（アキレス腱断裂）。",
    "スクイーズ(脛腓)": "【方法】下腿中央部で脛骨と腓骨を両側から圧迫。【陽性】遠位脛腓関節部の疼痛（脛腓靭帯結合損傷）。",
    "衝突試験": "【方法】足関節を最大背屈または最大底屈させる。【陽性】関節前部または後部の疼痛（インピンジメント）。",
    "Tinelサイン(足根管)": "【方法】内果の後下方（足根管部）を叩打。【陽性】足底への放散痛やしびれ（足根管症候群）。",
    "モートンテスト": "【方法】足趾のMP関節を横方向から強く圧迫。【陽性】趾間などに激痛やしびれ（モートン病）。"
}

FLEXIBILITY_TEST_HELP = {
    "FFD": "【方法】立位・両膝伸展位で体幹を前屈し、中指の先端と床の距離を測定する。【意義】体幹後面およびハムストリングスの柔軟性を評価。",
    "Thomasテスト": "【方法】背臥位で健側の股・膝を胸に付くよう最大屈曲させる。【陽性】患側の大腿が床から浮き上がる（腸腰筋の短縮）。",
    "Elyテスト": "【方法】腹臥位で他動的に膝を屈曲させる。【陽性】同側の骨盤が浮き上がり、股関節が屈曲する（大腿直筋の短縮）。",
    "90-90膝伸展テスト": "【方法】背臥位で股・膝90度屈曲位から膝を他動伸展。【陽性】完全伸展できず20度以上の制限がある（ハムストリングスの短縮）。",
    "SLR": "【方法】背臥位で膝を伸展したまま下肢を他動挙上する。【意義】ハムストリングスの短縮度合い、または神経根症状の有無を評価。"
}

st.title("🦴 Yudai式：AI理学療法アシスタント")

# --- サイドバー ---
with st.sidebar:
    if st.button("🗑️ 入力データをリセット", use_container_width=True):
        st.session_state.clear()
        st.rerun()
        
    st.header("🔑 AI設定")
    gemini_key = st.text_input("Gemini APIキーを入力", type="password")
    
    MODEL_OPTIONS = {
        "gemini-3-flash-preview（最新鋭・プレビュー版）": "gemini-3-flash-preview",
        "gemini-2.5-flash（安定の高性能モデル）": "gemini-2.5-flash"
    }
    
    st.divider()
    st.header("🧠 モデル設定")
    selected_label = st.selectbox("使用するAIモデル", list(MODEL_OPTIONS.keys()), index=0)
    selected_model = MODEL_OPTIONS[selected_label]
    
    st.caption(f"現在の接続先: {selected_model}")
            
    st.divider()
    st.header("📋 基本設定")
    patient_id = st.text_input("患者ID", "000000")
    joint = st.selectbox("評価する部位を選択", list(JOINT_CONFIG.keys()))
    diagnosis = st.text_input("病名を入力", "腰椎椎間板ヘルニア")
    
    onset_date = st.date_input("発症日", datetime.date.today())
    rehab_start_date = st.date_input("リハ開始日", datetime.date.today())
    
    if joint in ["頸部"]:
        side = "両側"
        sides_to_eval = ["右", "左", "正中"]
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
c_nrs1, c_nrs2, c_nrs3, _ = st.columns([1, 1, 1, 3])

# 💡【修正】この1行を復活させました！
nrs_options = list(range(11))

with c_nrs1: nrs_rest = st.selectbox("安静時NRS", nrs_options, index=0)
with c_nrs2: nrs_night = st.selectbox("夜間時NRS", nrs_options, index=0)
with c_nrs3: nrs_move = st.selectbox("動作時NRS", nrs_options, index=0)

pain_notes = st.text_area("疼痛に関する特記事項（部位、性質、放散痛など）", height=80, placeholder="例：右L5領域から下腿外側にかけての放散痛あり。")

st.divider()

rom_results = {s: {} for s in sides_to_eval}
rom_pain_results = {s: {} for s in sides_to_eval}
endfeel_results = {s: {} for s in sides_to_eval}
mmt_results = {s: {} for s in sides_to_eval}
sensory_results = {s: {} for s in sides_to_eval}
special_results = {s: {} for s in sides_to_eval}
check_results = {s: {} for s in sides_to_eval}

needs_ef = joint not in ["頸部", "腰部"]
EF_OPTIONS = ["骨", "靭帯", "筋", "軟部組織"]

# ROM入力
st.subheader("📐 関節可動域 (ROM)")
for item, ref in JOINT_CONFIG[joint]["rom"].items():
    is_median_item = (joint == "腰部" and item in ["屈曲", "伸展", "右側屈", "左側屈", "右回旋", "左回旋"]) or joint == "頸部"
    
    if is_median_item:
        if needs_ef:
            c_val, c_pain, c_ef, _ = st.columns([1.5, 0.8, 2.5, 3])
            with c_val: rom_results["正中"][item] = st.number_input(f"【正中】{item}", value=None, step=1, format="%d", placeholder=str(ref), key=f"c_{item}")
            with c_pain:
                st.markdown("<div style='margin-top: 32px;'></div>", unsafe_allow_html=True)
                rom_pain_results["正中"][item] = st.checkbox("疼痛あり", key=f"cpain_{item}")
            with c_ef:
                st.markdown("<div style='margin-top: 32px;'></div>", unsafe_allow_html=True)
                endfeel_results["正中"][item] = st.multiselect("End-Feel", EF_OPTIONS, key=f"ef_c_{item}", label_visibility="collapsed", placeholder="EFを選択")
        else:
            c_val, c_pain, _ = st.columns([1.5, 0.8, 5.7])
            with c_val: rom_results["正中"][item] = st.number_input(f"【正中】{item}", value=None, step=1, format="%d", placeholder=str(ref), key=f"c_{item}")
            with c_pain:
                st.markdown("<div style='margin-top: 32px;'></div>", unsafe_allow_html=True)
                rom_pain_results["正中"][item] = st.checkbox("疼痛あり", key=f"cpain_{item}")
    elif side == "両側":
        if needs_ef:
            cr_val, cr_pain, cr_ef, cl_val, cl_pain, cl_ef, _ = st.columns([1.5, 0.8, 2.5, 1.5, 0.8, 2.5, 1])
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
            with cr_ef:
                st.markdown("<div style='margin-top: 32px;'></div>", unsafe_allow_html=True)
                endfeel_results["右"][item] = st.multiselect("EF", EF_OPTIONS, key=f"ef_r_{item}", label_visibility="collapsed", placeholder="右EF")
            with cl_ef:
                st.markdown("<div style='margin-top: 32px;'></div>", unsafe_allow_html=True)
                endfeel_results["左"][item] = st.multiselect("EF", EF_OPTIONS, key=f"ef_l_{item}", label_visibility="collapsed", placeholder="左EF")
        else:
            cr_val, cr_pain, cl_val, cl_pain, _ = st.columns([1.5, 0.8, 1.5, 0.8, 3.4])
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

# 筋柔軟性テスト
thomas_r = thomas_l = ely_r = ely_l = k_ext_r = k_ext_l = False
slr_ang_r = slr_ang_l = ffd_val = None

if joint == "腰部":
    st.subheader("🧘 筋柔軟性テスト")
    c_ffd, _ = st.columns([1, 3])
    with c_ffd:
        ffd_val = st.number_input("FFD (cm)", value=None, step=0.1, format="%.1f", placeholder="0.0", key="ffd_val", help=FLEXIBILITY_TEST_HELP["FFD"])
    
    col_flex_r, col_flex_l, _ = st.columns([1, 1, 1])
    with col_flex_r:
        st.write("『右』")
        thomas_r = st.checkbox("Thomasテスト (右)", key="thomas_r", help=FLEXIBILITY_TEST_HELP["Thomasテスト"])
        ely_r = st.checkbox("Elyテスト (右)", key="ely_r", help=FLEXIBILITY_TEST_HELP["Elyテスト"])
        k_ext_r = st.checkbox("90-90膝伸展テスト (右)", key="k_ext_r", help=FLEXIBILITY_TEST_HELP["90-90膝伸展テスト"])
        slr_ang_r = st.number_input("SLR角度 (右)", value=None, step=1, format="%d", placeholder="70", key="slr_ang_r", help=FLEXIBILITY_TEST_HELP["SLR"])
    with col_flex_l:
        st.write("『左』")
        thomas_l = st.checkbox("Thomasテスト (左)", key="thomas_l", help=FLEXIBILITY_TEST_HELP["Thomasテスト"])
        ely_l = st.checkbox("Elyテスト (左)", key="ely_l", help=FLEXIBILITY_TEST_HELP["Elyテスト"])
        k_ext_l = st.checkbox("90-90膝伸展テスト (左)", key="k_ext_l", help=FLEXIBILITY_TEST_HELP["90-90膝伸展テスト"])
        slr_ang_l = st.number_input("SLR角度 (左)", value=None, step=1, format="%d", placeholder="70", key="slr_ang_l", help=FLEXIBILITY_TEST_HELP["SLR"])
    st.divider()

# MMT入力
st.subheader("💪 徒手筋力テスト (MMT)")
mmt_opts = ["0", "1", "2", "3-", "3", "3+", "4", "5"]
for item in JOINT_CONFIG[joint]["mmt"]:
    is_median_item = (joint == "腰部" and item in ["体幹屈筋群", "体幹伸筋群", "腹斜筋群"]) or (joint == "頸部" and item == "頚部伸筋群")
    
    if is_median_item:
        c1, _ = st.columns([1, 3])
        with c1:
            mmt_results["正中"][item] = st.selectbox(f"【正中】{item}", mmt_opts, index=None, key=f"mc_{item}")
    elif side == "両側":
        c1, c2, _ = st.columns([1, 1, 2])
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
if side == "両側" and joint != "頸部":
    c_sp_r, c_sp_l = st.columns(2)
    with c_sp_r:
        st.write("『右』")
        for test in JOINT_CONFIG[joint]["special"]:
            help_text = SPECIAL_TEST_HELP.get(test, "")
            special_results["右"][test] = st.checkbox(f"【右】{test}", key=f"sp_右_{test}", help=help_text)
    with c_sp_l:
        st.write("『左』")
        for test in JOINT_CONFIG[joint]["special"]:
            help_text = SPECIAL_TEST_HELP.get(test, "")
            special_results["左"][test] = st.checkbox(f"【左】{test}", key=f"sp_左_{test}", help=help_text)
else:
    c_sp = st.columns(3)
    for i, test in enumerate(JOINT_CONFIG[joint]["special"]):
        with c_sp[i % 3]:
            help_text = SPECIAL_TEST_HELP.get(test, "")
            special_results["正中"][test] = st.checkbox(f"{test}", key=f"sp_正中_{test}", help=help_text)
st.divider()

# --- 動作観察 ---
motion_kito = False
m_slr_pronation_r = m_slr_post_r = m_slr_toe_r = m_slr_arch_r = False
m_slr_pronation_l = m_slr_post_l = m_slr_toe_l = m_slr_arch_l = False
motion_walking = ""
if joint in ["腰部", "股関節", "膝関節", "足関節"]:
    st.subheader("👀 動作観察 (立ち上がり・片脚立位・歩行)")
    c_m1, c_m2, c_m3 = st.columns(3)
    with c_m1:
        st.write("『立ち上がり』")
        motion_kito = st.checkbox("Knee-in Toe-out (KITO)")
    with c_m2:
        st.write("『片脚立位・右』")
        m_slr_pronation_r = st.checkbox("足部回内", key="m_slr_pronation_r")
        m_slr_post_r = st.checkbox("後方重心", key="m_slr_post_r")
        m_slr_toe_r = st.checkbox("足趾への荷重不足", key="m_slr_toe_r")
        m_slr_arch_r = st.checkbox("内側アーチの低下", key="m_slr_arch_r")
    with c_m3:
        st.write("『片脚立位・左』")
        m_slr_pronation_l = st.checkbox("足部回内", key="m_slr_pronation_l")
        m_slr_post_l = st.checkbox("後方重心", key="m_slr_post_l")
        m_slr_toe_l = st.checkbox("足趾への荷重不足", key="m_slr_toe_l")
        m_slr_arch_l = st.checkbox("内側アーチの低下", key="m_slr_arch_l")
    motion_walking = st.text_area("『歩行』に関する観察・特記事項", height=80, placeholder="例：歩行時に股関節伸展代償としての腰椎前弯増強が見られる。")
    st.divider()

# --- ADL評価・観察項目 ---
st.subheader("🚶 ADL評価・観察項目")
if side == "両側" and joint not in ["腰部", "頸部"]:
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

# 他部門からの情報
st.subheader("🏥 他部門からの情報")
other_dept_info = st.text_area("医師や看護師など他部門からの共有事項", height=80, placeholder="例：医師より、右下肢の荷重は1/2PWBの指示あり。看護師より、夜間に不眠の訴えあり。")

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

        pain_str = f"安静時{nrs_rest}, 夜間時{nrs_night}, 動作時{nrs_move}"
        if pain_notes: pain_str += f"（特記：{pain_notes}）"

        def fmt_val(v): return str(int(v)) if isinstance(v, (int, float)) else str(v)

        rom_list = []
        for item in JOINT_CONFIG[joint]["rom"]:
            ref = JOINT_CONFIG[joint]["rom"][item]
            for s in sides_to_eval:
                val = rom_results[s].get(item)
                if val is not None:
                    if isinstance(val, (int, float)) and isinstance(ref, (int, float)):
                        if abs(val - ref) < 5:
                            continue
                    p = "（疼痛あり）" if rom_pain_results[s].get(item) else ""
                    ef_str = ""
                    if needs_ef and endfeel_results[s].get(item):
                        ef_str = f"[{'・'.join(endfeel_results[s][item])}]"
                    rom_list.append(f"{item}({s}{fmt_val(val)}{p}{ef_str})")
        
        mmt_list = []
        for item in JOINT_CONFIG[joint]["mmt"]:
            for s in sides_to_eval:
                val = mmt_results[s].get(item)
                if val is not None and val != "5":
                    mmt_list.append(f"{item}({s}{val})")
                    
        special_pos = [f"{k}" if s == "正中" else f"{k}({s})" for s in sides_to_eval for k, v in special_results[s].items() if v]
        check_pos = [f"{k}" if s == "正中" else f"{k}({s})" for s in sides_to_eval for k, v in check_results[s].items() if v]
        adl_str = "、".join(check_pos) if check_pos else "特記なし"
        if adl_notes: adl_str += f" / 特記：{adl_notes}"

        motion_prompt_line = ""
        if joint in ["腰部", "股関節", "膝関節", "足関節"]:
            m_parts = []
            if motion_kito: m_parts.append("立ち上がり:KITO")
            slr_issues_r = [txt for cond, txt in zip([m_slr_pronation_r, m_slr_post_r, m_slr_toe_r, m_slr_arch_r], ["足部回内", "後方重心", "足趾荷重不足", "内側アーチ低下"]) if cond]
            slr_issues_l = [txt for cond, txt in zip([m_slr_pronation_l, m_slr_post_l, m_slr_toe_l, m_slr_arch_l], ["足部回内", "後方重心", "足趾荷重不足", "内側アーチ低下"]) if cond]
            if slr_issues_r: m_parts.append("片脚立位(右):" + "、".join(slr_issues_r))
            if slr_issues_l: m_parts.append("片脚立位(左):" + "、".join(slr_issues_l))
            if motion_walking: m_parts.append(f"歩行:{motion_walking}")
            if m_parts: motion_prompt_line = f"\n・動作観察：{'、'.join(m_parts)}"

        flexibility_str = ""
        if joint == "腰部":
            flex_items = []
            if ffd_val is not None: flex_items.append(f"FFD({ffd_val}cm)")
            if thomas_r: flex_items.append("Thomasテスト(右陽性)")
            if thomas_l: flex_items.append("Thomasテスト(左陽性)")
            if ely_r: flex_items.append("Elyテスト(右陽性)")
            if ely_l: flex_items.append("Elyテスト(左陽性)")
            if k_ext_r: flex_items.append("90-90膝伸展テスト(右陽性)")
            if k_ext_l: flex_items.append("90-90膝伸展テスト(左陽性)")
            if slr_ang_r is not None: flex_items.append(f"SLR(右{slr_ang_r}°)")
            if slr_ang_l is not None: flex_items.append(f"SLR(左{slr_ang_l}°)")
            flexibility_str = "、".join(flex_items) if flex_items else "特記なし"

        common_data = f"""
【データ】
・病名：{diagnosis} / 部位：{joint}
・他部門からの情報：{other_dept_info if other_dept_info else "特記なし"}
・疼痛：{pain_str}
・ROM（制限あり）：{"、".join(rom_list) if rom_list else "特記なし"}{motion_prompt_line}
"""
        if joint == "腰部":
            common_data += f"・筋柔軟性テスト：{flexibility_str}\n"

        common_data += f"""・MMT（4以下）：{"、".join(mmt_list) if mmt_list else "特記なし"}
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
今回は「計画書の更新」です。以下の【９項目】のみを出力してください。挨拶や前置きは不要です。文章中での強調記号（カッコやアスタリスク等）は一切使用しないでください（指定した項目名のみ【】を使用可）。
・【疼痛について】（20文字以内。変化の経過を踏まえて記載）
・【筋力について】（20文字以内。変化の経過を踏まえて記載）
・【感覚異常について】（20文字以内。変化の経過を踏まえて記載）
・【可動域について】（20文字以内。変化の経過を踏まえ、疼痛を伴う制限がある場合はその旨を記載）
・【短期目標】（100文字以内。変化の経過を踏まえて記載）
・【長期目標】（50文字以内。変化の経過を踏まえて記載）
・【治療方針】（120文字以内。変化の経過とPT考察を踏まえて記載）
・【参加制限に対する具体的な対応方針】（200文字以内、簡潔な「です・ます調」。適宜改行を入れること。ただし、空行（空白の行）は絶対に作らず、行を詰めて出力すること）
・【機能障害に対する具体的な対応方針】（200文字以内、簡潔な「です・ます調」。適宜改行を入れること。ただし、空行（空白の行）は絶対に作らず、行を詰めて出力すること）
"""
        else:
            prompt = f"""
あなたは19年の経験を持つベテラン理学療法士です。以下のデータを元に電子カルテと計画書を作成してください。
{common_data}
【条件】
以下の構成と文字数制限を必ず遵守して出力してください。挨拶や前置きは不要です。いきなり【電子カルテ用】から出力してください。文章中での強調記号（カッコやアスタリスク等）は一切使用しないでください（指定した項目名のみ【】を使用可）。
【電子カルテ用】
・実施した評価結果を、項目ごとに改行や箇条書きを用いて視覚的にスッキリとしたレイアウトで記載。
・優先順位が高い問題点を３つ、改行して箇条書きで挙げます（改善が見込める、かつPT考察から導き出される視点から判断。1項目につき30文字程度で簡潔に）。
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
・【治療内容】（必要な治療プログラムを「①」「②」のような番号付き箇条書きで列挙、最大6行）
・【参加制限に対する具体的な対応方針】（200文字以内、簡潔な「です・ます調」。適宜改行を入れること。ただし、空行（空白の行）は絶対に作らず、行を詰めて出力すること）
・【機能障害に対する具体的な対応方針】（200文字以内、簡潔な「です・ます調」。適宜改行を入れること。ただし、空行（空白の行）は絶対に作らず、行を詰めて出力すること）
"""
        try:
            with st.spinner(f"Gemini（{selected_label}）がカルテ・計画書を作成中です..."):
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel(selected_model)
                response = model.generate_content(prompt)
            st.subheader("✨ 出力結果")
            st.text_area("Copy & Paste", response.text, height=600)
        except Exception as e:
            st.error(f"エラー: {e}")
