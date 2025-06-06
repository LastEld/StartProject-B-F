#app/crud/plugin.py
from sqlalchemy.orm import Session, aliased
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_ # For OR conditions in SQLAlchemy
from app.models.plugin import Plugin
from app.models.user import User as UserModel # Import User model for type hinting
from app.core.exceptions import PluginNotFoundError, PluginValidationError, ForbiddenError
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
import json
import logging

logger = logging.getLogger("DevOS.Plugins")

def create_plugin(db: Session, data: Dict, author_id: int) -> Plugin:
    """
    Создаёт новый плагин.
    """
    name = data.get("name", "").strip()
    if not name:
        raise PluginValidationError("Plugin name is required.")
    if get_plugin_by_name(db, name):
        raise PluginValidationError(f"Plugin with name '{name}' already exists.")

    config_json_data = data.get("config_json", {})
    if isinstance(config_json_data, str):
        try:
            config_dict = json.loads(config_json_data)
        except json.JSONDecodeError:
            raise PluginValidationError("Invalid JSON format for configuration.")
    elif isinstance(config_json_data, dict):
        config_dict = config_json_data
    else:
        raise PluginValidationError("Configuration must be a valid JSON string or a dictionary.")

    plugin = Plugin(
        name=name,
        description=data.get("description", "").strip(),
        config_json=config_dict,
        is_active=bool(data.get("is_active", True)), # Default from schema if not provided
        version=data.get("version"),
        author_id=author_id, # Set author_id
        subscription_level=data.get("subscription_level"),
        is_private=bool(data.get("is_private", False)), # Default from schema if not provided
        ui_component=data.get("ui_component"),
        tags=data.get("tags", []),
    )
    try:
        db.add(plugin)
        db.commit()
        db.refresh(plugin)
        logger.info(f"Plugin '{plugin.name}' created with ID {plugin.id}.")
        return plugin
    except IntegrityError:
        db.rollback()
        raise PluginValidationError(f"Database error: Could not create plugin '{name}'. It might violate a database constraint.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating plugin {name}: {e}")
        raise PluginValidationError(f"Error: {e}")

def get_plugin(db: Session, plugin_id: int, current_user: UserModel, include_deleted: bool = False) -> Plugin:
    """
    Получить плагин по ID, проверяя права доступа.
    """
    query = db.query(Plugin).filter(Plugin.id == plugin_id)
    if not include_deleted:
        query = query.filter(Plugin.is_deleted == False)

    plugin = query.first()

    if not plugin:
        raise PluginNotFoundError(f"Plugin with ID {plugin_id} not found{' (or is deleted)' if not include_deleted else ''}.")

    if plugin.is_private and not current_user.is_superuser and plugin.author_id != current_user.id:
        raise ForbiddenError(f"Not authorized to access plugin with ID {plugin_id}.")
        # Or raise PluginNotFoundError to obscure existence, though 403 is more accurate if ID is known.

    return plugin

def get_plugin_by_name(db: Session, name: str, current_user: Optional[UserModel] = None, include_deleted: bool = False) -> Optional[Plugin]:
    """
    Получить плагин по имени, опционально проверяя права доступа.
    Если current_user предоставлен, проверяет доступ для приватных плагинов.
    """
    query = db.query(Plugin).filter(Plugin.name == name)
    if not include_deleted:
        query = query.filter(Plugin.is_deleted == False)

    plugin = query.first()

    if plugin and current_user and plugin.is_private and not current_user.is_superuser and plugin.author_id != current_user.id:
        # This function is used internally by create_plugin before user context might be fully applied for auth,
        # so raising ForbiddenError might be too early. For get_by_name, it's better to return None if no access.
        # Or, ensure create_plugin uses a different way to check name uniqueness if this is an issue.
        # For now, let's assume this function is also for direct API use where current_user is available.
        raise ForbiddenError(f"Not authorized to access plugin with name '{name}'.")
        # Returning None might be safer to obscure existence based on access.
        # return None

    return plugin


