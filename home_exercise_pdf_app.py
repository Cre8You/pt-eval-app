from __future__ import annotations

import csv
import hashlib
import io
import re
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, quote, urlparse

import pandas as pd
import requests
import streamlit as st
from PIL import Image, UnidentifiedImageError
from reportlab.lib.pagesizes import A5, portrait
from reportlab.pdfgen import canvas


APP_TITLE = "ホームエクササイズ出力アプリ"
OUTPUT_FILENAME = "home_exercise_program.pdf"
APPROVED_STATUSES = {"採用", "採用候補"}
DISPLAY_COLUMNS = ["運動ID", "運動名", "対象部位", "カテゴリ", "回数", "注意点"]
HEADER_SCAN_ROWS = 10
MIN_HEADER_MATCHES = 3
CORE_HEADER_COLUMNS = {"運動ID", "運動名", "画像URL"}
HEADER_NOT_FOUND_MESSAGE = "運動ID、運動名、画像URLなどの見出し行が見つかりません。"
DEFAULT_SPREADSHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1LD1MsT7hk6xyii3ORzjECeLenaYmChi1rWQ8fVOWb54/edit?usp=drivesdk"
)
DEFAULT_SHEET_NAME = "運動DB"
DEFAULT_SHEET_GID = "1588738896"
DATABASE_SESSION_KEY = "exercise_database"
DATABASE_SOURCE_SESSION_KEY = "exercise_database_source"
DATABASE_PARAMS_SESSION_KEY = "exercise_database_params"
SELECTED_EXERCISE_IDS_SESSION_KEY = "selected_exercise_ids"
FOOT_BODY_PART = "足部・足趾"
BODY_PART_ORDER = ["頸部", "肩", "腰", "股関節", "膝", FOOT_BODY_PART]
BODY_PART_ORDER_INDEX = {body_part: index for index, body_part in enumerate(BODY_PART_ORDER)}
BODY_PART_ALIASES = {
    "首": "頸部",
    "頚部": "頸部",
    "足関節": FOOT_BODY_PART,
    "足指": FOOT_BODY_PART,
    "足趾": FOOT_BODY_PART,
    "足部": FOOT_BODY_PART,
    "足指・足部": FOOT_BODY_PART,
    "足趾・足部": FOOT_BODY_PART,
    FOOT_BODY_PART: FOOT_BODY_PART,
}
REQUIRED_COLUMNS = [
    "運動ID",
    "運動名",
    "対象部位",
    "カテゴリ",
    "対象疾患タグ",
    "荷重条件",
    "開始姿勢",
    "方法",
    "回数",
    "注意点",
    "中止基準",
    "画像ファイル名",
    "画像URL",
    "承認状態",
    "版数",
    "備考",
]


