# Đóng Gói Ứng Dụng Ở Local

Kích hoạt môi trường Python, cài dependency và chạy PyInstaller với file cấu hình của dự án:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
# .venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

pyinstaller --noconfirm --clean editor_video_app.spec
```

File thực thi được tạo trong `dist/`:

- Windows: `dist/EditorVideoApp.exe`
- macOS/Linux: `dist/EditorVideoApp`

# Push Tag Để Build & Release

Workflow GitHub Actions tại `.github/workflows/build.yml` sẽ build **Editor Video App** trên Windows, macOS và Linux khi nhận tag có dạng `v*`.

```bash
# Tạo tag phát hành (ví dụ v1.0.0)
git tag -a v1.0.0 -m "Release Editor Video App v1.0.0"

# Push tag để kích hoạt build và tạo GitHub Release
git push origin v1.0.0
```

Sau khi workflow hoàn tất, các gói ZIP cho ba hệ điều hành sẽ có trong GitHub Release của tag đó.
