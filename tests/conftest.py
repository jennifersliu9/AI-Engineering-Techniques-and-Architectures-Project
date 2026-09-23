import os

os.environ["HARBORLINE_RETRIEVE_BACKEND"] = "tfidf"
os.environ["HARBORLINE_ANSWER_MODE"] = "retrieve"

from harborline.config import get_settings

get_settings.cache_clear()
