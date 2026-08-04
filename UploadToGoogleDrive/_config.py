from pathlib import Path
import platform

LINUX_PREFIX   = Path("/mnt/dna_pipelines")
WINDOWS_PREFIX = Path("W:/")

DNAP_NETWORK_SUBDIR = Path(
    "0.253 Short Read (SR)"
    "/1. Short Read Library creation"
    "/8. MAVE_SGE"
    "/SGE Upload"
)

FILES_TO_UPLOAD = (".csv", ".pdf")

BASE_PREFIX   = LINUX_PREFIX if platform.system() == "Linux" else WINDOWS_PREFIX
NETWORK_DIR   = BASE_PREFIX / DNAP_NETWORK_SUBDIR
MAVE_FOLDER_ID = ""
PROCESSED_DIR = ""

REFRESH_RATE = 15