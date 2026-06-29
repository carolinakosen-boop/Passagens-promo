---
name: testing-carteira-cs
description: Test the Carteira CS dashboard end-to-end. Use when verifying dashboard UI, data accuracy, filters, and tab navigation after updates.
---

# Testing Carteira CS Dashboard

## Overview
The Carteira CS dashboard is a static HTML+JS+Chart.js multi-page dashboard deployed via Devin Apps. It displays client management data extracted from Google Sheets (XLSX export).

## Prerequisites
- Dashboard deployed at a Devin Apps URL (e.g. `carteira-cs-*.devinapps.com`)
- No authentication required — public static site

## Devin Secrets Needed
None — the dashboard is a public static site with no auth.

## Test Approach
Use browser-based GUI testing with screen recording. The dashboard is client-side rendered, so all data is embedded in the HTML.

## Key Test Areas

### 1. Tab Navigation
- Click each tab in the nav bar and verify:
  - Active tab gets blue highlight (underline + text color)
  - Previous tab loses highlight
  - Page content area changes (not blank)
  - Default active tab on load is "Visao Geral"

### 2. KPI Cards (Visao Geral)
- Verify all KPI card values match the extracted data.json
- Key values to check: total clients, meta contratos, retencao %, onboarding, ongoing, lost count, foco count
- The DOM output from the browser tool provides exact text content for verification

### 3. Specialist Performance (Desempenho)
- Verify each specialist card shows correct badge (ONBOARDING/ONGOING)
- Check: clientes, meta, ativos, % contratos, resultado final

### 4. Table Filters (Todos Clientes, Pipeline Diario)
- Click filter buttons and verify:
  - Table rows reduce to expected count
  - Every visible row matches the filter criteria (check Carteira or Status column)
  - Active filter button is highlighted
- The DOM output includes both onscreen and offscreen rows, making it easy to verify all rows

### 5. Lost Clients (Churn & Lost)
- Verify total count in section title
- Check first row data matches expected values
- Verify motivo breakdown cards sum to total

## Common Issues

### Template Variable Bug
Watch for literal `${...}` text appearing in the rendered page. This indicates a JS template literal used single quotes instead of backticks. The dashboard builds HTML via string concatenation in `<script>` tags — lines using `${variable}` interpolation MUST use backtick-delimited strings. Check both the source HTML and the browser-rendered DOM.

### Devin Apps Deployment Caching
After pushing a fix, the Devin Apps static site deployment may serve a cached version for some time. To verify fixes immediately:
1. Start a local HTTP server: `cd carteira-cs && python3 -m http.server 8080`
2. **Important:** If the server was started before the fix, restart it — Python's HTTP server may cache files.
3. Use a cache-busting URL parameter: `http://localhost:8080/?nocache=1`
4. Verify the fix via localhost before waiting for the deployed site to update.
5. To update the deployed site, re-deploy via the `deploy` tool with `command="frontend"`.

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
- When verifying a specific bugfix, always compare before/after screenshots side by side