def get_all_plugins(
    db: Session,
    current_user: UserModel,
    filters: Optional[Dict[str, Any]] = None,
    include_deleted: bool = False,
    search: Optional[str] = None
) -> List[Plugin]:
    """
    Получить список плагинов с фильтрами и правами доступа.
    """
    query = db.query(Plugin)
    filters = filters or {}

    # Handle soft-delete visibility
    if not include_deleted:
        query = query.filter(Plugin.is_deleted == False)

    # Privacy filtering based on user
    if not current_user.is_superuser:
        # If user wants to see only their private plugins
        if filters.get("is_private") is True:
            query = query.filter(Plugin.is_private == True, Plugin.author_id == current_user.id)
        # If user wants to see only public plugins
        elif filters.get("is_private") is False:
            query = query.filter(Plugin.is_private == False)
        # Default: user sees public plugins and their own private plugins
        else:
            query = query.filter(
                or_(
                    Plugin.is_private == False,
                    Plugin.author_id == current_user.id
                )
            )
    elif "is_private" in filters: # Superuser can still filter by is_private if they want
        query = query.filter(Plugin.is_private == filters["is_private"])

    # Other filters
    if "is_active" in filters:
        query = query.filter(Plugin.is_active == filters["is_active"])
    if "subscription_level" in filters:
        query = query.filter(Plugin.subscription_level == filters["subscription_level"])
    if "tag" in filters and filters["tag"]:
        from sqlalchemy import cast, String as SQLString # Keep import local if only used here
        tag_to_find = filters["tag"]
        # Ensure tag is searched as a whole word/element in JSON array if possible
        # For basic JSON array of strings: [{"tags": ["foo", "bar"]}]
        # This basic like search might find "bar" in "foobar". For exact match in JSON array,
        # specific DB functions are better (e.g., jsonb_exists, json_contains).
        # Sticking to compatible LIKE for now.
        query = query.filter(cast(Plugin.tags, SQLString).like(f'%"{tag_to_find}"%'))

    # Search filter for name and description
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            or_(
                Plugin.name.ilike(search_term),
                Plugin.description.ilike(search_term)
            )
        )

    return query.order_by(Plugin.name).all()

def update_plugin(db: Session, plugin_id: int, data: Dict, current_user: UserModel) -> Plugin:
    """
    Обновляет поля плагина. Доступ разрешен автору или суперюзеру.
    Не позволяет менять author_id.
    """
    plugin = get_plugin(db, plugin_id, current_user=current_user) # get_plugin handles initial access check

    if not current_user.is_superuser and plugin.author_id != current_user.id:
        raise ForbiddenError("Not authorized to update this plugin.")

    if plugin.is_deleted:
        raise PluginNotFoundError(f"Plugin with ID {plugin_id} is deleted and cannot be updated. Please restore it first.")

    if "name" in data:
        new_name = data["name"].strip()
        if not new_name:
            raise PluginValidationError("Plugin name cannot be empty.")
        if new_name != plugin.name:
            existing_plugin = get_plugin_by_name(db, new_name)
            if existing_plugin and existing_plugin.id != plugin_id:
                raise PluginValidationError(f"Plugin with name '{new_name}' already exists.")
        plugin.name = new_name

    if "description" in data:
        plugin.description = data["description"].strip()

    if "config_json" in data:
        config_json_data = data["config_json"]
        if isinstance(config_json_data, str):
            try:
                plugin.config_json = json.loads(config_json_data)
            except json.JSONDecodeError:
                raise PluginValidationError("Invalid JSON format for configuration.")
        elif isinstance(config_json_data, dict):
            plugin.config_json = config_json_data
        else:
            raise PluginValidationError("Configuration must be a valid JSON string or a dictionary.")

    if "is_active" in data:
        plugin.is_active = bool(data["is_active"])

    if "version" in data:
        plugin.version = data["version"]

    # author_id should not be changed via this generic update.
    # if "author_id" in data and current_user.is_superuser: # Potentially allow superuser to change author
    #     plugin.author_id = data["author_id"]

    if "subscription_level" in data:
        plugin.subscription_level = data["subscription_level"]

    if "is_private" in data:
        plugin.is_private = bool(data["is_private"])

    if "ui_component" in data:
        plugin.ui_component = data["ui_component"]

    if "tags" in data:
        plugin.tags = data["tags"]

    try:
        db.commit()
        db.refresh(plugin)
        logger.info(f"Plugin '{plugin.name}' (ID: {plugin.id}) updated.")
        return plugin
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating plugin {plugin.name}: {e}")
        raise PluginValidationError(f"Error updating plugin: {str(e)}")

