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

OUTPUT_MIN_LENGTH = 300
OUTPUT_MAX_LENGTH = 5000
LAXITY_MAX_SCORE = 7.0


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


def validate_ai_output(response_text, is_reevaluation):
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
