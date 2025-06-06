# app/core/exceptions.py
# app/core/exceptions.py


# app/core/exceptions.py

class BaseAppException(Exception):
    """Базовый класс для всех кастомных исключений приложения."""
    def __init__(self, message: str = "App exception"):
        super().__init__(message)

# ==== Валидация/создание ====

class ValidationError(BaseAppException):
    """Общая ошибка валидации."""
    def __init__(self, message: str = "Validation error"):
        super().__init__(message)

class ProjectValidationError(ValidationError):
    """Ошибка валидации проекта."""
    def __init__(self, message: str = "Project validation error"):
        super().__init__(message)

class TaskValidationError(ValidationError):
    """Ошибка валидации задачи."""
    def __init__(self, message: str = "Task validation error"):
        super().__init__(message)

class DevLogValidationError(ValidationError):
    """Ошибка валидации записи DevLog."""
    def __init__(self, message: str = "DevLog validation error"):
        super().__init__(message)

class PluginValidationError(ValidationError):
    """Ошибка валидации плагина."""
    def __init__(self, message: str = "Plugin validation error"):
        super().__init__(message)

class TemplateValidationError(ValidationError):
    """Ошибка валидации шаблона."""
    def __init__(self, message: str = "Template validation error"):
        super().__init__(message)

# ==== NotFound ====

class NotFoundError(BaseAppException):
    """Ошибка отсутствия ресурса."""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message)

class ProjectNotFound(NotFoundError):
    """Ошибка: проект не найден."""
    def __init__(self, message: str = "Project not found"):
        super().__init__(message)

class TaskNotFound(NotFoundError):
    """Ошибка: задача не найдена."""
    def __init__(self, message: str = "Task not found"):
        super().__init__(message)

class DevLogNotFound(NotFoundError):
    """Ошибка: запись DevLog не найдена."""
    def __init__(self, message: str = "DevLog entry not found"):
        super().__init__(message)

class PluginNotFoundError(NotFoundError):
    """Ошибка: плагин не найден."""
    def __init__(self, message: str = "Plugin not found"):
        super().__init__(message)

class SpecificTemplateNotFoundError(NotFoundError):
    """Ошибка: шаблон не найден (специфичная)."""
    def __init__(self, detail: str = "Template not found", status_code: int = 404): 
        super().__init__(message=detail) 
        self.status_code = status_code 
        self.detail = detail

# ==== Дубликаты ====

class DuplicateProjectName(BaseAppException):
    """Ошибка: проект или шаблон с таким именем уже существует."""
    def __init__(self, message: str = "Duplicate project name"):
        super().__init__(message)

# ==== Авторизация ====

class AuthError(BaseAppException):
    """Ошибка аутентификации или авторизации."""
    def __init__(self, message: str = "Authentication or authorization error"):
        super().__init__(message)

# ==== Teams ====

class TeamError(BaseAppException):
    """Ошибка, связанная с командами."""
    def __init__(self, message: str = "Team error"):
        super().__init__(message)

# ==== Settings ====

class SettingValidationError(ValidationError):
    """Ошибка валидации настройки."""
    def __init__(self, message: str = "Setting validation error"):
        super().__init__(message)

# ==== Добавляй другие категории по необходимости ====
