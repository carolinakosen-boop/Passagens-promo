---
name: testing-carteira-cs
description: Test the Carteira CS dashboard end-to-end. Use when verifying dashboard UI, data accuracy, filters, tab navigation, interactive charts, editable fields, notes, and backup/export after updates.
---

# Testing Carteira CS Dashboard

## Overview
The Carteira CS dashboard is a static HTML+JS+Chart.js multi-page dashboard deployed via Devin Apps. It displays client management data extracted from Google Sheets (XLSX export). The dashboard has 8 tabs and supports interactive features like clickable charts, editable fields, daily notes, and monthly backup/export.

## Prerequisites
- Dashboard deployed at a Devin Apps URL (e.g. `carteira-cs-*.devinapps.com`)
- No authentication required — public static site

## Devin Secrets Needed
None — the dashboard is a public static site with no auth.

## Test Approach
Use browser-based GUI testing with screen recording. The dashboard is client-side rendered — all data is embedded in `data.json` which is loaded by `index.html`. Interactive features use localStorage for persistence.

## Key Test Areas

### 1. Tab Navigation
- Click each tab in the nav bar and verify:
  - Active tab gets blue highlight (underline + text color)
  - Previous tab loses highlight
  - Page content area changes (not blank)
  - Default active tab on load is "Visao Geral"
- Tabs: Visao Geral, Desempenho, Churn & Lost, Pipeline Diario, Reunioes, Renovacoes, Todos Clientes, Backups

### 2. KPI Cards (Visao Geral)
- Verify all KPI card values match the extracted data.json
- Key values to check: total clients, meta contratos, retencao %, onboarding, ongoing, lost count, foco count
- The DOM output from the browser tool provides exact text content for verification

### 3. Clickable Charts (Visao Geral)
- **Status doughnut chart**: Click any segment to see modal with client names
  - Modal shows "Status — [status name] ([count])" with client list
  - Each client shows `dias_sem_contrato` + `carteira` details
  - Small segments (e.g. "Desconhecido" with 5 clients) may be hard to click — test larger segments first
- **Churn bar chart** ("Dias sem Contrato"): Click a bar to see clients in that range
  - Modal shows "Churn — [range] ([count])" with client names + dias + carteira
  - Scroll down the Visao Geral page to find this chart in the "Analise de Churn" section

### 4. Specialist Performance (Desempenho)
- Verify each specialist card shows correct badge (ONBOARDING/ONGOING)
- Check: clientes, meta, ativos, % contratos, resultado final

### 5. Clickable Lost Motivos (Churn & Lost)
- Click any motivo stat-box to see modal with client names for that motivo
- Modal shows "Lost — [motivo] ([count])" with client names + dias + consideracoes
- Verify counts match the stat-box numbers
- Also verify filter buttons below stat-boxes filter the table correctly

### 6. Pipeline Diario — Editable Fields
- **Status dropdown**: Each client row has a `<select>` for changing status
  - Options: Vai ativar, Tem promessas, Nao vai ativar, Em onboarding, Sem status
  - Changes persist via localStorage (`pipeline_statuses` key)
- **Editable contracts**: Each row has `<input type="number">` for contract count
  - Change value, blur/click elsewhere, reload page — value should persist
  - Stored in localStorage (`pipeline_contratos` key)
- **Consultant filter**: "Filtrar por Consultor" with Andressa/Emanuella buttons
- **Status filter**: Combined with consultant filter for multi-filter functionality

### 7. Pipeline Diario — Notes System
- **Inline notes**: Type in annotation input, click "Salvar" — note appears inline with date/time
  - Date format: `DD/MM/YYYY HH:MM` (pt-BR locale)
  - Recent 2 notes shown inline; "+N mais..." if more exist
- **Full-page history**: Click "Ver historico completo" to open full-screen overlay
  - Header shows "Anotacoes — [client name]"
  - "Voltar" button at top-right closes overlay
  - Textarea + "Salvar anotacao" button for adding notes from the page
  - Notes displayed newest-first with date and text
  - Stored in localStorage (`pipeline_notes` key)

### 8. Backups & CSV Export
- Navigate to "Backups" tab
- Verify page shows previous month backup card (e.g. "Maio") with "Abrir planilha" link
- Current month card (e.g. "Junho 2025 (Atual)") with "Em andamento" pill
- **CSV export**: Click "Exportar Dados Atuais (CSV)" — downloads file named `carteira_cs_[Month]_[Year].csv`
- **Save & reset**: "Salvar Backup do Mes & Zerar Contas" button — avoid clicking during testing unless specifically testing reset functionality, as it zeros out localStorage data

### 9. Table Filters (Todos Clientes, Pipeline Diario)
- Click filter buttons and verify:
  - Table rows reduce to expected count
  - Every visible row matches the filter criteria (check Carteira or Status column)
  - Active filter button is highlighted
- The DOM output includes both onscreen and offscreen rows, making it easy to verify all rows

## Common Issues

### Template Variable Bug
Watch for literal `${...}` text appearing in the HTML. This indicates a template variable was not properly rendered during HTML generation. The extraction script uses string interpolation to build HTML, and missing or misplaced backticks can cause this.

### localStorage Persistence
- Editable fields (status, contracts, notes) use localStorage for persistence
- To verify persistence: change a value, reload (F5), check the value is still changed
- Important: after changing an input value, click elsewhere (blur the field) before reloading — the `onchange` event fires on blur, not on every keystroke
- localStorage keys: `pipeline_statuses`, `pipeline_contratos`, `pipeline_notes`, `carteira_backups`

### Small Chart Segments
Doughnut chart segments with small values (e.g. 5 out of 230 clients) produce very thin arcs that are hard to click. If testing a specific small segment, try larger segments first to confirm the onClick handler works, then attempt the small one. The functionality is the same for all segments.

### Data Accuracy
When the spreadsheet changes (new month), re-run `extract_data.py` to regenerate `data.json`, then rebuild `index.html`. Key verification steps:
1. Run `python3 extract_data.py` and check output counts
2. Compare data.json values against the spreadsheet
3. Verify the HTML renders the correct values

### Google Sheets Export
- Use XLSX export URL: `https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx`
- The spreadsheet might have multiple sheets — identify the correct ones by name patterns (e.g. "Meta Geral 062025", "Visao Geral da Carteira")
- Sheet names may change month to month

## Testing Tips
- Use the browser tool's DOM output to verify exact text values without needing to scroll
- The DOM includes `offscreen` attribute on rows not currently visible, but they are still in the filtered table
- For row counting, use the DOM data rather than trying to count visually
- Chart.js canvases render as `<canvas>` elements — verify they exist but visual content requires screenshots
- Record the full test session for user proof
- Modals are created dynamically via `showModal()` — they appear as overlays on the page and can be closed by clicking the X button or clicking outside
- Full-page overlays (notes page) use fixed positioning with z-index:300 — they cover the entire viewport
- CSV export uses Blob + URL.createObjectURL — the browser download notification confirms successful export
- Client name keys are sanitized via `.replace(/[^a-zA-Z0-9]/g,'_')` for localStorage storage