import base64
import hashlib
import json
import math
import re


ROM_REFERENCE_VALUES = {
    "頸部": {
        "屈曲": 60,
        "伸展": 50,
        "右側屈": 50,
        "左側屈": 50,
        "右回旋": 60,
        "左回旋": 60,
        "CV角": None,
    },
    "腰部": {
        "屈曲": 45,
        "伸展": 30,
        "右側屈": 50,
        "左側屈": 50,
        "右回旋": 40,
        "左回旋": 40,
        "股関節屈曲": 125,
        "股関節伸展": 15,
        "股関節外転": 45,
        "股関節内転": 20,
        "股関節外旋": 45,
        "股関節内旋": 45,
        "膝関節屈曲": 130,
        "膝関節伸展": 0,
        "足関節背屈": 20,
        "足関節底屈": 45,
    },
    "肩関節": {
        "屈曲": 180,
        "伸展": 50,
        "外転": 180,
        "内転": 0,
        "外旋(1st)": 60,
        "外旋(2nd)": 90,
        "外旋(3rd)": None,
        "内旋(結帯)": None,
    },
    "肘関節": {
        "屈曲": 145,
        "伸展": 5,
        "回外": 90,
        "回内": 90,
        "外反": None,
    },
    "手関節": {
        "掌屈": 90,
        "背屈": 70,
        "橈屈": 25,
        "尺屈": 55,
        "母指橈側外転": 60,
        "母指掌側外転": 90,
        "母指対立": None,
    },
    "手指": {
        "MP屈曲": 90,
        "MP伸展": 45,
        "PIP屈曲": 100,
        "PIP伸展": 0,
        "DIP屈曲": 80,
        "DIP伸展": 0,
    },
    "股関節": {
        "屈曲": 125,
        "伸展": 15,
        "外転": 45,
        "内転": 20,
        "外旋": 45,
        "内旋": 45,
        "膝関節屈曲": 130,
        "膝関節伸展": 0,
        "足関節背屈": 20,
        "足関節底屈": 45,
        "SLR": None,
    },
    "膝関節": {
        "股関節屈曲": 125,
        "股関節伸展": 15,
        "股関節外転": 45,
        "股関節内転": 20,
        "股関節外旋": 45,
        "股関節内旋": 45,
        "屈曲": 130,
        "伸展": 0,
        "足関節背屈": 20,
        "足関節底屈": 45,
        "SLR": None,
    },
    "足関節": {
        "背屈": 20,
        "底屈": 45,
        "膝関節屈曲": 130,
        "膝関節伸展": 0,
        "SLR": None,
    },
}

# 関節可動域表示ならびに測定法（2022年4月改訂）の基本軸・移動軸。
# 参考可動域がない項目（CV角、外旋(3rd)、内旋(結帯)、外反、母指対立、SLR）は対象外。
_CERVICAL_FLEXION_AXES = ("肩峰を通る床への垂直線", "外耳孔と頭頂を結ぶ線")
_CERVICAL_LATERAL_FLEXION_AXES = (
    "第7頸椎棘突起と第1仙椎の棘突起を結ぶ線",
    "頭頂と第7頸椎棘突起を結ぶ線",
)
_CERVICAL_ROTATION_AXES = ("両側の肩峰を結ぶ線への垂直線", "鼻梁と後頭結節を結ぶ線")
_THORACOLUMBAR_FLEXION_AXES = ("仙骨後面", "第1胸椎棘突起と第5腰椎棘突起を結ぶ線")
_THORACOLUMBAR_LATERAL_FLEXION_AXES = (
    "ヤコビー線の中点に立てた垂直線",
    "第1胸椎棘突起と第5腰椎棘突起を結ぶ線",
)
_THORACOLUMBAR_ROTATION_AXES = ("両側の後上腸骨棘を結ぶ線", "両側の肩峰を結ぶ線")
_SHOULDER_ELEVATION_AXES = ("肩峰を通る床への垂直線", "上腕骨")
_SHOULDER_ROTATION_AXES = ("肘を通る前額面への垂直線", "尺骨")
_ELBOW_AXES = ("上腕骨", "橈骨")
_FOREARM_AXES = ("床への垂直線", "手指を伸展した手掌面")
_WRIST_FLEXION_AXES = ("橈骨", "第2中手骨")
_WRIST_DEVIATION_AXES = ("前腕の中央線", "第3中手骨")
_THUMB_ABDUCTION_AXES = ("示指（橈骨の延長上）", "母指")
_MP_AXES = ("第2-5中手骨", "第2-5基節骨")
_PIP_AXES = ("第2-5基節骨", "第2-5中節骨")
_DIP_AXES = ("第2-5中節骨", "第2-5末節骨")
_HIP_FLEXION_AXES = ("体幹と平行な線", "大腿骨（大転子と大腿骨外顆の中心を結ぶ線）")
_HIP_ABDUCTION_AXES = (
    "両側の上前腸骨棘を結ぶ線への垂直線",
    "大腿中央線（上前腸骨棘より膝蓋骨中心を結ぶ線）",
)
_HIP_ROTATION_AXES = (
    "膝蓋骨より下ろした垂直線",
    "下腿中央線（膝蓋骨中心より足関節内外果中央を結ぶ線）",
)
_KNEE_AXES = ("大腿骨", "腓骨（腓骨頭と外果を結ぶ線）")
_ANKLE_AXES = ("矢状面における腓骨長軸への垂直線", "足底面")

