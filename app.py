import streamlit as st
from PIL import Image, ImageSequence
import io
import os

# ページ設定
st.set_page_config(page_title="最強の画像圧縮ツール", layout="centered")
st.title("✂️ 時間トリミング & 圧縮ツール")
st.write("アニメーションの「切り抜き」と「速度調整」を行い、512KB以下に圧縮します。")

# 定数
TARGET_SIZE = 512 * 1024  # 512 KB
MAX_ATTEMPTS = 15         # 圧縮試行回数の上限

def compress_image(image_file, output_format, custom_duration, start_frame, end_frame):
    """
    指定範囲のフレームを抽出し、指定サイズ以下になるまで縮小・圧縮を繰り返す
    """
    try:
        img = Image.open(image_file)
    except Exception as e:
        return None, f"エラー: 画像を開けませんでした。 {e}"

    img_format = output_format.upper()
    
    # APNG対応
    if img_format == "APNG":
        if getattr(img, "is_animated", False):
            img_format = "GIF"
        else:
            img_format = "PNG"

    if img_format == "JPEG":
        img = img.convert("RGB")

    # 圧縮ループ用変数
    scale = 1.0
    quality = 90
    output_buffer = io.BytesIO()
    
    is_animated = getattr(img, "is_animated", False) and img_format == "GIF"

    # 全フレームを先に取得（トリミングのため）
    all_frames = []
    if is_animated:
        for f in ImageSequence.Iterator(img):
            all_frames.append(f.copy())
    else:
        all_frames.append(img.copy())

    # 指定範囲でスライス（トリミング実行）
    # end_frameはインデックス+1の扱いにするため調整
    selected_frames = all_frames[start_frame : end_frame + 1]
    
    if not selected_frames:
        return None, "フレームが選択されていません。"

    # プログレスバー
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i in range(MAX_ATTEMPTS):
        status_text.text(f"最適化中... 試行 {i+1}/{MAX_ATTEMPTS} (倍率: {scale:.2f})")
        progress_bar.progress((i + 1) / MAX_ATTEMPTS)

        output_buffer = io.BytesIO()
        
        # 現在のスケールでリサイズ幅計算
        base_frame = selected_frames[0]
        new_width = int(base_frame.width * scale)
        new_height = int(base_frame.height * scale)
        
        if new_width < 1 or new_height < 1:
            break

        if is_animated:
            # --- アニメーション (GIF) 処理 ---
            resized_frames = []
            for f in selected_frames:
                rf = f.resize((new_width, new_height), Image.Resampling.LANCZOS)
                resized_frames.append(rf)

            if resized_frames:
                resized_frames[0].save(
                    output_buffer,
                    format="GIF",
                    save_all=True,
                    append_images=resized_frames[1:],
                    optimize=True,
                    duration=custom_duration,
                    loop=0
                )
        else:
            # --- 静止画処理 ---
            img_resized = selected_frames[0].resize((new_width, new_height), Image.Resampling.LANCZOS)
            if img_format == "JPEG":
                img_resized.save(output_buffer, format="JPEG", quality=int(quality), optimize=True)
            else:
                img_resized.save(output_buffer, format="PNG", optimize=True)

        # サイズチェック
        current_size = output_buffer.tell()
        
        if current_size <= TARGET_SIZE:
            progress_bar.empty()
            status_text.text("✅ 完了！")
            return output_buffer, None
        
        # サイズオーバー時の調整
        scale *= 0.85
        if img_format == "JPEG":
            quality = max(10, quality - 10)

    return None, "圧縮できませんでした。範囲を短くするか、元画像を変更してください。"

# --- UI部分 ---
file = st.file_uploader("画像をアップロード", type=["png", "jpg", "jpeg", "gif", "webp"])

if file is not None:
    # 画像情報の取得
    img_preview = Image.open(file)
    st.image(file, caption="元画像", width=300)
    
    # アニメーション情報の取得
    is_anim = getattr(img_preview, "is_animated", False)
    total_frames = img_preview.n_frames if is_anim else 1
    default_duration = img_preview.info.get('duration', 100)
    
    st.divider()
    st.subheader("⚙️ 編集設定")

    # --- 設定エリア ---
    col1, col2 = st.columns(2)
    
    with col1:
        format_option = st.selectbox("保存形式", ("GIF", "APNG", "PNG", "JPEG"))

    # アニメーション設定（GIF/APNG選択時かつ、元がアニメーションの場合）
    target_is_anim = format_option in ["GIF", "APNG"] and is_anim
    
    start_f, end_f = 0, total_frames - 1
    custom_duration = default_duration

    if target_is_anim:
        # トリミングスライダー
        st.markdown("##### ✂️ 時間の切り抜き (トリミング)")
        start_f, end_f = st.slider(
            "使用するフレーム範囲を選択",
            min_value=0,
            max_value=total_frames - 1,
            value=(0, total_frames - 1),
            help="左端と右端を動かして、必要な部分だけを切り取ってください。"
        )
        
        selected_count = end_f - start_f + 1
        st.caption(f"選択範囲: {start_f}コマ目 〜 {end_f}コマ目 (計 {selected_count}コマ)")

        st.divider()

        # 速度設定
        with col2:
            st.markdown("##### ⏱️ 再生速度")
            custom_duration = st.number_input(
                "1コマの時間 (ms)",
                min_value=10, max_value=5000, value=int(default_duration), step=10
            )
        
        # 合計時間の計算と表示
        total_time_sec = (selected_count * custom_duration) / 1000
        st.info(f"🎬 完成予定の再生時間: **{total_time_sec:.2f} 秒**")
    
    else:
        st.info("静止画として保存します（1フレーム目のみ使用）。")
        start_f, end_f = 0, 0

    # 実行ボタン
    st.divider()
    if st.button("変換・圧縮を実行", type="primary", use_container_width=True):
        file.seek(0)
        with st.spinner('フレームを解析して最適化中...'):
            compressed_data, error = compress_image(file, format_option, custom_duration, start_f, end_f)

        if error:
            st.error(error)
        else:
            size_kb = compressed_data.tell() / 1024
            st.success(f"成功！ サイズ: {size_kb:.2f} KB")
            
            # ダウンロード
            ext = "gif" if format_option == "APNG" else format_option.lower()
            mime_type = "image/gif" if format_option == "APNG" else f"image/{ext}"
            
            st.download_button(
                label="画像をダウンロード",
                data=compressed_data.getvalue(),
                file_name=f"cut_compressed.{ext}",
                mime=mime_type,
                use_container_width=True
            )