def soft_delete_plugin(db: Session, plugin_id: int) -> Plugin:
    """
    Помечает плагин как удалённый (soft-delete).
    """
    plugin = get_plugin(db, plugin_id, current_user=current_user, include_deleted=True) # Access check

    if not current_user.is_superuser and plugin.author_id != current_user.id:
        raise ForbiddenError("Not authorized to delete this plugin.")

    if plugin.is_deleted:
        logger.info(f"Plugin '{plugin.name}' (ID: {plugin.id}) is already soft-deleted.")
        return plugin # Or raise error if trying to delete again

    plugin.is_deleted = True
    plugin.deleted_at = datetime.now(timezone.utc)
    plugin.is_active = False # Deactivate on soft delete
    try:
        db.commit()
        db.refresh(plugin)
        logger.info(f"Plugin '{plugin.name}' (ID: {plugin.id}) soft-deleted.")
        return plugin
    except Exception as e:
        db.rollback()
        logger.error(f"Error soft-deleting plugin ID {plugin_id}: {e}")
        raise PluginValidationError(f"Error during soft delete: {str(e)}")

def restore_plugin(db: Session, plugin_id: int) -> Plugin:
    """
    Восстанавливает soft-deleted плагин.
    """
    plugin = get_plugin(db, plugin_id, current_user=current_user, include_deleted=True) # Access check

    if not current_user.is_superuser and plugin.author_id != current_user.id:
        raise ForbiddenError("Not authorized to restore this plugin.")

    if not plugin.is_deleted:
        raise PluginValidationError(f"Plugin '{plugin.name}' (ID: {plugin.id}) is not deleted. No action taken.")

    plugin.is_deleted = False
    plugin.deleted_at = None
    # Consider if plugin should be restored to is_active = True or its previous state.
    # For now, it remains inactive unless explicitly activated.
    try:
        db.commit()
        db.refresh(plugin)
        logger.info(f"Plugin '{plugin.name}' (ID: {plugin.id}) restored.")
        return plugin
    except Exception as e:
        db.rollback()
        logger.error(f"Error restoring plugin ID {plugin_id}: {e}")
        raise PluginValidationError(f"Error during restore: {str(e)}")

def hard_delete_plugin(db: Session, plugin_id: int) -> bool:
    """
    Физически удаляет плагин (hard-delete).
    """
    plugin = get_plugin(db, plugin_id, current_user=current_user, include_deleted=True) # Access check

    if not current_user.is_superuser: # Only superuser can hard delete
        raise ForbiddenError("Not authorized to hard-delete this plugin.")

    try:
        db.delete(plugin)
        db.commit()
        logger.info(f"Plugin '{plugin.name}' (ID: {plugin.id}) hard-deleted from database.")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error hard-deleting plugin ID {plugin_id}: {e}")
        raise PluginValidationError(f"Error during hard delete: {str(e)}")