_HIP_AXES_BY_MOTION = {
    "屈曲": _HIP_FLEXION_AXES,
    "伸展": _HIP_FLEXION_AXES,
    "外転": _HIP_ABDUCTION_AXES,
    "内転": _HIP_ABDUCTION_AXES,
    "外旋": _HIP_ROTATION_AXES,
    "内旋": _HIP_ROTATION_AXES,
}
_LOWER_LIMB_ADDITIONAL_AXES = {
    "膝関節屈曲": _KNEE_AXES,
    "膝関節伸展": _KNEE_AXES,
    "足関節背屈": _ANKLE_AXES,
    "足関節底屈": _ANKLE_AXES,
}
_PREFIXED_HIP_AXES = {
    f"股関節{motion}": axes for motion, axes in _HIP_AXES_BY_MOTION.items()
}

ROM_MEASUREMENT_AXES = {
    "頸部": {
        "屈曲": _CERVICAL_FLEXION_AXES,
        "伸展": _CERVICAL_FLEXION_AXES,
        "右側屈": _CERVICAL_LATERAL_FLEXION_AXES,
        "左側屈": _CERVICAL_LATERAL_FLEXION_AXES,
        "右回旋": _CERVICAL_ROTATION_AXES,
        "左回旋": _CERVICAL_ROTATION_AXES,
    },
    "腰部": {
        "屈曲": _THORACOLUMBAR_FLEXION_AXES,
        "伸展": _THORACOLUMBAR_FLEXION_AXES,
        "右側屈": _THORACOLUMBAR_LATERAL_FLEXION_AXES,
        "左側屈": _THORACOLUMBAR_LATERAL_FLEXION_AXES,
        "右回旋": _THORACOLUMBAR_ROTATION_AXES,
        "左回旋": _THORACOLUMBAR_ROTATION_AXES,
        **_PREFIXED_HIP_AXES,
        **_LOWER_LIMB_ADDITIONAL_AXES,
    },
    "肩関節": {
        "屈曲": _SHOULDER_ELEVATION_AXES,
        "伸展": _SHOULDER_ELEVATION_AXES,
        "外転": _SHOULDER_ELEVATION_AXES,
        "内転": _SHOULDER_ELEVATION_AXES,
        "外旋(1st)": _SHOULDER_ROTATION_AXES,
        "外旋(2nd)": _SHOULDER_ROTATION_AXES,
    },
    "肘関節": {
        "屈曲": _ELBOW_AXES,
        "伸展": _ELBOW_AXES,
        "回外": _FOREARM_AXES,
        "回内": _FOREARM_AXES,
    },
    "手関節": {
        "掌屈": _WRIST_FLEXION_AXES,
        "背屈": _WRIST_FLEXION_AXES,
        "橈屈": _WRIST_DEVIATION_AXES,
        "尺屈": _WRIST_DEVIATION_AXES,
        "母指橈側外転": _THUMB_ABDUCTION_AXES,
        "母指掌側外転": _THUMB_ABDUCTION_AXES,
    },
    "手指": {
        "MP屈曲": _MP_AXES,
        "MP伸展": _MP_AXES,
        "PIP屈曲": _PIP_AXES,
        "PIP伸展": _PIP_AXES,
        "DIP屈曲": _DIP_AXES,
        "DIP伸展": _DIP_AXES,
    },
    "股関節": {**_HIP_AXES_BY_MOTION, **_LOWER_LIMB_ADDITIONAL_AXES},
    "膝関節": {
        **_PREFIXED_HIP_AXES,
        "屈曲": _KNEE_AXES,
        "伸展": _KNEE_AXES,
        "足関節背屈": _ANKLE_AXES,
        "足関節底屈": _ANKLE_AXES,
    },
    "足関節": {
        "背屈": _ANKLE_AXES,
        "底屈": _ANKLE_AXES,
        "膝関節屈曲": _KNEE_AXES,
        "膝関節伸展": _KNEE_AXES,
    },
}

MMT_MYOTOME_MAP = {
    "頚部伸筋群": "C2-C4",
    "僧帽筋上部": "C3-C4・副神経",
    "肩甲挙筋": "C3-C5",
    "前鋸筋": "C5-C7",
    "上腕二頭筋": "C5-C6、主にC5",
    "上腕三頭筋": "C6-C8、主にC7",
    "肩甲下筋": "C5-C6",
    "上腕筋": "C5-C6",
    "腕橈骨筋": "C5-C6、主にC6",
    "棘上筋": "C5-C6",
    "棘下筋": "C5-C6",
    "小円筋": "C5-C6",
    "三角筋(前・中・後)": "C5-C6",
    "僧帽筋(上・中・下)": "C3-C4・副神経",
    "円回内筋": "C6-C7",
    "方形回内筋": "C8-Th1",
    "回外筋": "C6-C7",
    "手関節伸筋": "C6-C8、主にC6",
    "手関節屈筋": "C6-Th1、主にC7",
    "骨間筋": "C8-Th1、主にTh1",
    "虫様筋": "C8-Th1",
    "体幹屈筋群": "Th7-L1",
    "体幹伸筋群": "Th1-L5、分節性",
    "腹斜筋群": "Th7-L1",
    "腸腰筋": "L1-L3、主にL2",
    "大殿筋": "L5-S2",
    "中殿筋": "L4-S1",
    "大腿筋膜張筋": "L4-S1",
    "ハムストリングス": "L5-S2",
    "大腿四頭筋": "L2-L4、主にL3",
    "前脛骨筋": "L4-L5、主にL4",
    "長腓骨筋": "L5-S1",
    "短腓骨筋": "L5-S1",
    "第三腓骨筋": "L5-S1",
    "下腿三頭筋": "S1-S2、主にS1",
    "足趾屈筋": "L5-S2",
    "足趾伸筋": "L5-S1、主にL5",
}

