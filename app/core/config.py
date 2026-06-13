from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Класс настроек приложения.

    Наследуется от BaseSettings из pydantic-settings,
    что позволяет автоматически загружать значения из переменных окружения
    или из файла .env.

    Все поля класса становятся конфигурационными параметрами приложения.
    """

    model_config = SettingsConfigDict(env_file=".env")

    PROJECT_NAME: str = "To-Do App"
    DATABASE_URL: str # Значение обязательно должно быть задано в переменных окружения или в файле .env

    SECRET_KEY: str # Секретный ключ для подписи JWT-токенов
    ALGORITHM: str = "HS256" # Алгоритм шифрования/подписи JWT-токенов

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30 # Время жизни access-токена в минутах
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080 # Время жизни refresh-токена в минутах
    
    OPENROUTER_API_KEY: str | None = None # API ключ к openrouter ai
    DEEPSEEK_MODEL: str | None = None # модель

    YANDEX_DISK_TOKEN: str | None = None # API ключ для доступа к yandex.disk

settings = Settings()