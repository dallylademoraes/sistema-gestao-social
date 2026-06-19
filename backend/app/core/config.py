from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    FIRST_ADMIN_EMAIL: str | None = None
    FIRST_ADMIN_PASSWORD: str | None = None
    S3_ENDPOINT_URL: str | None = None
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    # Recommended default for shorter-lived access tokens to reduce risk window
    # for stolen tokens when using browser-based sessions.
    # Lowered to 60 minutes by default as per security guidance.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_LOCK_MINUTES: int = 15
    LOGIN_RATE_LIMIT_WINDOW_MINUTES: int = 10
    UPLOAD_MAX_BYTES: int = 10485760
    STORAGE_PROVIDER: str = "local"
    CADASTROS_STORAGE: str = "database"
    GOOGLE_APPS_SCRIPT_URL: str | None = None
    GOOGLE_APPS_SCRIPT_TOKEN: str | None = None
    S3_BUCKET_NAME: str | None = None
    S3_REGION: str | None = None
    S3_VERIFY_SSL: bool = True
    B2_APPLICATION_KEY_ID: str | None = None
    B2_APPLICATION_KEY: str | None = None
    BLOB_CONNECTION_STRING: str | None = None
    BLOB_CONTAINER_NAME: str | None = None
    BREVO_SMTP_LOGIN: str | None = None
    BREVO_SMTP_KEY: str | None = None
    BREVO_API_KEY: str | None = None     
    BREVO_FROM_EMAIL: str | None = None
    BREVO_FROM_NAME: str | None = None
    RETURN_PASSWORD_RESET_TOKEN_IN_RESPONSE: bool = False

    class Config:
        env_file = ".env"

    @property
    def cors_origins_list(self) -> list[str]:
        origins = [
            origin.strip().rstrip("/")
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]
        for origin in (
            self.FRONTEND_URL,
            "https://sistema-gestao-social.vercel.app",
        ):
            clean_origin = origin.strip().rstrip("/") if origin else ""
            if clean_origin and clean_origin not in origins:
                origins.append(clean_origin)
        return origins


settings = Settings()