NECK_MMT_ITEMS = (
    "頚部伸筋群",
    "僧帽筋上部",
    "肩甲挙筋",
    "前鋸筋",
    "上腕二頭筋",
    "上腕三頭筋",
    "上腕筋",
    "腕橈骨筋",
    "手関節伸筋",
    "手関節屈筋",
)


PRIVACY_PATTERNS = {
    "電話番号": re.compile(
        r"(?<!\d)(?:\+81|0)[-\s]?\d{1,4}[-ー‐−\s]?\d{1,4}[-ー‐−\s]?\d{3,4}(?!\d)"
    ),
    "メールアドレス": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "生年月日の可能性がある日付": re.compile(
        r"(?:生年月日|誕生日|DOB|birth(?:day)?|バースデー)\s*(?:は|[:：])?\s*"
        r"(?:(?:19|20)\d{2}[年/.\-]\s*\d{1,2}[月/.\-]\s*\d{1,2}日?"
        r"|(?:明治|大正|昭和|平成|令和)\s*\d{1,2}年\s*\d{1,2}月\s*\d{1,2}日)",
        re.IGNORECASE,
    ),
    "住所の可能性がある表記": re.compile(
        r"(?:(?:東京都|北海道|(?:大阪|京都)府|[一-鿿]{2,3}県).{0,30}(?:市|区|郡|町|村)|丁目|番地)"
    ),
    "個人名の可能性がある表記": re.compile(
        r"(?:氏名|患者名|名前|お名前)\s*[:：]?\s*[一-鿿々ぁ-んァ-ヶー・　]{2,20}"
    ),
}

INITIAL_OUTPUT_REQUIREMENTS = {
    "評価結果": ("電子カルテ用", "評価結果"),
    "問題点": ("問題点", "優先順位"),
    "短期目標": ("短期目標",),
    "長期目標": ("長期目標",),
    "治療方針": ("治療方針",),
    "治療内容": ("治療内容",),
}

REEVALUATION_OUTPUT_REQUIREMENTS = {
    "先月から今月の変化": ("疼痛について", "筋力について", "感覚異常について", "可動域について"),
    "現在の問題点": ("参加制限", "機能障害"),
    "今後の方針": ("治療方針", "対応方針"),
    "目標": ("短期目標", "長期目標"),
    "治療内容": ("治療内容", "治療方針", "対応方針"),
    "優先的問題点": ("優先的問題点", "優先順位の高い問題点", "主要問題点"),
    "実施プログラム": ("実施プログラム", "実施内容", "治療プログラム"),
}

PRIORITY_PROBLEM_HEADINGS = ("優先的問題点", "優先順位の高い問題点", "主要問題点")
PRIORITY_PROBLEM_ITEM_PATTERN = re.compile(
    r"^\s*(?:[＃#][1-9１-９]|[1-9１-９][\.．、\)]|[①②③④⑤⑥⑦⑧⑨]|・)\s*\S+",
    re.MULTILINE,
)
FULLWIDTH_PRIORITY_PROBLEM_ITEM_PATTERN = re.compile(
    r"^\s*＃([1-9１-９])\s*\S+",
    re.MULTILINE,
)
PROGRAM_HEADINGS = ("実施プログラム", "実施内容", "治療プログラム")
PROGRAM_ITEM_PATTERN = re.compile(
    r"^\s*(?:・|-|\*|[1-9１-９][\.．、\)]|[①②③④⑤⑥⑦⑧⑨])\s*\S+",
    re.MULTILINE,
)

PLAN_TRANSLATION_LANGUAGES = {
    "翻訳なし": None,
    "英語": "English",
    "中国語（簡体字）": "Simplified Chinese",
    "韓国語": "Korean",
    "ベトナム語": "Vietnamese",
    "ネパール語": "Nepali",
    "スペイン語": "Spanish",
}

REHABILITATION_PLAN_HEADINGS = (
    "リハビリテーション実施計画書案",
    "リハビリテーション計画書案",
    "リハビリ実施計画書案",
    "計画書案",
    "計画書用",
)
REHABILITATION_PLAN_CONTENT_HEADINGS = {
    "疼痛について",
    "筋力について",
    "感覚異常について",
    "可動域について",
    "優先的問題点",
    "優先順位の高い問題点",
    "主要問題点",
    "短期目標",
    "長期目標",
    "治療方針",
    "治療内容",
    "実施プログラム",
    "実施内容",
    "治療プログラム",
    "参加制限に対する具体的な対応方針",
    "機能障害に対する具体的な対応方針",
}
BRACKETED_HEADING_PATTERN = re.compile(r"^[ \t]*【\s*([^】\r\n]+?)\s*】", re.MULTILINE)
UNINDENTED_OUTPUT_HEADING_PATTERN = re.compile(
    r"^[ \t]*(?:【[^】\r\n]+】|[^\s　：:\r\n][^：:\r\n]*[：:])[ \t]*$",
    re.MULTILINE,
)
BULLET_LINE_PATTERN = re.compile(
    r"^(?:・\s*|[-*]\s+|[0-9０-９]+[.．、\)](?![0-9０-９])\s*|[①-⑳]\s*)\S"
)
DEPRECATED_REASONING_HEADINGS = ("補足評価結果", "PT推論", "臨床推論")

