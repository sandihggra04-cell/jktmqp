# Upload ke GitHub — versi flat

Versi ini sengaja dibuat tanpa folder `rooms`, `pages`, `src`, atau `assets`.

Upload semua file di folder ini langsung ke root repository GitHub.

File utama di Streamlit Community Cloud:

```text
app.py
```

File page yang harus berada sejajar dengan `app.py`:

```text
home.py
reliability_page.py
engine_shop_visit_page.py
apu_shop_visit_page.py
```

Shared modules juga berada di root, misalnya:

```text
sv_source_loader.py
session_uploads.py
rel_config.py
rel_data_loader.py
engine_config.py
engine_data_utils.py
```

File gambar Garuda juga sudah dipindahkan ke root sehingga tidak memerlukan folder `assets`.

Untuk private SharePoint, masukkan secrets melalui Streamlit Cloud > App settings > Secrets.
Tidak perlu meng-upload folder `.streamlit`.
