# Private SharePoint Setup — Microsoft Graph

This dashboard supports three Shop Visit source types in both **APU Shop Visit** and **Engine Shop Visit** rooms:

- Google Sheets URL
- SharePoint / OneDrive Excel URL
- Local Excel / CSV path (automatic refresh when the dashboard runs on that machine)
- Uploaded Excel / CSV file

For SharePoint links that require Microsoft sign-in, configure Microsoft Graph once. After that, paste the normal SharePoint file URL into the existing **Data source URL** field. The dashboard first tries anonymous/direct download and, if Microsoft sign-in is detected, automatically retries through Microsoft Graph.

## 1. Microsoft Entra App Registration

Create an App Registration in Microsoft Entra ID. Record:

- Tenant ID
- Client ID
- Client secret

The app must have a Microsoft Graph **Application** permission that can read the target SharePoint site/file, with admin consent. Common approaches are:

- `Sites.Read.All` for broad read access; or
- `Sites.Selected` for least-privilege access, provided the app is separately granted access to the required site.

Your Microsoft 365 administrator may need to create the app and/or grant admin consent.

## 2. Configure Streamlit secrets

Copy:

```text
.streamlit/secrets.toml.example
```

to:

```text
.streamlit/secrets.toml
```

Then fill:

```toml
[sharepoint]
tenant_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
client_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
client_secret = "YOUR_SECRET_VALUE"
```

Do not put the secret into Python source code and do not commit `secrets.toml`.

Environment variables are also supported for servers/containers:

```text
SP_TENANT_ID
SP_CLIENT_ID
SP_CLIENT_SECRET
```

## 3. Install / update dependencies

```powershell
python -m pip install -r requirements.txt
```

The Graph integration uses `msal`.

## 4. Use the dashboard

In either Shop Visit room:

1. Paste the Google Sheets or SharePoint file URL into **Data source URL**.
2. Click **Connect / Test** in Engine Shop Visit, or **Refresh** in APU Shop Visit.
3. For a private SharePoint link, the sidebar should show **Private SharePoint: Microsoft Graph ready** when credentials are available.
4. The existing 60-second refresh logic remains active.

## Source behavior

### Google Sheets
The source must allow export/read access from the machine running Streamlit. The dashboard tries CSV/XLSX export and recognizes the required Shop Visit schema.

### SharePoint / OneDrive
The loader tries, in order:

1. direct/anonymous SharePoint download;
2. Microsoft Graph `/shares` resolution using the pasted URL;
3. SharePoint site/document-library path resolution through Graph.

This means the same URL field works for both public and private SharePoint links.

### Excel / CSV upload
Use **Upload Excel/CSV** for a local workbook. Each workbook sheet is inspected and the worksheet with the best APU/Engine Shop Visit schema match is selected.

## Security note

Prefer read-only permissions and least privilege. `Sites.Selected` is safer than tenant-wide read access when your Microsoft 365 administrator can provision it correctly.


## Local Excel / CSV path (automatic)

If Streamlit runs on the same Windows PC/server that has the workbook, paste a local path such as:

```text
C:\Users\YourName\Company\Powerplant\DATA APU SHOP VISIT.xlsx
```

or a synced OneDrive/SharePoint path. The dashboard will re-read the local file using the existing refresh cycle. This is different from **Upload Excel/CSV**, which stores the uploaded file only in the Streamlit session.


## Optional: automatic source at startup

To avoid pasting URLs after every restart, add the source locations to `.streamlit/secrets.toml`:

```toml
[sources]
apu_shop_visit = "https://.../DATA APU SHOP VISIT.xlsx"
engine_shop_visit = "https://.../ENGINE SHOP VISIT.xlsx"
```

The values may also be Google Sheets URLs or local Excel/CSV paths. Environment-variable alternatives are `APU_SHOP_VISIT_SOURCE` and `ENGINE_SHOP_VISIT_SOURCE`.


## SharePoint `Doc.aspx` workbook links

Engine Shop Visit and APU Shop Visit now accept Office-generated SharePoint workbook URLs such as:

```text
https://tenant.sharepoint.com/:x:/r/sites/PowerplantTeam/_layouts/15/Doc.aspx?sourcedoc={DOCUMENT-GUID}&file=DATA%20APU%20SHOP%20VISIT.xlsx&action=default&mobileredirect=true
```

The loader recognizes the `sourcedoc` and `file` parameters. It first tries anonymous/direct download variants (`action=download`, `download=1`, and a GUID download endpoint).

If the corporate SharePoint file is private, the Streamlit backend cannot reuse the Microsoft 365 browser login cookie. In that case configure the existing `[sharepoint]` Microsoft Graph credentials in `.streamlit/secrets.toml`. The Graph fallback resolves the site, searches its document libraries for the exact workbook name, prefers a matching SharePoint unique ID when available, and downloads the matching drive item.
