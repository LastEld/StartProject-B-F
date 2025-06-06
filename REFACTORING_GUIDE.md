# Backend Refactoring Guide

This document outlines areas for improvement in the backend codebase (`app/`) focusing on DRY, SOLID, separation of concerns, validation, and error handling.

## 1. DRY (Don't Repeat Yourself)

*   **Objective:** Reduce code duplication to improve maintainability and reduce the chance of inconsistencies.
*   **Areas:**
    *   **Generic Query Helpers:**
        *   Create utility functions or a base CRUD class with methods for common filtering logic (e.g., `by_status`, `by_tags`, `is_not_deleted`, `is_archived_or_not`).
        *   **Files to Review:** `app/crud/project.py`, `app/crud/task.py`, `app/crud/template.py`.
    *   **Centralized Authorization Logic:**
        *   Develop reusable FastAPI dependency functions for common authorization patterns (e.g., `get_project_or_404_for_user`, `require_superuser`).
        *   **Files to Review:** `app/api/*.py`.
    *   **Custom Field Update Pattern:**
        *   Ensure the `custom_fields_dict = data_update.custom_fields.copy()` pattern (or a more robust abstraction) is used consistently for updating JSONB dictionary fields to ensure SQLAlchemy detects changes.
        *   **Files to Review:** `app/crud/*.py` (where models have `custom_fields`).
    *   **Test Fixture Abstraction:**
        *   Explore creating base fixture factories or helper functions to reduce boilerplate in setting up test data sets (e.g., for `project_set`, `task_set`).
        *   **Files to Review:** `app/tests/crud/*.py`, `app/tests/api/*.py`.

## 2. SOLID Principles Adherence

*   **Objective:** Ensure code is robust, maintainable, and flexible.
*   **Areas:**
    *   **SRP in API Layer:**
        *   Move complex filtering logic or business rule enforcement from API endpoint functions to the CRUD layer or a new service layer. API endpoints should primarily handle request/response and auth.
        *   **Files to Review:** `app/api/*.py`.
    *   **OCP for Filtering:**
        *   Consider a more generic mechanism for API filter parameters (e.g., a filter model passed to CRUD) to make adding new filterable fields easier.
        *   **Files to Review:** `app/api/*.py`, `app/crud/*.py`.

## 3. Separation of Concerns

*   **Objective:** Maintain clear boundaries between different parts of the application.
*   **Areas:**
    *   **Thin API Controllers:** Reinforce the role of API controllers as thin layers, delegating most work. (Related to SRP above).
    *   **Validation Strategy:** Define a clear hierarchy/location for different types of validation:
        *   Pydantic: Type, format, presence.
        *   Service/CRUD Layer: Business rule validation, existence checks (before action), inter-field dependencies.
        *   API Layer: Primarily auth-related checks or very high-level request validity.

## 4. Validation and Custom Error Handling

*   **Objective:** Provide clear, consistent, and robust validation and error feedback.
*   **Areas:**
    *   **Standardize Custom Field Validation:**
        *   Ensure a consistent approach to validating the *contents* of `custom_fields` against their schema definitions, especially during creation and updates.
        *   **Files to Review:** `app/crud/*.py`.
    *   **Pre-computation Validation:**
        *   Where possible, perform validations *before* expensive operations or database queries.
    *   **Error Granularity:**
        *   Review existing custom exceptions. Ensure they are specific enough and used consistently.
        *   Consider if new custom exceptions are needed for unhandled business rule violations.
    *   **Error Response Consistency (API):**
        *   Already good due to FastAPI, but ensure any manually crafted HTTPExceptions follow the same format.

## 5. Specific Code Hotspots & Patterns

*   **Tag Filtering:** Standardize on `cast(Model.tags, SQLString).like(f"%{tag}%")` for JSON array string searches or evaluate more robust JSON query methods if the database supports them well.
*   **SQLAlchemy Change Detection for JSON:** Consistently use patterns like dictionary copying for mutable JSON fields to ensure changes are tracked.
*   **API Query Parameter Handling:** Refactor long lists of optional query parameters in API functions into Pydantic models or dictionaries for cleaner passing to CRUD/service layers.

## Next Steps (Refactoring Process)

1.  **Prioritize:** Focus on the most impactful changes first (e.g., DRYing up query logic and authorization).
2.  **Incremental Changes:** Apply refactorings incrementally, model by model or concern by concern.
3.  **Testing:** Ensure existing tests pass after each refactoring step. Augment tests if current coverage is insufficient for the refactored code.
4.  **Code Review:** Conduct code reviews for refactored sections.
