// src/app/utils/formatters.ts

// Форматирование даты (YYYY-MM-DD -> DD.MM.YYYY)
export function formatDate(dateStr?: string | Date, locale = "en-GB"): string {
  if (!dateStr) return "";
  const d = typeof dateStr === "string" ? new Date(dateStr) : dateStr;
  if (isNaN(d.getTime())) return "";
  return d.toLocaleDateString(locale); // формат DD/MM/YYYY или по locale
}

// Форматирование имени: "Kamal Elkateb" -> "K. Elkateb"
export function formatShortName(name?: string): string {
  if (!name) return "";
  const [first, ...rest] = name.split(" ");
  if (!first) return name;
  return first[0].toUpperCase() + ". " + rest.join(" ");
}

// Преобразует snake_case/status в человекочитаемый вид
export function formatStatus(status?: string): string {
  if (!status) return "";
  return status
    .replace(/_/g, " ")
    .replace(/\b\w/g, (l) => l.toUpperCase());
}

// Форматирование приоритета задачи (число или строка)
export function formatPriority(priority?: string | number): string {
  if (priority === undefined || priority === null) return "";
  if (typeof priority === "number") {
    if (priority >= 5) return "Highest";
    if (priority === 4) return "High";
    if (priority === 3) return "Medium";
    if (priority === 2) return "Low";
    if (priority <= 1) return "Lowest";
    return String(priority);
  }
  switch (priority) {
    case "low":
      return "Low";
    case "medium":
      return "Medium";
    case "high":
      return "High";
    default:
      return priority;
  }
}
