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
}

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


def validate_ai_output(response_text, is_reevaluation):
    requirements = REEVALUATION_OUTPUT_REQUIREMENTS if is_reevaluation else INITIAL_OUTPUT_REQUIREMENTS
    missing_items = [
        item_name
        for item_name, markers in requirements.items()
        if not any(marker in response_text for marker in markers)
    ]
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
