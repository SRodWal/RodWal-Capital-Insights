# app/core/log.py
import logging, os

def get_logger(name="rodwal"):
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    fmt = logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s", "%H:%M:%S")
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    os.makedirs("logs", exist_ok=True)
    fh = logging.FileHandler("logs/app.log", encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger
