# Phase Context: Phase 7 — i18n Foundation & Layout

## Decisions

- **Language Selector**: Keep the current standard `<select>` dropdown in `AppHeader.vue`. No UI upgrade needed.
- **Default Language**: For new users, the default language must be English (`en`).
- **Persistence**: Use `localStorage` to remember the user's language choice.
- **Dictionary Organization**: Organize translation keys by feature/function. Layout-specific strings (Header/Sidebar) can reside in `nav` or `layout` sections.
- **Fallback Policy**: Fallback to English (`en`) if a translation is missing in the current language.

## Scope Clarification

- **AppHeader & AppSidebar**: Remove all hardcoded strings (Nav labels, status banner messages).
- **Core Components**: Update `PaginationBar`, `ConfirmModal`, and `ToastNotification` to use i18n.
- **i18n Initialization**: Update `i18n/index.js` to prioritize 'en' and handle first-visit default logic.

## Specifics

- The user specifically requested that English be the default for first-time visitors.
- Translation keys for progress banners (Syncing, Exporting) should be moved to their respective feature namespaces in JSON if applicable, or a shared `global` namespace if they appear across layout.
