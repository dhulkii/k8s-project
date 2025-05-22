import tkinter as tk
from tkinter import filedialog, messagebox
import fitz  # PyMuPDF
import os
from PIL import Image
from io import BytesIO
import threading

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

def choose_file():
    file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
    if file_path:
        input_entry.delete(0, tk.END)
        input_entry.insert(0, file_path)
        status_label.config(text="Selected file: " + os.path.basename(file_path))
        compress_button.config(state="normal")

def compress_and_save():
    input_path = input_entry.get()
    if not input_path or not os.path.isfile(input_path):
        status_label.config(text="Error: Please select a valid PDF file.", fg="red")
        return

    output_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
    if not output_path:
        status_label.config(text="Compression cancelled.", fg="orange")
        return

    compress_button.config(state="disabled")
    status_label.config(text="Compressing...", fg="blue")
    root.update_idletasks()

    def run_compression(in_path, out_path):
        success = compress_pdf(in_path, out_path, image_quality=30)
        if success:
            status_label.config(text=f"Compression successful! Saved to:\n{out_path}", fg="green")
            messagebox.showinfo("Success", "PDF compressed and saved successfully!")
        else:
            status_label.config(text="Compression failed. See console for errors.", fg="red")
        compress_button.config(state="normal")

    threading.Thread(target=run_compression, args=(input_path, output_path)).start()


# Build GUI
root = tk.Tk()
root.title("PDF Compressor")
root.geometry("500x200")
root.resizable(False, False)

frame = tk.Frame(root, padx=20, pady=20)
frame.pack(fill=tk.BOTH, expand=True)

title_label = tk.Label(frame, text="PDF Compressor", font=("Helvetica", 18, "bold"))
title_label.grid(row=0, column=0, columnspan=3, pady=(0, 15))

tk.Label(frame, text="Select PDF File:", font=("Arial", 12)).grid(row=1, column=0, sticky="w")

input_entry = tk.Entry(frame, width=40, font=("Arial", 11))
input_entry.grid(row=2, column=0, padx=(0,10), pady=5)

browse_button = tk.Button(frame, text="Browse", command=choose_file, width=12)
browse_button.grid(row=2, column=1, pady=5)

compress_button = tk.Button(frame, text="Compress & Save", command=compress_and_save, bg="#28a745", fg="white", font=("Arial", 12, "bold"))
compress_button.grid(row=3, column=0, columnspan=2, pady=20)
compress_button.config(state="disabled")

status_label = tk.Label(frame, text="", font=("Arial", 10), fg="green", wraplength=460, justify="left")
status_label.grid(row=4, column=0, columnspan=3, sticky="w")

root.mainloop()