OUTPUT_MIN_LENGTH = 300
OUTPUT_MAX_LENGTH = 5000
PHYSICAL_THERAPY_EVALUATION_MIN_LENGTH = 150
PHYSICAL_THERAPY_EVALUATION_MAX_LENGTH = 250
LAXITY_MAX_SCORE = 7.0
LOWER_LIMB_BALANCE_JOINTS = {"股関節", "膝関節", "足関節"}
TUG_REFERENCE_CUTOFF_SECONDS = 13.5
SINGLE_LEG_STANCE_REFERENCE_SECONDS = 5.0
SEBT_COMPOSITE_REFERENCE_PERCENT = 94.0
SEBT_ANTERIOR_ASYMMETRY_REFERENCE_CM = 4.0
ROM_REFERENCE_DIFFERENCE_THRESHOLD = 5
ROM_SIDE_DIFFERENCE_THRESHOLD = 5


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def should_include_rom_value(
    value,
    reference,
    *,
    has_pain=False,
    has_end_feel=False,
    contralateral_value=None,
):
    """Decide whether a measured ROM value is sent to the AI prompt.

    Values close to the reference are omitted only when there is no pain,
    no End-Feel entry and no side-to-side difference, so that reference
    values alone are not used to discard clinically relevant findings.
    """
    if value is None:
        return False
    if not _is_number(value) or not _is_number(reference):
        return True
    if abs(value - reference) >= ROM_REFERENCE_DIFFERENCE_THRESHOLD:
        return True
    if has_pain or has_end_feel:
        return True
    if (
        _is_number(contralateral_value)
        and abs(value - contralateral_value) >= ROM_SIDE_DIFFERENCE_THRESHOLD
    ):
        return True
    return False


def build_privacy_review_key(text_fields):
    """Return a widget-key suffix that changes whenever any scanned text changes."""
    joined = "\u0000".join(
        f"{field_name}\u0001{value or ''}" for field_name, value in text_fields.items()
    )
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def detect_potential_personal_information(text_fields):
    findings = []
    for field_name, value in text_fields.items():
        text = str(value or "")
        for finding_name, pattern in PRIVACY_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{field_name}（{finding_name}）")
    return findings


def format_measurement_value(value):
    return str(int(value)) if isinstance(value, (int, float)) else str(value)


def format_rom_display_name(item, reference_value):
    if reference_value is None:
        return str(item)
    if isinstance(reference_value, (int, float)) and float(reference_value).is_integer():
        formatted_reference = str(int(reference_value))
    else:
        formatted_reference = str(reference_value)
    return f"{item}（{formatted_reference}°）"


def format_rom_measurement_help(reference_value, axes):
    """Return tooltip text with the reference ROM and measurement axes."""
    lines = []
    if reference_value is not None:
        lines.append(f"参考可動域：{format_measurement_value(reference_value)}°")
    if axes:
        basic_axis, moving_axis = axes
        lines.append(f"基本軸：{basic_axis}")
        lines.append(f"移動軸：{moving_axis}")
    return "\n\n".join(lines) or None


def format_mmt_display_name(muscle_name, myotome_map=None):
    mapping = MMT_MYOTOME_MAP if myotome_map is None else myotome_map
    myotome = mapping.get(muscle_name)
    return f"{muscle_name}（{myotome}）" if myotome else str(muscle_name)


def format_grip_strength_items(right_strength, left_strength):
    items = []
    if right_strength is not None:
        items.append(f"右 {right_strength:.1f}kg")
    if left_strength is not None:
        items.append(f"左 {left_strength:.1f}kg")
    return items


def calculate_laxity_score(bilateral_results, single_results):
    """Calculate the seven-point generalized joint laxity score."""
    bilateral_score = sum(
        0.5
        for side_results in bilateral_results.values()
        for is_positive in side_results.values()
        if is_positive
    )
    single_score = sum(1.0 for is_positive in single_results.values() if is_positive)
    return min(bilateral_score + single_score, LAXITY_MAX_SCORE)


