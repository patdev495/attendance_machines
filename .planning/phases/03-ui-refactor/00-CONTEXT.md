# Phase Context: UI Refactor

## Decisions captured on 2026-04-09

### UI Layout
- **Sidebar**: Implement a collapsible vertical sidebar for main navigation.
- **Vertical Tabs**: Move "Rawlog" and "Daily Summary" into this sidebar as vertical tabs.
- **Device Status**: Promote "Device Status" to a top-level tab in the sidebar, equal to Rawlog and Summary.
- **Main View Area**: Should expand when the sidebar is collapsed to maximize information display.

### Action Relocation
- **Rawlog View**:
  - Incorporate the "Sync Machine" functionality here.
- **Daily Summary View**:
  - Incorporate "Export Excel" (including mode selection) and "Sync Excel" buttons here.
- **Header**: Slim down the header, removing global actions but keeping language and branding.

### Technical Approach
- Use a `uiStore` (or update `attendanceStore`) to manage sidebar state and active view.
- Maintain existing routes but ensure sidebar correctly reflects the active route.
- Use CSS Flex/Grid for the sidebar layout.

## Out of Scope
- Changing the underlying data structures or API endpoints (unless strictly necessary for the UI move).
- Redesigning the employee management modal (keeping it as is for now).
