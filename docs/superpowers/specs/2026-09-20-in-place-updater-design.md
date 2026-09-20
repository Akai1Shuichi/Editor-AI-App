# In-place updater design

## Goal

When a packaged Editor Video AI application downloads a newer release, selecting
**Cập nhật ngay** must replace the installed application with that release and
restart it.  On the next launch, the application must read the version bundled
with the new executable.  Users must not manually delete or replace files.

The existing backend endpoints remain the source of truth:

- `POST /api/v1/update/check` reports whether a newer version exists.
- `GET /api/v1/update/download?code=s-editor&versionName=<version>&os=<os>`
  redirects to the platform ZIP asset.

## Release and installation contract

The release pipeline already emits a ZIP per Windows, macOS, and Linux.  The ZIP
contains the files directly under `dist/`; the current PyInstaller build is a
one-file executable, so each ZIP normally contains one `EditorVideoApp`
executable (`.exe` on Windows).  A future one-folder build remains supported as
long as its archive paths are relative to the app's install directory.

The installed application root is `Path(sys.executable).resolve().parent` for a
frozen build.  Development runs never perform an in-place update, because their
interpreter and source checkout must not be replaced.

The application version remains `app/data/config/version.json` bundled by
PyInstaller.  The updater does not edit a version file: replacing the executable
replaces the bundled configuration, so the new version appears on restart.

## Update flow

1. The main process downloads the backend-provided ZIP to a temporary update
   directory and validates every archive entry against path traversal.
2. It extracts the ZIP to a sibling staging directory.  The original install is
   untouched at this stage.
3. The app writes a short platform-specific helper script into the temporary
   directory.  The script receives the main process PID, staged directory,
   install directory, and executable name.
4. The app starts the helper as a detached external process and exits.
5. The helper waits until the original PID has exited, moves the current app
   files to a temporary backup, copies staged files into the install directory,
   and starts the replacement executable.
6. Once replacement starts successfully, the helper removes its backup and its
   own temporary files.  If copying fails, it restores the backup and leaves a
   human-readable failure log in the temporary update directory.

## Platform helper behavior

| Platform | Helper | Replace and restart |
| --- | --- | --- |
| Windows | PowerShell script launched with `powershell.exe` | waits for PID, uses `Copy-Item -Recurse -Force`, then `Start-Process` on the replacement `.exe` |
| macOS | POSIX shell script launched with `/bin/sh` | waits for PID, copies with `ditto`, then `open` or executes the replacement binary |
| Linux | POSIX shell script launched with `/bin/sh` | waits for PID, copies with `cp -a`, restores execute bits, then executes replacement binary |

The helper removes only files that belong to the packaged application.  It must
not delete unrelated user-created files in the installation directory.  For the
current one-file build, this is the old executable only; the future one-folder
case uses a packaged manifest of release paths to identify replaceable files.

## Failure handling

- A non-ZIP download is reported as an unsupported update package; it is not
  launched as a standalone installer.
- Archive traversal, missing executable, write denial, and helper-launch errors
  keep the current app untouched and report the error before exit.
- Installations in protected directories may need operating-system permission.
  The app reports that elevation is required rather than silently failing.
- If the helper cannot replace a locked file, it restores the previous package
  and writes the reason to the update log.

## UI behavior

The top-right update bar keeps the current state:

- `✓ Đã cập nhật (vX)` when the API reports no new version.
- `↑ Có bản mới vY` and **Cập nhật ngay** when a new release is available.
- `Đang cài đặt bản cập nhật…` after replacement is handed to the helper; the
  app exits immediately afterward.
- A failed preparation does not exit the app and shows an error dialog.

## Verification

Automated tests cover archive validation, frozen-versus-development eligibility,
the generated helper command for Windows/macOS/Linux, and the UI handoff state.
The existing update API tests continue to verify the check request and backend
download URL.  Manual packaged-build verification is required on each target OS:
install v1, update to v2, confirm the original installation path is retained,
and relaunch shows v2.
