import streamlit as st
from PIL import Image, ImageSequence
import io
import os

# --- ページ設定 ---
st.set_page_config(page_title="512KB以下画像圧縮ツール", layout="centered", page_icon="🎨")

# --- カスタムCSS (ダークテーマ & 高品質デザイン) ---
st.markdown("""
    <style>
    /* 全体の背景とフォント */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    
    /* タイトル周り */
    h1 {
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 700;
        color: #FFFFFF;
        text-shadow: 0 2px 4px rgba(0,0,0,0.5);
    }
    
    /* ファイルアップローダーのカスタマイズ */
    [data-testid="stFileUploader"] {
        background-color: #1A1C24;
        border: 2px dashed #3D4050;
        border-radius: 12px;
        padding: 20px;
        transition: border-color 0.3s;
    }
    [data-testid="stFileUploader"]:hover {
        border-color: #4A90E2;
    }

    /* メインボタン (変換開始) */
    div.stButton > button {
        width: 100%;
        background: linear-gradient(90deg, #4A90E2 0%, #007BFF 100%);
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 16px;
        box-shadow: 0 4px 14px rgba(74, 144, 226, 0.3);
        transition: all 0.2s ease-in-out;
    }
    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(74, 144, 226, 0.5);
        color: white;
    }
    div.stButton > button:active {
        transform: translateY(1px);
    }

    /* ダウンロードボタン (別スタイル) */
    /* Streamlitはボタンのクラスを区別しにくいため、後述のロジックでダウンロードボタンが表示される場所のスタイルを適用 */

    /* スライダーと数値入力 */
    div[data-baseweb="slider"] {
        padding-top: 10px;
    }
    
    /* 成功メッセージの背景 */
    .stSuccess {
        background-color: #143628;
        color: #28a745;
        border: 1px solid #1e5c38;
    }
    
    /* 区切り線 */
    hr {
        border-color: #333;
    }
    
    /* 結果表示エリアのカード化 */
    .result-card {
        background-color: #1A1C24;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #333;
        margin-top: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    </style>
    """, unsafe_allow_html=True)

# タイトル表示
st.title("512KB以下画像圧縮ツール")
st.caption("対応ファイル　PNG,APNG,JPEG,GIF")

st.markdown("""
<div style='background-color: #1A1C24; padding: 15px; border-radius: 10px; border-left: 5px solid #4A90E2; margin-bottom: 20px;'>
    <small style='color: #B0B3B8;'>
    GIF/APNGのアニメーションを維持したまま、Discord等のファイル制限(512KB)に合わせてスマートに圧縮します。
    トリミング機能と再生速度の調整も可能です。
    </small>
</div>
""", unsafe_allow_html=True)

# 定数
TARGET_SIZE = 512 * 1024
MAX_ATTEMPTS = 15

def compress_image(image_file, output_format, custom_duration, start_frame, end_frame):
    try:
        img = Image.open(image_file)
    except Exception as e:
        return None, f"エラー: 画像を開けませんでした。 {e}"

    img_format = output_format.upper()
    if img_format == "APNG":
        if getattr(img, "is_animated", False):
            img_format = "GIF"
        else:
            img_format = "PNG"

    if img_format == "JPEG":
        img = img.convert("RGB")

    scale = 1.0
    quality = 90
    output_buffer = io.BytesIO()
    is_animated = getattr(img, "is_animated", False) and img_format == "GIF"

    all_frames = []
    if is_animated:
        for f in ImageSequence.Iterator(img):
            all_frames.append(f.copy())
    else:
        all_frames.append(img.copy())

    selected_frames = all_frames[start_frame : end_frame + 1]
    if not selected_frames:
        return None, "フレームが選択されていません。"

    progress_bar = st.progress(0)
    status_text = st.empty()

    for i in range(MAX_ATTEMPTS):
        status_text.caption(f"最適化プロセス実行中... Step {i+1}/{MAX_ATTEMPTS} (Scale: {scale:.2f})")
        progress_bar.progress((i + 1) / MAX_ATTEMPTS)

        output_buffer = io.BytesIO()
        base_frame = selected_frames[0]
        new_width = int(base_frame.width * scale)
        new_height = int(base_frame.height * scale)
        
        if new_width < 1 or new_height < 1:
            break

        if is_animated:
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
            img_resized = selected_frames[0].resize((new_width, new_height), Image.Resampling.LANCZOS)
            if img_format == "JPEG":
                img_resized.save(output_buffer, format="JPEG", quality=int(quality), optimize=True)
            else:
                img_resized.save(output_buffer, format="PNG", optimize=True)

        current_size = output_buffer.tell()
        if current_size <= TARGET_SIZE:
            progress_bar.empty()
            status_text.empty()
            return output_buffer, None
        
        scale *= 0.85
        if img_format == "JPEG":
            quality = max(10, quality - 10)

    return None, "圧縮できませんでした。範囲を短くするか、元画像を変更してください。"

# --- UI部分 ---
file = st.file_uploader("画像をドラッグ＆ドロップ", type=["png", "jpg", "jpeg", "gif", "webp"])

if file is not None:
    img_preview = Image.open(file)
    
    # プレビュー画像の表示（枠付き）
    st.markdown("<div style='margin-top: 10px; margin-bottom: 20px;'>", unsafe_allow_html=True)
    st.image(file, caption="Original Image", width=300)
    st.markdown("</div>", unsafe_allow_html=True)

    is_anim = getattr(img_preview, "is_animated", False)
    total_frames = img_preview.n_frames if is_anim else 1
    default_duration = img_preview.info.get('duration', 100)
    
    st.markdown("<h3 style='color:#4A90E2;'>⚙️ Editor Settings</h3>", unsafe_allow_html=True)
    
    # レイアウトコンテナ
    with st.container():
        col1, col2 = st.columns(2)
        
        with col1:
            format_option = st.selectbox("出力フォーマット", ("GIF", "APNG", "PNG", "JPEG"))

        target_is_anim = format_option in ["GIF", "APNG"] and is_anim
        start_f, end_f = 0, total_frames - 1
        custom_duration = default_duration

        if target_is_anim:
            st.markdown("<label style='font-size:14px; font-weight:bold;'>✂️ フレーム・トリミング</label>", unsafe_allow_html=True)
            start_f, end_f = st.slider(
                "範囲選択",
                min_value=0, max_value=total_frames - 1, value=(0, total_frames - 1),
                label_visibility="collapsed"
            )
            
            selected_count = end_f - start_f + 1
            st.caption(f"選択範囲: {start_f} - {end_f} (計 {selected_count} frames)")

            with col2:
                st.markdown("<label style='font-size:14px; font-weight:bold;'>⏱️ 1コマの時間(ms)</label>", unsafe_allow_html=True)
                custom_duration = st.number_input(
                    "ms",
                    min_value=10, max_value=5000, value=int(default_duration), step=10,
                    label_visibility="collapsed"
                )
            
            total_time_sec = (selected_count * custom_duration) / 1000
            st.markdown(f"""
            <div style='background-color: #2D2F36; padding: 10px; border-radius: 8px; text-align: center; margin-top: 10px;'>
                <span style='color: #B0B3B8; font-size: 0.9em;'>完成予定の再生時間</span><br>
                <span style='color: #4A90E2; font-size: 1.2em; font-weight: bold;'>{total_time_sec:.2f} sec</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            start_f, end_f = 0, 0

    st.write("") # Spacer
    
    # 実行ボタン
    if st.button("ROCK AND ROLL (変換開始)", type="primary"):
        file.seek(0)
        with st.spinner('Processing...'):
            compressed_data, error = compress_image(file, format_option, custom_duration, start_f, end_f)

        if error:
            st.error(error)
        else:
            size_kb = compressed_data.tell() / 1024
            
            # 結果表示エリア（カスタムCSSの.result-cardを適用するためのHTMLハック）
            st.markdown(f"""
            <div class="result-card">
                <h3 style="color: #2ecc71; margin-top:0;">✅ Completed!</h3>
                <p style="color: #D1D5DB;">最終サイズ: <strong>{size_kb:.2f} KB</strong> <span style="color: #6B7280;">(Target: 512KB)</span></p>
            </div>
            """, unsafe_allow_html=True)
            
            ext = "gif" if format_option == "APNG" else format_option.lower()
            mime_type = "image/gif" if format_option == "APNG" else f"image/{ext}"
            
            # ダウンロードボタン用の余白
            st.write("")
            st.download_button(
                label="📥 画像をダウンロード",
                data=compressed_data.getvalue(),
                file_name=f"optimized_image.{ext}",
                mime=mime_type,
                use_container_width=True
            )