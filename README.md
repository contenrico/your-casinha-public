# Your Casinha – Admin Dashboard

Streamlit admin tool for the Airbnb property at Rua de Marvila, Lisbon.

## Features

- **Register Guests** – submits guest check-in forms to the Portuguese SIBA/SEF portal.
- **Issue Invoices** – issues a *Fatura-Recibo* on the Portuguese IRS portal from Airbnb payout emails.

## Running locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

For local development, create `.streamlit/secrets.toml` (already git-ignored):

```toml
password = "your-admin-password"

SEF_UH            = "..."
SEF_ESTABELECIMENTO = "..."
SEF_CHAVE         = "..."
PDF_NIF           = "..."
PDF_SENHA         = "..."
```

AWS credentials are picked up from the environment / `~/.aws/credentials` as usual.

## Project structure

```
app.py                      # Entry point: auth gate + st.navigation
app_pages/
  home.py                   # Welcome page
  register_guests.py        # SEF guest registration UI
  issue_invoices.py         # Invoice issuance UI
src/casinha/
  config.py                 # All constants and secret accessors
  auth.py                   # Password gate helpers
  domain/
    columns.py              # DataFrame column-name constants
  services/
    storage.py              # S3 helpers
    google_sheets.py        # Fetch guest form from Google Sheets → S3
    gmail.py                # Fetch Airbnb payout emails from Gmail → S3
    transforms.py           # Pure pandas transformations (no I/O)
    records.py              # Cumulative guest records (records.json in S3)
  automation/
    driver.py               # Chrome WebDriver factory + wait helpers
    sef.py                  # SIBA/SEF portal automation
    invoices.py             # IRS invoice portal automation
parameters/
  countries_mapping.json
  nationalities_mapping.json
```

## Adding a new page

1. Create `app_pages/my_new_page.py`.
2. Register it in `app.py`:
   ```python
   new_page = st.Page("app_pages/my_new_page.py", title="My New Page", icon="✨")
   nav = st.navigation([home_page, register_page, invoices_page, new_page])
   ```
That's it – auth is handled automatically by the `app.py` gate.

## Required secrets

| Key | Description |
|-----|-------------|
| `password` | Dashboard login password |
| `SEF_UH` | SEF unit/hotel code |
| `SEF_ESTABELECIMENTO` | SEF establishment code |
| `SEF_CHAVE` | SEF activation key |
| `PDF_NIF` | NIF for the IRS invoice portal login |
| `PDF_SENHA` | Password for the IRS invoice portal login |
