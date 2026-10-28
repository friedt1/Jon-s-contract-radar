# Jon's Tree Service Contract Radar

Mobile-friendly static dashboard and twice-daily automated public-news lead scanner.

## Install into existing GitHub repository

1. Extract this ZIP. Upload **all files and folders** to the root of `friedt1/Jon-s-contract-radar`, including the hidden `.github` folder. GitHub's web upload may hide dotfolders on some devices; use a desktop browser or GitHub Desktop if needed.
2. GitHub Settings → Pages → Build and deployment → Source: **GitHub Actions**.
3. Actions → Refresh contract leads → Run workflow.
4. Actions → Deploy website → Run workflow if necessary.
5. Check the website URL in Settings → Pages after successful deployment.

GitHub Actions workflow permissions must allow writing repository contents for scanner commits (Settings → Actions → General → Workflow permissions).

## Limitations

The initial feed uses Google News RSS and **does not establish that any lead is an open solicitation**. Coverage is incomplete. The approximately 2-hour radius is a target, not an actual travel-time filter. SAM.gov integration is deferred. Official procurement feeds, bid deadline extraction, and routing validation remain future work. The repo is public; avoid adding secrets.