def activate_plugin(db: Session, plugin_id: int, current_user: UserModel) -> Plugin:
    """
    Активирует плагин. Доступ автору или суперюзеру.
    """
    plugin = get_plugin(db, plugin_id, current_user=current_user, include_deleted=True) # Access check

    if not current_user.is_superuser and plugin.author_id != current_user.id:
        raise ForbiddenError("Not authorized to activate this plugin.")

    if plugin.is_deleted:
        raise PluginValidationError(f"Cannot activate a deleted plugin. Please restore '{plugin.name}' first.")
    if not plugin.is_active:
        plugin.is_active = True
        db.commit()
        db.refresh(plugin)
        logger.info(f"Plugin '{plugin.name}' activated.")
    return plugin

def deactivate_plugin(db: Session, plugin_id: int, current_user: UserModel) -> Plugin:
    """
    Деактивирует плагин. Доступ автору или суперюзеру.
    """
    plugin = get_plugin(db, plugin_id, current_user=current_user, include_deleted=False) # Access check, no need for include_deleted=True if only active can be deactivated

    if not current_user.is_superuser and plugin.author_id != current_user.id:
        raise ForbiddenError("Not authorized to deactivate this plugin.")

    if plugin.is_deleted: # Should ideally not happen if get_plugin is called with include_deleted=False
        logger.warning(f"Attempt to deactivate an already deleted plugin '{plugin.name}'. This should not happen if logic is correct.")
        raise PluginValidationError("Cannot deactivate a deleted plugin.")

    if plugin.is_active:
        plugin.is_active = False
        db.commit()
        db.refresh(plugin)
        logger.info(f"Plugin '{plugin.name}' deactivated.")
    return plugin

def get_active_plugins_summary(db: Session) -> str: # No user context needed if it's a global summary of public state
    """
    Возвращает строку-список активных плагинов (для UI/логов).
    """
    active_plugins = db.query(Plugin.name).filter(Plugin.is_active == True, Plugin.is_deleted == False).all()
    if not active_plugins:
        return "No plugins are currently active."
    return "Active plugins: " + ", ".join([name for (name,) in active_plugins]) + "."

def run_plugin_action(db: Session, plugin_name: str, action_name: str, project_context: dict, plugin_params: dict = None) -> str:
    """
    Заглушка для вызова экшена плагина (расширяй под реальную бизнес-логику).
    """
    # For run_plugin_action, the plugin must be fetched ensuring the user has rights to *use* it,
    # which might be different from *viewing* its details.
    # This example uses a simplified get_plugin_by_name without user context for action running,
    # assuming active non-private plugins are generally runnable.
    # A more robust implementation would pass current_user to get_plugin_by_name.
    plugin = get_plugin_by_name(db, plugin_name) # Potentially add current_user here if needed for access check
    if not plugin:
        raise PluginNotFoundError(f"Plugin '{plugin_name}' not found or not accessible.")

    if plugin.is_private: # Simplified check: if it's private, assume only owner or superuser can run (needs current_user)
        # This part requires current_user in get_plugin_by_name or a separate check here.
        # For now, this action might be too permissive for private plugins if current_user is not checked.
        logger.warning(f"Action run attempt on private plugin '{plugin_name}' without full user context check in run_plugin_action.")

    if not plugin.is_active:
        return f"Error: Plugin '{plugin_name}' is not active. Please activate it first."
    if not plugin.is_active:
        return f"Error: Plugin '{plugin_name}' is not active. Please activate it first."
    logger.info(f"Attempting to run action '{action_name}' from plugin '{plugin_name}' for project: {project_context.get('name')}")
    additional_params = plugin_params or {}
    if plugin_name == "EchoTest" and action_name == "echo":
        message_to_echo = additional_params.get("message", "No message provided for echo.")
        return f"Plugin '{plugin_name}' simulated echoing: '{message_to_echo}' for project '{project_context.get('name')}'."
    return f"Plugin '{plugin_name}' action '{action_name}' called (simulated). Params: {additional_params}. Project: '{project_context.get('name')}'."
