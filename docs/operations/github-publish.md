# Publishing NEXUS COVE to GitHub

The repository is initialized on `main` with a clean root commit (`4dd8423`).

## One-time remote setup

```powershell
# From the repository root (after creating an empty GitHub repo with no README)
git remote add origin https://github.com/<org-or-user>/NEXUS-COVE.git
git push -u origin main
```

SSH variant:

```powershell
git remote add origin git@github.com:<org-or-user>/NEXUS-COVE.git
git push -u origin main
```

## Recommended GitHub repository settings

| Setting | Value |
|---------|--------|
| Visibility | Private until a license decision is final; or Public with the current All Rights Reserved notice |
| Branch protection on `main` | Require PR, require status checks (CI) |
| Actions | Enabled (workflow: `.github/workflows/ci.yml`) |
| Dependabot | Enabled (config present) |
| Topics | `multi-agent`, `websocket`, `python`, `orchestration`, `local-first` |

## What is intentionally *not* in this baseline

- Open-source license grant (see `LICENSE`)
- Authentication / TLS
- Hyper-scale memory matrix, unanchored free will, or four-agent expansion (roadmap phases)
- Modernized PowerShell launchers beyond the Diagnostic Hospital

## Post-push verification

1. Confirm CI runs green on the initial push.
2. Open `README.md` on GitHub and check links resolve.
3. Clone into a clean directory and run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest tests -q
```

## Local identity used for the root commit

```
user.name  = NEXUS COVE
user.email = nexus-cove@local.dev
```

Override with your own identity before further commits if desired:

```powershell
git config user.name "Your Name"
git config user.email "you@example.com"
```
