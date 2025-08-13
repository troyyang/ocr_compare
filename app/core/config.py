from dotenv import load_dotenv
import os

# query the path of the current file
root_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
# the path of the .env file
env_path = os.path.join(root_path, '.env')

# Check if the .env file exists
if not os.path.exists(env_path):
    env_path = os.path.join(root_path, '../', '.env')

if os.path.exists(env_path):
    # Load environment variables from the .env file
    load_dotenv(env_path)

# Load environment variables from .env file
load_dotenv()

# Access the environment variables
API_ENV: str = os.getenv('API_ENV', 'dev')
SECRET_KEY: str = os.getenv('SECRET_KEY')
# ---------------------------API CONFIG----------------------------
API_HOST: str = os.getenv('API_HOST', '0.0.0.0')
API_PORT: int = int(os.getenv('API_PORT', 8078))
APP_WORKERS: int = int(os.getenv('APP_WORKERS', 4))
APP_LIMIT_CONCURRENCY: int = int(os.getenv('APP_LIMIT_CONCURRENCY', 1000))
APP_LOG_LEVEL: str = os.getenv('APP_LOG_LEVEL', 'info')
# the json key in request and response data will be converted to camelCase
IS_CAMEL_CASE: bool = os.getenv('IS_CAMEL_CASE', True)
# --------------------------- data dir----------------------------
DATA_DIR: str = os.getenv('DATA_DIR', './data')
EXPORT_DIR: str = os.path.join(DATA_DIR, 'export')
UPLOAD_FOLDER: str = os.path.join(DATA_DIR, 'uploads')
IMAGE_UPLOAD_FOLDER: str = os.path.join(DATA_DIR, 'uploads/image')
ATTACHMENT_UPLOAD_FOLDER: str = os.path.join(DATA_DIR, 'uploads/attachment')
# ---------------------------postgres CONFIG----------------------------
POSTGRES_HOST: str = os.getenv('POSTGRES_HOST')
POSTGRES_PORT: int = int(os.getenv('POSTGRES_PORT', 5432))
POSTGRES_DB: str = os.getenv('POSTGRES_DB', 'doc_assistant')
POSTGRES_USER: str = os.getenv('POSTGRES_USER', 'doc_assistant')
POSTGRES_PASSWORD: str = os.getenv('POSTGRES_PASSWORD', 'doc_assistant')
# ---------------------------EPK CONFIG----------------------------
APPROVAL_URL: str = os.getenv('APPROVAL_URL', '')
MAINTENANCE_URL: str = os.getenv('MAINTENANCE_URL', '')
INVOKE_URL: str = os.getenv('INVOKE_URL', '')
DOC_PERMISSIONS_URL: str = os.getenv('DOC_PERMISSIONS_URL', '')
TAG_PERMISSIONS_URL: str = os.getenv('TAG_PERMISSIONS_URL', '')
DEPARTMENT_URL: str = os.getenv('DEPARTMENT_URL', '')
STAFF_URL: str = os.getenv('STAFF_URL', '')
GET_USER_INFO_URL: str = os.getenv('GET_USER_INFO_URL', '')
GET_QUOTE_URL: str = os.getenv('GET_QUOTE_URL', '')
