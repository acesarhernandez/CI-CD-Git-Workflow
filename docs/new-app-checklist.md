# New App CI/CD Onboarding Checklist

Use this checklist when wiring a new application into the CI/CD system.

This is the **execution version** of the onboarding guide.

---

## 0. Pre-check (1 minute)

- [ ] App can run in Docker
- [ ] App has a clear start command
- [ ] Environment variables are defined
- [ ] Deployment target exists (server / VM / host)

---

## 1. Add CI/CD Config

Create:

- [ ] `cicd.app.yaml`

Define:
- app name
- image name
- environments
- ports / runtime config

---

## 2. Ensure Deploy Target Exists

On target host:

- [ ] App directory exists (e.g. `/home/cesar/docker/<app>`)
- [ ] `docker-compose.yml` or run strategy exists
- [ ] `.env` file exists if needed

---

## 3. Add Wrapper Workflows

Create in app repo:

- [ ] `.github/workflows/validate-cicd.yaml`
- [ ] `.github/workflows/build-deploy.yaml`
- [ ] `.github/workflows/build-publish.yaml` (manual)
- [ ] `.github/workflows/recover.yaml` (manual)

These should call the shared repo workflows.

---

## 4. Run Validation

- [ ] Push branch
- [ ] Confirm `validate-cicd` passes

If this fails:
→ fix config, not workflows

---

## 5. Run Full Pipeline

- [ ] Trigger build + deploy
- [ ] Confirm:
  - build passes
  - deploy passes
  - verify passes

---

## 6. Confirm App is Running

On target host:

- [ ] Container is running
- [ ] App is reachable (port / URL)
- [ ] Logs look correct

---

## 7. Confirm Manifest Retention

Check:
/home/cesar/docker//releases//release-manifest.json
- [ ] File exists
- [ ] Release ID matches pipeline output

---

## 8. Test Recovery (IMPORTANT)

Run manual recovery workflow:

- [ ] Provide manifest path
- [ ] Confirm:
  - deploy runs
  - verify passes

If this fails:
→ system is not production-ready

---

## 9. Clean Up

- [ ] Remove duplicate or legacy workflows
- [ ] Ensure only intended workflows remain
- [ ] Confirm manual workflows are not auto-triggering

---

## 10. Snapshot

Record:

- what worked
- what broke
- what was confusing
- what you fixed

---

## Done Criteria

You are finished when:

- [ ] Full pipeline passes
- [ ] App runs correctly
- [ ] Manifest is retained
- [ ] Recovery works
- [ ] No duplicate workflows exist

---

## Notes

- Always fix issues in the **shared repo**, not per app
- Always push new commits after shared workflow changes
- Do not rely on "re-run failed jobs" for shared updates