def _nonnegative_number_or_none(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        numeric_value = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(numeric_value) or numeric_value < 0:
        return None
    return numeric_value


def classify_tug_reference(seconds):
    seconds = _nonnegative_number_or_none(seconds)
    if seconds is None:
        return None
    if seconds < TUG_REFERENCE_CUTOFF_SECONDS:
        return f"参考カットオフ{TUG_REFERENCE_CUTOFF_SECONDS:.1f}秒未満"
    return f"参考カットオフ{TUG_REFERENCE_CUTOFF_SECONDS:.1f}秒以上、総合評価が必要"


def classify_single_leg_stance_reference(seconds):
    seconds = _nonnegative_number_or_none(seconds)
    if seconds is None:
        return None
    if seconds < SINGLE_LEG_STANCE_REFERENCE_SECONDS:
        return (
            f"参考値{SINGLE_LEG_STANCE_REFERENCE_SECONDS:g}秒未満、"
            "静的バランス低下の可能性"
        )
    return f"参考値{SINGLE_LEG_STANCE_REFERENCE_SECONDS:g}秒以上"


def calculate_sebt_composite_score(anterior, posteromedial, posterolateral, limb_length):
    values = [
        _nonnegative_number_or_none(value)
        for value in (anterior, posteromedial, posterolateral, limb_length)
    ]
    if any(value is None for value in values):
        return None
    anterior_value, posteromedial_value, posterolateral_value, limb_length_value = values
    if limb_length_value <= 0:
        return None
    score = (
        (anterior_value + posteromedial_value + posterolateral_value)
        / (limb_length_value * 3)
        * 100
    )
    return round(score, 1)


def calculate_sebt_anterior_asymmetry(right_anterior, left_anterior):
    right_value = _nonnegative_number_or_none(right_anterior)
    left_value = _nonnegative_number_or_none(left_anterior)
    if right_value is None or left_value is None:
        return None
    return round(abs(right_value - left_value), 1)


def classify_sebt_composite_reference(score):
    score = _nonnegative_number_or_none(score)
    if score is None:
        return None
    if score < SEBT_COMPOSITE_REFERENCE_PERCENT:
        return f"参考値{SEBT_COMPOSITE_REFERENCE_PERCENT:g}%未満"
    return f"参考値{SEBT_COMPOSITE_REFERENCE_PERCENT:g}%以上"


def classify_sebt_asymmetry_reference(asymmetry):
    asymmetry = _nonnegative_number_or_none(asymmetry)
    if asymmetry is None:
        return None
    if asymmetry <= SEBT_ANTERIOR_ASYMMETRY_REFERENCE_CM:
        return f"参考値{SEBT_ANTERIOR_ASYMMETRY_REFERENCE_CM:g}cm以下"
    return f"参考値{SEBT_ANTERIOR_ASYMMETRY_REFERENCE_CM:g}cm超"


def build_balance_assessment_lines(
    *,
    tug_seconds=None,
    tug_condition="",
    single_leg_right=None,
    single_leg_left=None,
    sebt_right_composite=None,
    sebt_left_composite=None,
    sebt_anterior_asymmetry=None,
    include_references=False,
):
    lines = []
    tug_value = _nonnegative_number_or_none(tug_seconds)
    if tug_value is not None:
        tug_line = f"TUG：{tug_value:.1f}秒"
        condition = str(tug_condition or "").strip()
        if condition:
            tug_line += f"、{condition}"
        if include_references:
            tug_line += f"（{classify_tug_reference(tug_value)}）"
        lines.append(tug_line)

    single_values = {
        "右": _nonnegative_number_or_none(single_leg_right),
        "左": _nonnegative_number_or_none(single_leg_left),
    }
    measured_single_values = {
        side: value for side, value in single_values.items() if value is not None
    }
    if measured_single_values:
        measurements = "、".join(
            f"{side}{value:.1f}秒" for side, value in measured_single_values.items()
        )
        single_line = f"片脚立位時間（開眼）：{measurements}"
        if include_references:
            if (
                len(measured_single_values) == 2
                and all(
                    value >= SINGLE_LEG_STANCE_REFERENCE_SECONDS
                    for value in measured_single_values.values()
                )
            ):
                single_line += (
                    f"（左右とも参考値{SINGLE_LEG_STANCE_REFERENCE_SECONDS:g}秒以上）"
                )
            else:
                references = "、".join(
                    f"{side}：{classify_single_leg_stance_reference(value)}"
                    for side, value in measured_single_values.items()
                )
                single_line += f"（{references}）"
        lines.append(single_line)

    composite_values = {
        "右": _nonnegative_number_or_none(sebt_right_composite),
        "左": _nonnegative_number_or_none(sebt_left_composite),
    }
    measured_composite_values = {
        side: value for side, value in composite_values.items() if value is not None
    }
    if measured_composite_values:
        measurements = "、".join(
            f"{side}{value:.1f}%" for side, value in measured_composite_values.items()
        )
        composite_line = f"SEBT Composite score：{measurements}"
        if include_references:
            references = "、".join(
                f"{side}：{classify_sebt_composite_reference(value)}"
                for side, value in measured_composite_values.items()
            )
            composite_line += f"（{references}）"
        lines.append(composite_line)

    asymmetry_value = _nonnegative_number_or_none(sebt_anterior_asymmetry)
    if asymmetry_value is not None:
        asymmetry_line = f"SEBT 前方到達左右差：{asymmetry_value:.1f}cm"
        if include_references:
            asymmetry_line += f"（{classify_sebt_asymmetry_reference(asymmetry_value)}）"
        lines.append(asymmetry_line)
    return lines


def summarize_items(items, limit=8):
    if not items:
        return "特記なし"
    summary = "、".join(items[:limit])
    if len(items) > limit:
        summary += f"、ほか{len(items) - limit}件"
    return summary


def summarize_free_text(value, limit=120):
    text = " ".join(str(value or "").split())
    if not text:
        return "特記なし"
    return text if len(text) <= limit else f"{text[:limit]}…"


def normalize_pt_free_text(value):
    return str(value or "").strip()


def build_pt_free_text_instruction(is_reevaluation=False):
    if is_reevaluation:
        return """【PT自由記載の取扱い】
・PT自由記載には、客観的所見、患者申告、PTが明示した解釈・原因仮説が混在する可能性があります。これらを内部的に区別して判断材料にしてください。
・「補足評価結果」「PT推論」「臨床推論」の独立見出しを追加せず、指定された11項目だけを出力してください。
・優先的問題点は必ず3項目とし、各行を全角の「＃1」「＃2」「＃3」で開始してください。
・PTが測定・観察・確認した内容と患者本人から聴取した内容を区別し、患者申告をPTの客観所見へ変換せず、PTの観察所見を患者申告として扱わないでください。
・PT自由記載が「入力なし」の場合は、入力されていない推論を作らないでください。
・原文より因果関係や確信度を強めず、推論を事実として断定しないでください。
・数値、単位、左右、身体部位、検査名を変更せず、入力されていない所見や診断名を追加しないでください。
・構造化入力とPT自由記載が矛盾する場合は、どちらかへ統合したり、片方を削除したりせず、矛盾を勝手に解決しないでください。
・【実施プログラム】には、計画書更新用カルテ内容に記載されていないプログラムを追加しないでください。"""

    return """【PT自由記載の統合と理学療法評価】
・PT自由記載にある客観所見と患者申告は、「補足評価結果」という独立項目を作らず、該当する既存の評価項目へ統合してください。
・疼痛・圧痛・疼痛誘発動作・疼痛の患者申告は「疼痛：」、追加ROM・筋短縮・End-Feel・FFD・SLR・Thomasテスト・Elyテストは「関節可動域：」、追加MMT・筋収縮・筋萎縮・握力・筋持久力は「筋力：」へ統合してください。
・しびれ・感覚鈍麻・反射・筋緊張・神経症状は「感覚：」などの神経学的項目、片脚立位・TUG・SEBT・姿勢制御・動揺は「バランス評価：」、追加検査と陽性・陰性結果は「スペシャルテスト：」へ統合してください。
・立脚期・歩幅・跛行・Trendelenburg徴候・Knee-in・立ち上がり・階段・代償動作は「動作観察：」、更衣・入浴・歩行・仕事・スポーツ・家事などの活動制限は「ADL：」へ統合してください。
・明確な既存分類がない客観所見だけを「その他評価：」へ記載し、安易に使用しないでください。
・構造化入力と自由記載の同じ所見は1つの項目内で自然な文章にまとめ、同じ所見を複数項目へ重複して記載しないでください。「補足評価」という名称を電子カルテへ残してはいけません。
・PT自由記載の箇条書きや短文メモは、記号をそのまま残さず、内容を変えない範囲で該当項目内の簡潔で自然な文章へ整えてください。
・患者本人から聴取した内容は「患者は〜と訴えた」「〜との申告あり」など情報源を保持し、患者申告をPTの観察所見へ変換せず、PTの観察所見を患者申告として扱わないでください。
・数値、単位、左右、身体部位、動作、検査名を変更せず、入力されていない所見・診断名・因果関係を追加しないでください。
・構造化入力と自由記載が矛盾する場合は勝手に統一せず、重要な場合は「入力内容間で所見の不一致あり」など事実だけを記載してください。
・「補足評価結果：」「PT推論：」「臨床推論：」の独立見出しは出力してはいけません。
・PT自由記載内の臨床推論は独立出力せず、疼痛、ROM、筋力、感覚、バランス、スペシャルテスト、姿勢・動作・歩行、ADL、患者申告と統合して、必ず「理学療法評価：」へ反映してください。
・理学療法評価は本文約200文字、原則150～250文字の1つの自然な段落とし、箇条書きや所見の単純な羅列にしないでください。情報が少ない場合は無理に水増しせず、得られた情報の範囲で簡潔に記載してください。
・重要な所見とADL・活動制限の関連を慎重に解釈し、「可能性がある」「影響していると考える」など非断定的に表現してください。原文より確信度を高めず、治療プログラムを細かく羅列しないでください。
・PT自由記載が入力なしでも、測定された構造化評価を統合した理学療法評価を作成してください。未測定内容を推測してはいけません。
・参考可動域は実測値ではなく、それだけで正常・異常を断定してはいけません。MMTに表示された髄節レベルを神経学的診断の確定根拠として扱ってはいけません。
・理学療法評価の後に「優先的問題点：」を置き、必ず3行を全角の「＃1」「＃2」「＃3」で開始してください。"""


def _find_colon_heading(text, heading):
    if not text:
        return None
    normalized_heading = str(heading or "").strip().rstrip("：:")
    if not normalized_heading:
        return None
    return re.search(
        rf"^[ \t]*{re.escape(normalized_heading)}[：:][ \t]*(?=\r?$)",
        str(text),
        re.MULTILINE,
    )


def extract_colon_heading_body(text, heading):
    """Extract an unindented colon-heading body, returning None when absent."""
    heading_match = _find_colon_heading(text, heading)
    if heading_match is None:
        return None

    remaining_text = str(text)[heading_match.end():]
    next_heading_match = UNINDENTED_OUTPUT_HEADING_PATTERN.search(remaining_text)
    if next_heading_match is not None:
        remaining_text = remaining_text[:next_heading_match.start()]
    return remaining_text.strip()


def contains_bullet_only_content(text):
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    return bool(lines) and all(BULLET_LINE_PATTERN.match(line) for line in lines)


def _find_rehabilitation_plan_start(response_text):
    for match in BRACKETED_HEADING_PATTERN.finditer(response_text or ""):
        if match.group(1).strip() in REHABILITATION_PLAN_HEADINGS:
            return match.start()
    return None


def validate_physical_therapy_evaluation(response_text):
    """Return structural warnings without judging clinical validity."""
    response_text = str(response_text or "")
    warnings = []
    heading_match = _find_colon_heading(response_text, "理学療法評価")
    body = extract_colon_heading_body(response_text, "理学療法評価")

    if heading_match is None:
        warnings.append("理学療法評価")
    else:
        plan_start = _find_rehabilitation_plan_start(response_text)
        if plan_start is not None and heading_match.start() > plan_start:
            warnings.append("理学療法評価（計画書部分より前）")
        if not body:
            warnings.append("理学療法評価（本文なし）")
        else:
            if contains_bullet_only_content(body):
                warnings.append("理学療法評価（文章形式）")
            body_length = len(re.sub(r"\s+", "", body))
            if not (
                PHYSICAL_THERAPY_EVALUATION_MIN_LENGTH
                <= body_length
                <= PHYSICAL_THERAPY_EVALUATION_MAX_LENGTH
            ):
                warnings.append("理学療法評価（150～250文字）")

    for heading in DEPRECATED_REASONING_HEADINGS:
        if re.search(
            rf"^[ \t]*{re.escape(heading)}[：:]",
            response_text,
            re.MULTILINE,
        ):
            warnings.append(f"{heading}（廃止見出し）")
    return warnings


def extract_rehabilitation_plan_section(response_text):
    """Return the unchanged rehabilitation-plan portion of a Japanese AI response."""
    if not response_text:
        return None

    heading_matches = list(BRACKETED_HEADING_PATTERN.finditer(response_text))
    start_match = next(
        (
            match
            for match in heading_matches
            if match.group(1).strip() in REHABILITATION_PLAN_HEADINGS
        ),
        None,
    )

    # Reevaluation responses currently contain only plan fields and begin with
    # 【疼痛について】, without a separate 【計画書用】 wrapper.
    if start_match is None:
        start_match = next(
            (
                match
                for match in heading_matches
                if match.group(1).strip() == "疼痛について"
            ),
            None,
        )
    if start_match is None:
        return None

    section_end = len(response_text)
    for match in heading_matches:
        if match.start() <= start_match.start():
            continue
        heading = match.group(1).strip()
        if heading not in REHABILITATION_PLAN_CONTENT_HEADINGS:
            section_end = match.start()
            break

    section = response_text[start_match.start():section_end]
    if not response_text[start_match.end():section_end].strip():
        return None
    return section


def build_plan_translation_prompt(plan_text, target_language):
    return f"""以下の区切り内にある日本語のリハビリテーション計画書だけを{target_language}へ翻訳してください。

【翻訳条件】
・医療内容を追加・削除・要約・推測しないでください。
・診断名、症状、左右、数値、単位、頻度、回数を変更しないでください。
・箇条書き、番号、見出し構造を可能な限り維持してください。
・固有名詞や医学用語は、医学的な意味が変わらないように翻訳してください。
・日本語原文にない注意事項、治療内容、評価結果を追加しないでください。
・翻訳文だけを返してください。説明や前置きは不要です。
・読みやすく自然な患者向け表現にしつつ、自然さより医学的意味の保持を優先してください。

<<<REHABILITATION_PLAN_START>>>
{plan_text}
<<<REHABILITATION_PLAN_END>>>"""


def is_plan_translation_usable(plan_text, translated_text):
    if not translated_text or not translated_text.strip():
        return False
    normalized_source = plan_text.strip()
    normalized_translation = translated_text.strip()
    if normalized_translation == normalized_source:
        return False
    return len(normalized_translation) >= 10


def extract_section_body(response_text, headings):
    heading_pattern = "|".join(re.escape(heading) for heading in headings)
    section_match = re.search(
        rf"(?:【\s*)?(?:{heading_pattern})(?:\s*】)?\s*(.*?)(?=\n\s*【|\Z)",
        response_text,
        re.DOTALL,
    )
    if section_match is None:
        return None
    return section_match.group(1)


def count_priority_problem_items(response_text):
    section_body = extract_section_body(response_text, PRIORITY_PROBLEM_HEADINGS)
    if section_body is None:
        return None
    return len(PRIORITY_PROBLEM_ITEM_PATTERN.findall(section_body))


def count_fullwidth_priority_problem_items(response_text):
    section_body = extract_section_body(response_text, PRIORITY_PROBLEM_HEADINGS)
    if section_body is None:
        return None
    return len(FULLWIDTH_PRIORITY_PROBLEM_ITEM_PATTERN.findall(section_body))


def has_fullwidth_priority_problem_sequence(response_text):
    section_body = extract_section_body(response_text, PRIORITY_PROBLEM_HEADINGS)
    if section_body is None:
        return False
    numbers = FULLWIDTH_PRIORITY_PROBLEM_ITEM_PATTERN.findall(section_body)
    normalized_numbers = [
        number.translate(str.maketrans("１２３４５６７８９", "123456789"))
        for number in numbers
    ]
    return normalized_numbers == ["1", "2", "3"]


def count_program_items(response_text):
    section_body = extract_section_body(response_text, PROGRAM_HEADINGS)
    if section_body is None:
        return None
    return len(PROGRAM_ITEM_PATTERN.findall(section_body))


def validate_ai_output(
    response_text,
    is_reevaluation,
    require_balance=False,
    has_pt_free_text=False,
):
    response_text = str(response_text or "")
    _ = has_pt_free_text  # Retained for backwards-compatible callers.
    requirements = REEVALUATION_OUTPUT_REQUIREMENTS if is_reevaluation else INITIAL_OUTPUT_REQUIREMENTS
    missing_items = [
        item_name
        for item_name, markers in requirements.items()
        if not any(marker in response_text for marker in markers)
    ]
    priority_problem_count = count_priority_problem_items(response_text)
    if priority_problem_count != 3:
        missing_items.append("優先的問題点（3項目）")
    else:
        if not has_fullwidth_priority_problem_sequence(response_text):
            missing_items.append("優先的問題点（＃1～＃3形式）")

    if is_reevaluation:
        program_count = count_program_items(response_text)
        if program_count is not None and program_count > 5:
            missing_items.append("実施プログラム（5行以内）")
    else:
        if require_balance and "バランス評価" not in response_text:
            missing_items.append("バランス評価")
        missing_items.extend(validate_physical_therapy_evaluation(response_text))
    output_length = len(response_text.strip())
    return missing_items, output_length < OUTPUT_MIN_LENGTH, output_length > OUTPUT_MAX_LENGTH


def classify_gemini_error(error):
    error_type = type(error).__name__.lower()
    error_message = str(error).lower()
    status_values = []
    for attribute_name in ("code", "status_code"):
        value = getattr(error, attribute_name, None)
        if callable(value):
            try:
                value = value()
            except Exception:
                value = None
        if value is not None:
            status_values.append(str(value).lower())
    signature = " ".join([error_type, error_message, *status_values])

    if any(
        marker in signature
        for marker in (
            "api key not valid",
            "api_key_invalid",
            "unauthenticated",
            "authentication",
            "permissiondenied",
            "permission denied",
            "401",
            "403",
        )
    ):
        return (
            "error",
            "Gemini APIの認証に失敗した可能性があります。"
            "APIキーが正しいか、無効化されていないかを確認してください。",
        )
    if any(marker in signature for marker in ("resourceexhausted", "rate limit", "quota", "429", "too many requests")):
        return (
            "warning",
            "Gemini APIの利用上限、レート制限、またはQuotaを超過した可能性があります。"
            "時間をおいて再試行し、利用状況を確認してください。",
        )
    if any(
        marker in signature
        for marker in ("deadlineexceeded", "timeout", "timed out", "connection", "network", "serviceunavailable", "unavailable", "503", "dns")
    ):
        return (
            "warning",
            "Gemini APIとの通信に失敗、またはタイムアウトした可能性があります。"
            "ネットワーク状態を確認し、しばらく後に再試行してください。",
        )
    if any(marker in signature for marker in ("notfound", "not found", "invalidargument", "badrequest", "404")):
        return (
            "error",
            "選択したGeminiモデル名またはリクエスト設定が無効であるか、"
            "このAPIキーで利用できない可能性があります。モデル設定を確認してください。",
        )
    return (
        "error",
        "Gemini APIの呼び出し中に予期しないエラーが発生しました。"
        "入力内容とモデル設定を確認し、しばらく後に再試行してください。",
    )


def response_may_be_blocked_by_safety(response):
    try:
        safety_values = []
        prompt_feedback = getattr(response, "prompt_feedback", None)
        if prompt_feedback is not None:
            safety_values.append(getattr(prompt_feedback, "block_reason", ""))
        for candidate in getattr(response, "candidates", None) or []:
            safety_values.append(getattr(candidate, "finish_reason", ""))
    except Exception:
        return False
    safety_summary = " ".join(str(value).upper() for value in safety_values)
    return any(marker in safety_summary for marker in ("SAFETY", "PROHIBITED", "BLOCKLIST", "RECITATION", "SPII"))


def build_output_file_name(joint, is_reevaluation, generated_at):
    """Return a download file name such as PTカルテ_20261026_200512_膝関節_初回評価.txt."""
    mode = "計画書更新" if is_reevaluation else "初回評価"
    safe_joint = re.sub(r'[\\/:*?"<>|\s]+', "_", str(joint or "部位未選択"))
    return f"PTカルテ_{generated_at:%Y%m%d_%H%M%S}_{safe_joint}_{mode}.txt"


def build_output_download_text(display_text, *, joint, is_reevaluation, generated_at):
    """Return the saved text with a short header; patient identifiers are not added."""
    mode = "計画書更新" if is_reevaluation else "初回評価"
    header = (
        "【AI生成の下書き】医療者が内容を確認・修正してから使用してください。\n"
        f"生成日時：{generated_at:%Y/%m/%d %H:%M:%S}（日本時間）\n"
        f"評価部位：{joint}\n"
        f"モード：{mode}\n"
        "----------------------------------------\n"
    )
    return header + str(display_text or "")


def build_auto_download_html(text, file_name):
    """Return a tiny HTML/JS snippet that saves text as a UTF-8 (BOM) file."""
    encoded_text = base64.b64encode(("\ufeff" + str(text)).encode("utf-8")).decode("ascii")
    return f"""<script>
(function () {{
  try {{
    const binary = atob({json.dumps(encoded_text)});
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    const blob = new Blob([bytes], {{ type: "text/plain;charset=utf-8" }});
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = {json.dumps(str(file_name))};
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(function () {{ URL.revokeObjectURL(url); }}, 10000);
  }} catch (error) {{
    console.error("auto download failed", error);
  }}
}})();
</script>"""
