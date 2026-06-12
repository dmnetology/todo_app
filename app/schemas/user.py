from pydantic import BaseModel, EmailStr, Field, field_validator
import re


class UserCreate(BaseModel):
    """
    Pydantic-схема для регистрации пользователя.

    Эта схема описывает данные, которые клиент должен отправить
    при создании нового пользователя.

    Эта схема нужна для:
    - валидации входящих данных;
    - ограничения длины строк;
    - автоматической генерации OpenAPI-документации;
    - удобной передачи данных внутри приложения.
    """

    first_name: str = Field(min_length=2, max_length=100)
    last_name: str = Field(min_length=2, max_length=100)
    login: EmailStr
    password: str = Field(min_length=6, max_length=100)

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value:
            raise ValueError("Имя не может быть пустым")
        if value[0].isdigit():
            raise ValueError("Имя не может начинаться с цифры")
        if not value.isalpha():
            raise ValueError("Имя должно содержать только буквы")
        return value.capitalize()
    
    @field_validator("login")
    @classmethod
    def validate_login(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError("Логин слишком короткий")
        if " " in v:
            raise ValueError("Логин не может содержать пробелы")
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("Логин может содержать только буквы, цифры и знак подчеркивания")
        return v.lower()

    @field_validator("password")
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Пароль должен быть длинной минимум 8 знаков")

        if not re.search(r"\d", v):
            raise ValueError("Пароль должен содержать хотя бы одну цифру")

        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must содержать заглавные буквы")

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Пароль должен содержать спецсимволы")

        return v

class UserRead(BaseModel):
    """
    Pydantic-схема ответа с данными пользователя.

    Эта схема используется, когда приложение возвращает данные пользователя
    клиенту.

    Здесь нет поля password или hashed_password.
    Это сделано специально, чтобы не отдавать пароль или его хэш наружу
    через API-ответ.
    """

    id: int
    first_name: str
    last_name: str
    login: str

    model_config = {
        "from_attributes": True,
    }