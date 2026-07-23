"""Quick diagnostic: import PaddleOCR and log result"""
import os, sys, traceback

log_file = os.path.join(os.path.dirname(sys.executable), "ocr_diag.log")

def log(msg):
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{msg}\n")

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["REDLIST_DEBUG"] = "1"

log(f"=== OCR Diagnostic Start ===")
log(f"frozen={getattr(sys, 'frozen', False)}")
log(f"MEIPASS={getattr(sys, '_MEIPASS', 'N/A')}")
log(f"sys.path={sys.path}")
log(f"sys.executable={sys.executable}")

try:
    from paddleocr import PaddleOCR
    log("import paddleocr.PaddleOCR: SUCCESS")
except Exception as e:
    log(f"import paddleocr.PaddleOCR: FAILED - {e}")
    log(traceback.format_exc())

try:
    ocr = PaddleOCR(use_angle_cls=True, lang="ch", use_gpu=False, show_log=False)
    log("PaddleOCR(use_gpu=False): SUCCESS")
except Exception as e:
    log(f"PaddleOCR instantiation: FAILED - {e}")
    log(traceback.format_exc())

log("=== OCR Diagnostic End ===")