def text_value(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def normalize_body_part(value) -> str:
    body_part = text_value(value)
    return BODY_PART_ALIASES.get(body_part, body_part)


def normalize_exercise_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    normalized_df = df.copy()
    if "対象部位" in normalized_df.columns:
        normalized_df["対象部位"] = normalized_df["対象部位"].map(normalize_body_part)
    return normalized_df


def get_selected_exercise_ids() -> set[str]:
    selected_ids = st.session_state.get(SELECTED_EXERCISE_IDS_SESSION_KEY, set())
    if not isinstance(selected_ids, set):
        selected_ids = set(selected_ids)
    return {text_value(exercise_id) for exercise_id in selected_ids if text_value(exercise_id)}


def store_selected_exercise_ids(selected_ids: set[str]) -> None:
    st.session_state[SELECTED_EXERCISE_IDS_SESSION_KEY] = {
        text_value(exercise_id) for exercise_id in selected_ids if text_value(exercise_id)
    }


def selected_rows_from_ids(df: pd.DataFrame, selected_ids: set[str]) -> pd.DataFrame:
    if not selected_ids:
        return df.iloc[0:0].copy()
    return df[df["運動ID"].map(text_value).isin(selected_ids)].copy()


def prune_selected_exercise_ids(df: pd.DataFrame) -> None:
    valid_ids = {text_value(exercise_id) for exercise_id in df["運動ID"].dropna()}
    store_selected_exercise_ids(get_selected_exercise_ids().intersection(valid_ids))


def selection_table_key(display_df: pd.DataFrame) -> str:
    exercise_ids = "|".join(display_df["運動ID"].map(text_value).tolist())
    digest = hashlib.md5(exercise_ids.encode("utf-8")).hexdigest()
    return f"exercise_selection_table_{digest}"


def detect_header_row(raw_df: pd.DataFrame) -> int:
    best_index: int | None = None
    best_matches: set[str] = set()

    for row_index, row in raw_df.head(HEADER_SCAN_ROWS).iterrows():
        row_values = {text_value(value) for value in row.tolist()}
        matches = row_values.intersection(REQUIRED_COLUMNS)
        if len(matches) > len(best_matches):
            best_index = row_index
            best_matches = matches

    if (
        best_index is None
        or len(best_matches) < MIN_HEADER_MATCHES
        or not CORE_HEADER_COLUMNS.issubset(best_matches)
    ):
        raise ValueError(HEADER_NOT_FOUND_MESSAGE)

    return best_index


def apply_detected_header(raw_df: pd.DataFrame) -> pd.DataFrame:
    header_row_index = detect_header_row(raw_df)
    headers = [text_value(value) for value in raw_df.iloc[header_row_index].tolist()]
    data = raw_df.iloc[header_row_index + 1 :].copy()
    data.columns = headers
    data = data.loc[:, [bool(column) for column in data.columns]]
    data = data.dropna(how="all").reset_index(drop=True)
    return data


def read_csv_without_header(file_bytes: bytes) -> pd.DataFrame:
    last_error: Exception | None = None

    for encoding in ("utf-8-sig", "cp932"):
        try:
            decoded = file_bytes.decode(encoding)
            rows = list(csv.reader(io.StringIO(decoded)))
        except UnicodeDecodeError as exc:
            last_error = exc
            continue

        max_columns = max((len(row) for row in rows), default=0)
        padded_rows = [row + [""] * (max_columns - len(row)) for row in rows]
        return pd.DataFrame(padded_rows)

    if last_error:
        raise last_error
    return pd.DataFrame()


def read_exercise_database(uploaded_file) -> pd.DataFrame:
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        raw_df = pd.read_excel(uploaded_file, header=None)
        return apply_detected_header(raw_df)
    if suffix == ".csv":
        file_bytes = uploaded_file.getvalue()
        raw_df = read_csv_without_header(file_bytes)
        return apply_detected_header(raw_df)
    raise ValueError("Excelファイル（.xlsx / .xls）またはCSVファイルをアップロードしてください。")


def extract_spreadsheet_id(spreadsheet_url: str) -> str | None:
    spreadsheet_url = spreadsheet_url.strip()
    if not spreadsheet_url:
        return None

    path_match = re.search(r"/spreadsheets/d/([^/]+)", spreadsheet_url)
    if path_match:
        return path_match.group(1)

    if "/" not in spreadsheet_url and " " not in spreadsheet_url:
        return spreadsheet_url

    return None


def build_google_sheet_csv_url(spreadsheet_url: str, sheet_name: str, gid: str) -> str:
    spreadsheet_id = extract_spreadsheet_id(spreadsheet_url)
    if not spreadsheet_id:
        raise ValueError("GoogleスプレッドシートURLからIDを取得できませんでした。")

    gid = gid.strip()
    if gid:
        return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}"

    sheet_name = sheet_name.strip()
    if sheet_name:
        encoded_sheet_name = quote(sheet_name)
        return (
            f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/gviz/tq"
            f"?tqx=out:csv&sheet={encoded_sheet_name}"
        )

    raise ValueError("シート名またはgidを入力してください。")


