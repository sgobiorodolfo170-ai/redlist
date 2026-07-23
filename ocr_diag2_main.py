"""Minimal diagnostic for PaddleOCR in frozen build"""
import os, sys

# Write to known location immediately
log_file = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "ocr_diag2.log")
with open(log_file, "w") as f:
    f.write(f"START\n")
    f.write(f"frozen={getattr(sys, 'frozen', False)}\n")
    f.write(f"MEIPASS={getattr(sys, '_MEIPASS', 'N/A')}\n")
    f.write(f"executable={sys.executable}\n")
    f.write(f"path={sys.path}\n")

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

with open(log_file, "a") as f:
    f.write("envar set\n")

try:
    from paddleocr import PaddleOCR
    with open(log_file, "a") as f:
        f.write("IMPORT OK\n")
except Exception as e:
    import traceback
    with open(log_file, "a") as f:
        f.write(f"IMPORT FAILED: {e}\n")
        traceback.print_exc(file=f)
        f.write("DONE\n")
        raise SystemExit(1)

try:
    ocr = PaddleOCR(use_angle_cls=True, lang="ch", use_gpu=False, show_log=False)
    with open(log_file, "a") as f:
        f.write("INSTANTIATE OK\n")
except Exception as e:
    import traceback
    with open(log_file, "a") as f:
        f.write(f"INSTANTIATE FAILED: {e}\n")
        traceback.print_exc(file=f)

with open(log_file, "a") as f:
    f.write("DONE\n")
