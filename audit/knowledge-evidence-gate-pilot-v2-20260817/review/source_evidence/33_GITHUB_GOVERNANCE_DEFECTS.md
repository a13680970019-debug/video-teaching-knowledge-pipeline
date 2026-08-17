# GitHub Governance Defects

- main API branch record reports protected=False.
- Branch protection API returncode=1; response=None; stderr=Get "https://api.github.com/repos/a13680970019-debug/video-teaching-knowledge-pipeline/branches/main/protection": EOF.
- Rulesets API returncode=1; response={'message': 'Upgrade to GitHub Pro or make this repository public to enable this feature.', 'documentation_url': 'https://docs.github.com/rest/repos/rules#get-all-repository-rulesets', 'status': '403'}; stderr=gh: Upgrade to GitHub Pro or make this repository public to enable this feature. (HTTP 403).
- The live response states the private-repository plan limitation. This is recorded as UNKNOWN/UNSUPPORTED_BY_CURRENT_PLAN, not as enabled and not as none.
- Repository was not made public and plan was not upgraded.
- GITHUB_GOVERNANCE_READY = false until server-side protection is verifiable on a supported plan.
