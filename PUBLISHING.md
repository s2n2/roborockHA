# Put Dobby Scheduler on GitHub and install it through HACS

## 1. Set your repository identity

Repository: `https://github.com/s2n2/roborockHA`.

Open `custom_components/dobby_scheduler/manifest.json` and replace all three
Repository metadata has already been configured for `https://github.com/s2n2/roborockHA` with `@s2n2` as code owner. For an organisation-owned repository, use the
organisation in the URLs and a real individual maintainer in codeowners.

Alternatively, with Python installed, run this from the extracted repository:

```sh
python scripts/configure_repository.py s2n2 --repo roborockHA
python scripts/check_repository.py
```

The scripts operate on local files only. They do not create a GitHub repository,
request credentials, or publish anything.

## 2. Create and upload

Create a **public** GitHub repository. Add a description such as:

> Label-driven Roborock room scheduling and dashboard controls for Home Assistant.

Suggested topics: `home-assistant`, `hacs`, `roborock`, `robot-vacuum`.
Leave Issues enabled. The included LICENSE is MIT.

For a browser upload, use the new repository's Upload files link (or Add file >
Upload files). Drag in the CONTENTS of this extracted folder. Include hidden
`.github` and `.gitignore` items. GitHub supports uploading folders.

Do not upload the ZIP as the only file. Do not add an extra containing directory.
Your GitHub repository root must show `custom_components`, `hacs.json`, and
`README.md` together. The integration must be at:

```
custom_components/dobby_scheduler/manifest.json
```

Commit the upload. GitHub Actions runs HACS validation, hassfest and local
controller simulations. Fix failed checks before a release. These workflows
have read-only repository permissions and do not publish releases or control HA.
The metadata check deliberately fails while the username placeholder remains.

The previous household-specific `dobby_mapping_review.md`, HA exports,
`.storage`, credentials and backups are NOT part of this repository. Do not add
them. A .gitignore helps local Git use but is not a security boundary or a
substitute for checking a browser upload.

## 3. Add the custom repository in HACS

In Home Assistant, open HACS > three dots > Custom repositories.
Paste your new GitHub repository URL, select **Integration**, and Add.
Find Dobby Scheduler and Download. Restart Home Assistant.

This is an integration with a bundled dashboard card, not a separate HACS
Dashboard repository. HACS installs the whole custom_components/dobby_scheduler
folder, including its frontend subfolder. It does not copy the optional package
or root dashboard-card.yaml into your configuration.

For a new install, use Settings > Devices & services > Add integration > Dobby
Scheduler. No YAML bootstrap package is necessary on this route.

Add this dashboard resource once as a JavaScript module:

```
/dobby_scheduler_frontend/dobby-scheduler-card.js?v=0.1.0
```

Add the card:

```yaml
type: custom:dobby-scheduler-card
title: Dobby
```

This build serves the card but does not register the Lovelace resource for you.
Do not use /hacsfiles for this integration-bundled card. Existing manual installs
should keep the same domain and config entry; do not delete the integration entry
just to move file updates to HACS. Back up first and keep automatic scheduling off
during the change. Do not add a duplicate resource or configuration entry.

## 4. Releases and updates

A custom repository can initially install from its default branch, without a
GitHub Release. For controlled versioned updates, publish a release once you
have checked the uploaded code and performed supervised tests:

- Tag: `v0.1.0`
- Target: your uploaded branch, normally `main`
- Title: `Dobby Scheduler 0.1.0 - experimental`
- Description: state compatibility, changes and known limitations honestly.

Use a GitHub Release, not only a Git tag. You do not need to attach a ZIP: this
hacs.json uses the files in the tagged repository and does not use zip_release.
A GitHub pre-release is appropriate for testing. For pre-release update alerts,
enable the repository's pre-release switch supplied by HACS; it may be disabled
in the entity registry initially. The default branch remains available for
initial testing.

For a subsequent version, update manifest.json (for example to `0.1.1`), update
CHANGELOG.md, run tests and publish a NEW release tag, for example `v0.1.1`.
Do not overwrite old release tags to distribute changed code. Update any visible
version strings when making a functional release. When the JavaScript changes,
change the documented resource query version, update the existing HA resource
entry and refresh clients rather than adding a second resource entry.

HACS can deliver updates, but it does not prove those updates are safe on your
robot. Keep explicit user-approved updates until live compatibility is established.
Settings and the queue are stored outside the integration source directory in
HA's `.storage`; back up HA, keep the same config entry, and do not put `.storage`
in GitHub. Avoid editing installed Python locally because HACS replaces it.

## 5. HACS default catalogue is a separate later step

A custom repository is enough for you and other people to install and update
using its URL. It does not need prior catalogue acceptance.

For public discovery in the default catalogue, meet the current HACS submission
requirements: public repository, description/topics/issues, brand assets, passing
HACS validation with no ignored checks, passing hassfest, and a published release.
Then submit your owner/repository to the integration list in `hacs/default` in
alphabetical order. Acceptance is not automatic or a hardware-safety certification.

This repository has a simple original DS placeholder icon in the integration's
brand directory. Replace it with your preferred properly licensed branding later.

## Scope of this preparation

Added publishing metadata, documentation, original placeholder brand images,
ignore rules, helper scripts and validation workflows. The scheduling Python
and card JavaScript were not changed. The maintainer username and URLs still need
to be filled in. Local packaging checks do not establish a successful HACS install.
No GitHub account was connected and nothing was published remotely.

## Official references (checked 3 October 2026)

- https://www.hacs.xyz/docs/publish/start/
- https://www.hacs.xyz/docs/publish/integration/
- https://www.hacs.xyz/docs/faq/custom_repositories/
- https://www.hacs.xyz/docs/publish/action/
- https://www.hacs.xyz/docs/publish/include/
- https://www.hacs.xyz/docs/use/entities/switch/
- https://developers.home-assistant.io/docs/core/integration/brand_images/
- https://developers.home-assistant.io/docs/creating_integration_manifest/
- https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository
- https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository
