from flask import Flask, request, render_template, send_file, redirect, url_for
import fitz  # PyMuPDF
from PIL import Image
from io import BytesIO
import os
import uuid

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def compress_pdf(input_path, output_path, image_quality=30):
    try:
        doc = fitz.open(input_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            images = page.get_images(full=True)
            image_rects = {}
            blocks = page.get_text("dict")["blocks"]
            for b in blocks:
                if b["type"] == 1:
                    xref = b.get("image")
                    rect = fitz.Rect(b["bbox"])
                    image_rects[xref] = rect

            for img in images:
                xref = img[0]
                rect = image_rects.get(xref)
                if rect is None:
                    continue

                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                pil_image = Image.open(BytesIO(image_bytes)).convert("RGB")
                pil_image = pil_image.resize(
                    (max(1, pil_image.width // 2), max(1, pil_image.height // 2)),
                    resample=Image.Resampling.LANCZOS
                )
                compressed_io = BytesIO()
                pil_image.save(compressed_io, format="JPEG", quality=image_quality)
                compressed_image_bytes = compressed_io.getvalue()
                page.insert_image(rect, stream=compressed_image_bytes)
                page.add_redact_annot(rect, fill=(1, 1, 1))
            page.apply_redactions()

        doc.save(output_path, garbage=4, deflate=True, clean=True)
        doc.close()
        return True
    except Exception as e:
        print("Compression error:", e)
        return False

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        uploaded_file = request.files.get("pdf_file")
        if uploaded_file and uploaded_file.filename.endswith(".pdf"):
            input_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}.pdf")
            output_path = os.path.join(UPLOAD_FOLDER, f"compressed_{os.path.basename(input_path)}")
            uploaded_file.save(input_path)

            success = compress_pdf(input_path, output_path)

            if success:
                return send_file(output_path, as_attachment=True)
            else:
                return "Compression failed", 500
        return redirect(url_for('index'))

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8000)
