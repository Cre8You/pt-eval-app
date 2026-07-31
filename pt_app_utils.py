import math
import re


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
    r"^\s*(?:[1-9１-９][\.．、\)]|[①②③④⑤⑥⑦⑧⑨])\s*\S+",
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
PT_FREE_TEXT_OUTPUT_HEADINGS = ("補足評価結果", "PT推論")

OUTPUT_MIN_LENGTH = 300
OUTPUT_MAX_LENGTH = 5000
LAXITY_MAX_SCORE = 7.0
LOWER_LIMB_BALANCE_JOINTS = {"股関節", "膝関節", "足関節"}
TUG_REFERENCE_CUTOFF_SECONDS = 13.5
SINGLE_LEG_STANCE_REFERENCE_SECONDS = 5.0
SEBT_COMPOSITE_REFERENCE_PERCENT = 94.0
SEBT_ANTERIOR_ASYMMETRY_REFERENCE_CM = 4.0


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
・PT自由記載には、客観的な補足評価結果と、PTが明示した解釈・原因仮説が混在する可能性があります。客観的事実と明示された推論を区別して判断材料にしてください。
・PTが測定・観察・確認した内容と患者本人から聴取した内容を区別し、患者申告をPTの客観所見へ変換せず、PTの観察所見を患者申告として扱わないでください。患者申告から新しい原因や解釈を作らないでください。
・PT自由記載が「入力なし」の場合は、入力されていない推論を作らないでください。
・原文より因果関係や確信度を強めず、推論を事実として断定しないでください。
・数値、単位、左右、身体部位、検査名を変更せず、入力されていない所見や診断名を追加しないでください。
・構造化入力とPT自由記載が矛盾する場合は、どちらかへ統合したり、片方を削除したりせず、矛盾を勝手に解決しないでください。
・計画書更新結果には「補足評価結果」と「PT推論」の新しい見出しを追加せず、指定された11項目だけを出力してください。
・【実施プログラム】には、計画書更新用カルテ内容に記載されていないプログラムを追加しないでください。"""

    return """【PT自由記載の分類・文章化】
・PT自由記載だけを、入力に明示されている範囲で「補足評価結果」と「PT推論」へ分類してください。
・補足評価結果には、PTが測定・観察・確認した事実、実施した検査結果、姿勢・動作・歩行所見、触診所見、疼痛の誘発動作、数値、左右差、および患者本人から聴取した内容を記載してください。
・PTが測定・観察・確認した内容は、測定所見・観察所見として「認めた」「確認した」などと記載してください。
・患者本人から聴取した内容は、「患者は〜と訴えた」「〜との申告あり」など、患者申告であることが分かる文章にしてください。患者申告を「認めた」「確認した」などのPTによる客観所見へ変換せず、PTが観察した所見を患者申告として記載しないでください。
・患者申告も入力されている内容だけを記載し、患者申告から新しい原因や解釈を作らないでください。患者申告に含まれる数値、単位、左右、身体部位、動作を変更してはいけません。
・PT推論には、評価結果の解釈、所見同士の関連性、疼痛や動作障害の原因仮説、代償動作の解釈、機能障害と活動制限のつながりなど、入力者が明示した解釈・仮説だけを記載してください。
・1つの文に事実と推論が混在する場合は、入力に明示されている範囲だけを分離してください。入力にない所見や因果関係を補ってはいけません。
・各本文は箇条書きにせず、「・」「-」「1.」「①」などの記号を除去し、短文や単語のメモを簡潔で自然な文章へ整えてください。
・推論は「可能性がある」「と考える」などの非断定的な表現にしてください。原文より因果関係や確信度を強めてはいけません。
・関係が不明な内容を無理につなげず、無関係な内容は別の文にしてください。文章を過度に膨らませてはいけません。
・数値、単位、左右、身体部位、検査名を変更せず、入力されていない所見・診断名・因果関係を追加しないでください。
・構造化入力とPT自由記載が矛盾する場合は、どちらかへ統合したり、片方を削除したりせず、矛盾を勝手に解決しないでください。
・既存の構造化評価と重複する内容を「補足評価結果」へ不必要に繰り返さないでください。
・PT自由記載が「入力なし」の場合は、「補足評価結果：」と「PT推論：」を出力せず、新しいPT推論を作らないでください。既存の理学療法評価、問題点、目標、治療方針は従来どおり作成してください。
・客観的内容だけの場合は「補足評価結果：」だけ、推論だけの場合は「PT推論：」だけ、両方ある場合は両方を出力してください。内容のない見出しや「特記なし」を出力してはいけません。
・新しい見出しは、既存の構造化評価項目と「理学療法評価：」の後、「優先的問題点：」の前、かつ「【計画書用】」より前に配置してください。
・新しい見出しも「項目名：」を単独行とし、本文の各行は全角スペース1つで字下げしてください。項目間に空行を入れないでください。
・患者申告の出力例：入力が「階段を降りるときに右膝が抜けそうになるとのこと」の場合は、「補足評価結果：」へ「　患者は、階段降段時に右膝が抜けそうになる感覚を訴えた。」と記載し、「階段降段時に右膝の不安定性を認めた。」という客観所見へ変換してはいけません。
・出力例：入力が「右立脚期が短く、股関節痛を避けていると思う」の場合は、「補足評価結果：」へ「　歩行では右立脚期の短縮を認めた。」、「PT推論：」へ「　右股関節痛を回避するため、右立脚時間が短縮している可能性がある。」と分けてください。"""


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


def validate_pt_free_text_output(response_text, has_pt_free_text):
    """Return structural warnings without judging clinical classification quality."""
    response_text = str(response_text or "")
    heading_details = {
        heading: (_find_colon_heading(response_text, heading), extract_colon_heading_body(response_text, heading))
        for heading in PT_FREE_TEXT_OUTPUT_HEADINGS
    }

    if not has_pt_free_text:
        return [
            f"{heading}（PT自由記載なし）"
            for heading, (heading_match, _) in heading_details.items()
            if heading_match is not None
        ]

    warnings = []
    present_headings = [
        heading
        for heading, (heading_match, _) in heading_details.items()
        if heading_match is not None
    ]
    if not present_headings:
        warnings.append("補足評価結果またはPT推論")
        return warnings

    plan_start = _find_rehabilitation_plan_start(response_text)
    for heading in present_headings:
        heading_match, body = heading_details[heading]
        if plan_start is not None and heading_match.start() > plan_start:
            warnings.append(f"{heading}（計画書部分より前）")
        if not body:
            warnings.append(f"{heading}（本文なし）")
        elif contains_bullet_only_content(body):
            warnings.append(f"{heading}（文章形式）")
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
    requirements = REEVALUATION_OUTPUT_REQUIREMENTS if is_reevaluation else INITIAL_OUTPUT_REQUIREMENTS
    missing_items = [
        item_name
        for item_name, markers in requirements.items()
        if not any(marker in response_text for marker in markers)
    ]
    if is_reevaluation:
        priority_problem_count = count_priority_problem_items(response_text)
        if priority_problem_count is not None and priority_problem_count != 3:
            missing_items.append("優先的問題点（3項目）")
        program_count = count_program_items(response_text)
        if program_count is not None and program_count > 5:
            missing_items.append("実施プログラム（5行以内）")
    elif require_balance and "バランス評価" not in response_text:
        missing_items.append("バランス評価")
    if not is_reevaluation:
        missing_items.extend(
            validate_pt_free_text_output(response_text, has_pt_free_text)
        )
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