def fetch_google_sheet_csv(spreadsheet_url: str, sheet_name: str, gid: str, timeout: int = 20) -> bytes:
    csv_url = build_google_sheet_csv_url(spreadsheet_url, sheet_name, gid)

    try:
        response = requests.get(csv_url, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ValueError(
            "Googleスプレッドシートを読み込めませんでした。"
            "共有設定が「リンクを知っている全員が閲覧可」になっているか確認してください。"
        ) from exc

    if not response.content:
        raise ValueError("GoogleスプレッドシートからCSVデータを取得できませんでした。")

    return response.content


def read_google_sheet_database(spreadsheet_url: str, sheet_name: str, gid: str) -> pd.DataFrame:
    file_bytes = fetch_google_sheet_csv(spreadsheet_url, sheet_name, gid)
    raw_df = read_csv_without_header(file_bytes)
    return apply_detected_header(raw_df)


def find_missing_columns(df: pd.DataFrame) -> list[str]:
    return [column for column in REQUIRED_COLUMNS if column not in df.columns]


def filter_by_approval(df: pd.DataFrame) -> pd.DataFrame:
    approval = df["承認状態"].map(text_value)
    return df[approval.isin(APPROVED_STATUSES)].copy()


def unique_options(df: pd.DataFrame, column: str) -> list[str]:
    if column not in df.columns:
        return []

    if column == "対象部位":
        values = {normalize_body_part(value) for value in df[column].dropna() if text_value(value)}
        return sorted(values, key=lambda value: (BODY_PART_ORDER_INDEX.get(value, len(BODY_PART_ORDER)), value))

    values = {text_value(value) for value in df[column].dropna() if text_value(value)}
    return sorted(values)


def apply_filters(
    df: pd.DataFrame,
    body_part: str,
    category: str,
    loading_condition: str,
    disease_keyword: str,
) -> pd.DataFrame:
    filtered = df.copy()

    if body_part != "すべて":
        filtered = filtered[filtered["対象部位"].map(normalize_body_part) == body_part]
    if category != "すべて":
        filtered = filtered[filtered["カテゴリ"].map(text_value) == category]
    if loading_condition != "すべて":
        filtered = filtered[filtered["荷重条件"].map(text_value) == loading_condition]
    if disease_keyword:
        keyword = disease_keyword.strip()
        filtered = filtered[
            filtered["対象疾患タグ"]
            .map(text_value)
            .str.contains(keyword, case=False, na=False, regex=False)
        ]

    return filtered


def extract_google_drive_file_id(url: str) -> str | None:
    parsed = urlparse(url)
    if "drive.google.com" not in parsed.netloc:
        return None

    file_path_match = re.search(r"/file/d/([^/]+)", parsed.path)
    if file_path_match:
        return file_path_match.group(1)

    query = parse_qs(parsed.query)
    if "id" in query and query["id"]:
        return query["id"][0]

    return None


def to_download_url(url: str) -> str:
    file_id = extract_google_drive_file_id(url)
    if file_id:
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return url


def fetch_image(image_url: str, timeout: int = 20) -> Image.Image:
    if not image_url:
        raise ValueError("画像URLが空です。")

    response = requests.get(to_download_url(image_url), timeout=timeout)
    response.raise_for_status()

    try:
        image = Image.open(io.BytesIO(response.content))
        image.load()
    except UnidentifiedImageError as exc:
        raise ValueError("画像として読み込めませんでした。") from exc

    return image.convert("RGB")


def add_image_page(pdf: canvas.Canvas, image: Image.Image, page_size: tuple[float, float]) -> None:
    page_width, page_height = page_size
    margin = 8
    max_width = page_width - margin * 2
    max_height = page_height - margin * 2
    image_width, image_height = image.size
    scale = min(max_width / image_width, max_height / image_height)
    draw_width = image_width * scale
    draw_height = image_height * scale
    x = (page_width - draw_width) / 2
    y = (page_height - draw_height) / 2

    image_buffer = io.BytesIO()
    image.save(image_buffer, format="JPEG", quality=95)
    image_buffer.seek(0)

    pdf.drawInlineImage(
        Image.open(image_buffer),
        x,
        y,
        width=draw_width,
        height=draw_height,
        preserveAspectRatio=True,
    )
    pdf.showPage()


def create_pdf(selected_rows: Iterable[pd.Series]) -> tuple[bytes | None, list[str]]:
    page_size = portrait(A5)
    pdf_buffer = io.BytesIO()
    pdf = canvas.Canvas(pdf_buffer, pagesize=page_size)
    failures: list[str] = []
    page_count = 0

    for row in selected_rows:
        exercise_id = text_value(row.get("運動ID"))
        exercise_name = text_value(row.get("運動名"))
        image_url = text_value(row.get("画像URL"))
        label = f"{exercise_id} {exercise_name}".strip() or "運動名未設定"

        try:
            image = fetch_image(image_url)
        except Exception as exc:  # noqa: BLE001 - user-facing failure details are useful here.
            failures.append(f"{label}: {exc}")
            continue

        add_image_page(pdf, image, page_size)
        page_count += 1

    if page_count == 0:
        return None, failures

    pdf.save()
    return pdf_buffer.getvalue(), failures


def render_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.subheader("フィルター")
    col1, col2, col3 = st.columns(3)

    with col1:
        body_part = st.selectbox("対象部位", ["すべて", *unique_options(df, "対象部位")])
    with col2:
        category = st.selectbox("カテゴリ", ["すべて", *unique_options(df, "カテゴリ")])
    with col3:
        loading_condition = st.selectbox("荷重条件", ["すべて", *unique_options(df, "荷重条件")])

    disease_keyword = st.text_input("対象疾患タグのキーワード検索", value="")
    return apply_filters(df, body_part, category, loading_condition, disease_keyword)


def render_selection_table(filtered_df: pd.DataFrame, all_df: pd.DataFrame) -> pd.DataFrame:
    st.subheader("運動一覧")

    selected_ids = get_selected_exercise_ids()

    if filtered_df.empty:
        st.info("条件に一致する運動はありません。")
        return selected_rows_from_ids(all_df, selected_ids)

    display_df = filtered_df.reset_index(drop=True)
    table = display_df[DISPLAY_COLUMNS].copy()
    table.insert(0, "選択", table["運動ID"].map(text_value).isin(selected_ids))

    edited_table = st.data_editor(
        table,
        hide_index=True,
        use_container_width=True,
        column_config={"選択": st.column_config.CheckboxColumn("選択", default=False)},
        disabled=DISPLAY_COLUMNS,
        key=selection_table_key(display_df),
    )

    visible_ids = set(display_df["運動ID"].map(text_value).tolist())
    checked_ids = set(edited_table.loc[edited_table["選択"], "運動ID"].map(text_value).tolist())
    updated_selected_ids = selected_ids.difference(visible_ids).union(checked_ids)
    store_selected_exercise_ids(updated_selected_ids)

    return selected_rows_from_ids(all_df, updated_selected_ids)


def database_params(spreadsheet_url: str, sheet_name: str, gid: str) -> tuple[str, str, str]:
    return (spreadsheet_url.strip(), sheet_name.strip(), gid.strip())


def store_database(df: pd.DataFrame, source: str, params: tuple[str, ...]) -> None:
    st.session_state[DATABASE_SESSION_KEY] = df
    st.session_state[DATABASE_SOURCE_SESSION_KEY] = source
    st.session_state[DATABASE_PARAMS_SESSION_KEY] = params


def get_stored_database(source: str, params: tuple[str, ...]) -> pd.DataFrame | None:
    if st.session_state.get(DATABASE_SOURCE_SESSION_KEY) != source:
        return None
    if st.session_state.get(DATABASE_PARAMS_SESSION_KEY) != params:
        return None

    stored_df = st.session_state.get(DATABASE_SESSION_KEY)
    if isinstance(stored_df, pd.DataFrame):
        return stored_df.copy()

    return None


def load_database_from_sidebar() -> pd.DataFrame | None:
    data_source = st.sidebar.radio(
        "読み込み元",
        ["Googleスプレッドシート", "ファイルアップロード"],
        index=0,
    )

    if data_source == "Googleスプレッドシート":
        spreadsheet_url = st.sidebar.text_input(
            "スプレッドシートURL",
            value=DEFAULT_SPREADSHEET_URL,
        )
        sheet_name = st.sidebar.text_input("シート名", value=DEFAULT_SHEET_NAME)
        gid = st.sidebar.text_input("gid", value=DEFAULT_SHEET_GID)
        params = database_params(spreadsheet_url, sheet_name, gid)

        if st.sidebar.button("運動DBを読み込む", type="primary"):
            try:
                df = read_google_sheet_database(spreadsheet_url, sheet_name, gid)
                store_database(df, data_source, params)
                st.sidebar.success("運動DBを読み込みました。")
                return df.copy()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Googleスプレッドシートを読み込めませんでした: {exc}")
                return None

        stored_df = get_stored_database(data_source, params)
        if stored_df is not None:
            st.sidebar.success("運動DBを読み込み済みです。")
            return stored_df

        st.info("サイドバーの「運動DBを読み込む」を押してください。")
        return None

    uploaded_file = st.sidebar.file_uploader(
        "運動DBファイルをアップロード",
        type=["xlsx", "xls", "csv"],
    )

    if uploaded_file is None:
        st.info("ExcelまたはCSV形式の運動DBをアップロードしてください。")
        return None

    params = (uploaded_file.name, str(getattr(uploaded_file, "size", "")))
    stored_df = get_stored_database(data_source, params)
    if stored_df is not None:
        return stored_df

    try:
        df = read_exercise_database(uploaded_file)
        store_database(df, data_source, params)
        return df.copy()
    except Exception as exc:  # noqa: BLE001
        st.error(f"ファイルを読み込めませんでした: {exc}")
        return None


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    st.title(APP_TITLE)
    st.warning("患者を直接特定できる個人情報は入力しないでください")
    st.caption("PTが選択した運動画像のみをPDF化します。禁忌判断や最終判断は医療者が行ってください。")

    df = load_database_from_sidebar()
    if df is None:
        return

    missing_columns = find_missing_columns(df)
    if missing_columns:
        st.error("運動DBに必要な列が不足しています。")
        st.write(missing_columns)
        return

    df = normalize_exercise_dataframe(df)
    approved_df = filter_by_approval(df)
    prune_selected_exercise_ids(approved_df)
    st.caption(f"読み込み件数: {len(df)}件 / 表示対象: {len(approved_df)}件")

    filtered_df = render_filters(approved_df)
    selected_df = render_selection_table(filtered_df, approved_df)
    st.metric("選択された運動数", len(selected_df))

    if st.button("PDFを作成", type="primary", disabled=selected_df.empty):
        with st.spinner("PDFを作成しています..."):
            pdf_bytes, failures = create_pdf((row for _, row in selected_df.iterrows()))

        if failures:
            st.error("画像取得に失敗した運動があります。")
            for failure in failures:
                st.write(f"- {failure}")

        if pdf_bytes:
            st.success("PDFを作成しました。")
            st.download_button(
                "PDFをダウンロード",
                data=pdf_bytes,
                file_name=OUTPUT_FILENAME,
                mime="application/pdf",
            )
        else:
            st.error("PDFに配置できる画像がありませんでした。画像URLを確認してください。")


if __name__ == "__main__":
    main()
