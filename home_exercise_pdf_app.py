from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, urlparse

import pandas as pd
import requests
import streamlit as st
from PIL import Image, UnidentifiedImageError
from reportlab.lib.pagesizes import A5, portrait
from reportlab.pdfgen import canvas


APP_TITLE = "足部ホームエクササイズPDF出力アプリ"
OUTPUT_FILENAME = "home_exercise_program.pdf"
APPROVED_STATUSES = {"採用", "採用候補"}
DISPLAY_COLUMNS = ["運動ID", "運動名", "対象部位", "カテゴリ", "回数", "注意点"]
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


def read_exercise_database(uploaded_file) -> pd.DataFrame:
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(uploaded_file)
    if suffix == ".csv":
        file_bytes = uploaded_file.getvalue()
        for encoding in ("utf-8-sig", "cp932"):
            try:
                return pd.read_csv(io.BytesIO(file_bytes), encoding=encoding)
            except UnicodeDecodeError:
                continue
        return pd.read_csv(io.BytesIO(file_bytes))
    raise ValueError("Excelファイル（.xlsx / .xls）またはCSVファイルをアップロードしてください。")


def text_value(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def find_missing_columns(df: pd.DataFrame) -> list[str]:
    return [column for column in REQUIRED_COLUMNS if column not in df.columns]


def filter_by_approval(df: pd.DataFrame) -> pd.DataFrame:
    approval = df["承認状態"].map(text_value)
    return df[approval.isin(APPROVED_STATUSES)].copy()


def unique_options(df: pd.DataFrame, column: str) -> list[str]:
    if column not in df.columns:
        return []
    values = sorted({text_value(value) for value in df[column].dropna() if text_value(value)})
    return values


def apply_filters(
    df: pd.DataFrame,
    body_part: str,
    category: str,
    loading_condition: str,
    disease_keyword: str,
) -> pd.DataFrame:
    filtered = df.copy()

    if body_part != "すべて":
        filtered = filtered[filtered["対象部位"].map(text_value) == body_part]
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


def render_selection_table(df: pd.DataFrame) -> pd.DataFrame:
    st.subheader("運動一覧")

    if df.empty:
        st.info("条件に一致する運動はありません。")
        return df.iloc[0:0]

    display_df = df.reset_index(drop=True)
    table = display_df[DISPLAY_COLUMNS].copy()
    table.insert(0, "選択", False)

    edited_table = st.data_editor(
        table,
        hide_index=True,
        use_container_width=True,
        column_config={"選択": st.column_config.CheckboxColumn("選択", default=False)},
        disabled=DISPLAY_COLUMNS,
        key="exercise_selection_table",
    )

    selected_positions = edited_table.index[edited_table["選択"]].tolist()
    return display_df.iloc[selected_positions].copy()


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    st.title(APP_TITLE)
    st.warning("患者を直接特定できる個人情報は入力しないでください")
    st.caption("PTが選択した運動画像のみをPDF化します。禁忌判断や最終判断は医療者が行ってください。")

    uploaded_file = st.sidebar.file_uploader(
        "運動DBファイルをアップロード",
        type=["xlsx", "xls", "csv"],
    )

    if uploaded_file is None:
        st.info("ExcelまたはCSV形式の運動DBをアップロードしてください。")
        return

    try:
        df = read_exercise_database(uploaded_file)
    except Exception as exc:  # noqa: BLE001
        st.error(f"ファイルを読み込めませんでした: {exc}")
        return

    missing_columns = find_missing_columns(df)
    if missing_columns:
        st.error("運動DBに必要な列が不足しています。")
        st.write(missing_columns)
        return

    approved_df = filter_by_approval(df)
    st.caption(f"読み込み件数: {len(df)}件 / 表示対象: {len(approved_df)}件")

    filtered_df = render_filters(approved_df)
    selected_df = render_selection_table(filtered_df)
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
