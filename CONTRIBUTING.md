# Contributing to lvgl-bindings

lvgl-bindings is the **single writer** for the LVGL family. The generator in
`binding/`, `lv_conf.h`, the helpers in `python/` and the generated bindings
under `generated/` are edited only here. lvgl-python, lvgl-micropython and
lvgl-circuitpython sync them in, and an edit made directly in one of those
repositories is overwritten by its next sync. How the family fits together is
on the [docs site](https://github.com/PyDevices/lvgl-bindings/blob/main/docs/index.md); this page is for changing it.

If you are fixing something that only one package owns (the CPython runtime,
the MicroPython allocator, a build file), open the pull request in that
package's repository instead; each has its own `CONTRIBUTING.md`.

## Where things are

```text
lvgl-bindings/
  binding/              Modular Python generator (binding.generate is the entry point)
  lvgl/                 LVGL submodule (git submodule update --init lvgl)
  lv_conf.h             Shared LVGL config for all targets
  generated/            Generated bindings, API model and shared stub (committed)
  python/               Hand-written helpers (fs_driver.py, committed)
  packages/             Optional MIP manifests
  regenerate_all.sh     Entry point for regenerating all binding artifacts
  docs/                 The LVGL documentation site's source
  fonts/                Committed *.bin font files that fs_driver.py loads at runtime
  tests/                Generator unit tests
  scratch/              Upstream-baseline oracle, to diff against LVGL's upstream binding
  tools/                Artifact hashing and smoke checks
  scripts/              Verification and release utilities
```

`docs/` also holds `baseline/`, the compact historical API record that
`binding.api_report` and the tests read. It stays off the site.

## Set up

```bash
git clone https://github.com/PyDevices/lvgl-bindings.git
cd lvgl-bindings
git submodule update --init lvgl
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
```

`requirements.txt` holds the runtime generator dependencies alone;
`requirements-dev.txt` adds the pinned test and static-checking tools. The
consumer repositories don't need this clone beside them: each one's
`scripts/sync_from_lvgl_bindings.sh` fetches an exact commit from GitHub, and
`LV_BINDINGS_REPO` points it at your own clone or fork instead.

## The usual loop

Make a small change in `binding/` or the LVGL submodule, regenerate the target
you need, sync the generated files into the consumer repository, then rebuild
that repository's firmware or extension. For a change to the Python helpers
only, start with [`python/fs_driver.py`](python/fs_driver.py) and the consumer sync script. If you
changed the C API surface or the LVGL headers, regenerate and rebuild a
consumer before trusting the result.

## Generate the bindings

Regenerate after changing `lvgl/`, `lv_conf.h` or `binding/`, then commit the
updated files under `generated/`:

```bash
./regenerate_all.sh                    # all targets
./regenerate_all.sh --target micropython
./regenerate_all.sh --target circuitpython
./regenerate_all.sh --target cpython
./regenerate_all.sh --pyi-only         # shared stub only
./regenerate_all.sh --check --hash     # read-only reproducibility check, the gate a release uses
```

`regenerate_all.sh` never commits, tags, pushes or dispatches a release. It
calls the generator directly:

```bash
PYTHONPATH=. .venv/bin/python -m binding.generate
```

Call `-m binding.generate` yourself only for flags the wrapper doesn't expose,
such as `binding.api_report`:

```bash
PYTHONPATH=. .venv/bin/python -m binding.api_report generated/api.json \
    --baseline docs/baseline/lvgl-bindings-api-baseline.json.gz \
    --classification docs/baseline/lvgl-bindings-api-baseline-classification.json \
    --format markdown
```

The unified command preprocesses LVGL once and writes the selected target's C
source, the target-neutral `api.json`, the shared `lvgl.pp`, the CircuitPython
generated header and the shared `lvgl.pyi`. The API model is hashed and
includes visibility and target availability; deliberate exceptions live in
[`binding/api_policy.json`](binding/api_policy.json). Preprocessing removes compiler line markers, so the
inputs are reproducible across checkout paths. `--check` generates into a
temporary directory and never changes the working tree.

The stub comes only from the canonical [`generated/api.json`](generated/api.json). Use `--pyi-only`
when you change typing emission, so the C bindings, the model and the
preprocessed input aren't regenerated. The public names are the one
upstream-compatible profile; there is no alternate naming mode.

`binding.api_report` validates the canonical model and reports qualified
export counts, common-target coverage, target availability exceptions,
inheritance-expanded object APIs, generated artifact hashes, and the diagnostic
projection against the historical baseline.

## Check your work

```bash
TMPDIR=/tmp/lvgl-bindings-pytest .venv/bin/python -m pytest -q -s tests
./scripts/verify_bindings.sh           # read-only checks
./scripts/release_dry_run.sh           # the complete non-mutating release gate
```

[`scratch/upstream_baseline/run.sh`](scratch/upstream_baseline/run.sh) verifies that the pinned upstream generator
still reproduces the baseline, without keeping its source or full outputs in
this repository. All of its output is created in a temporary directory and
removed on exit. Set `LVGL_BINDINGS_UPSTREAM_REPO` to reuse a checkout at the
pinned commit instead of cloning one.

`linux-integration.yml` builds the MicroPython and CircuitPython unix ports
with lvgl-micropython and lvgl-circuitpython pinned at the commit under test,
and runs [`tools/test_lvgl_smoke.py`](tools/test_lvgl_smoke.py) on each. CPython rebuilds its extension and
wheel from the synced source.

## The consumers

| Repository | What it takes from here |
|---|---|
| [lvgl-micropython](https://github.com/PyDevices/lvgl-micropython) | [`generated/lvgl_micropython.c`](generated/lvgl_micropython.c), `lvgl/`, `lv_conf.h`, `python/fs_driver.py` into `lib/` |
| [lvgl-circuitpython](https://github.com/PyDevices/lvgl-circuitpython) | [`generated/lvgl_circuitpython.c`](generated/lvgl_circuitpython.c) and `.h`, `lvgl/`, `lv_conf.h`, `python/fs_driver.py` into `lib/` |
| [lvgl-python](https://github.com/PyDevices/lvgl-python) | [`generated/lvgl_python.c`](generated/lvgl_python.c), [`generated/lvgl.pyi`](generated/lvgl.pyi), `lvgl/`, `lv_conf.h` and the helpers; the one that publishes the wheel |

Each consumer records the resolved source SHA in `LVGL_BINDINGS_COMMIT`. Its
sync script rejects branch names, so a downstream build can't silently move to
a different generator or artifact set.

## Releasing

Bindings releases mirror the LVGL major and minor API line and use their own
patch counter. The line is `9.5.N`; `N` advances with each bindings release
regardless of LVGL's own patch number. This repository publishes **source tags,
not wheels or GitHub Releases**, so an empty Releases sidebar here is expected.

Generation, validation and release are separate actions. None of the
`regenerate_all.sh` commands above commits, tags, pushes, dispatches another
repository or publishes a package.

1. Run the whole non-mutating gate. It runs the generator tests, regenerates
   and compares every artifact, validates the API, stub and namespace
   contracts, prints the artifact hashes, and checks the expected version is on
   the `9.5.N` line. Its last lines confirm that nothing was published or
   changed in git history.

   ```bash
   ./scripts/release_dry_run.sh
   ./scripts/next_release_version.sh --verbose    # the version alone
   ```

2. After committing the reviewed artifacts, cut the tag with the dedicated
   command. It rejects a dirty tree, an invalid version or an existing tag.
   Pushing the tag does not trigger anything by itself.

   ```bash
   ./scripts/publish_release_tag.sh --dry-run
   ./scripts/publish_release_tag.sh          # create locally
   ./scripts/publish_release_tag.sh --push   # push to the remote
   ```

3. Dispatch the **Release bindings** workflow (`release.yml`) by hand. It takes
   an exact 40-character commit SHA or a `vX.Y.Z` tag, runs the same dry-run
   gate, resolves the source to a full SHA, and reports the expected version.
   Its `publish` input defaults to false. Only a run with `publish=true`
   dispatches lvgl-python in release mode, which syncs and publishes the wheel.

Merging to `main` releases and propagates nothing. Consumers don't track
`main`: each pins an exact `LVGL_BINDINGS_COMMIT` and moves only when its own
sync is run against a specific commit or release tag.

```bash
./scripts/sync_from_lvgl_bindings.sh --ref <40-character-commit-sha>
./scripts/sync_from_lvgl_bindings.sh --ref v9.5.N
```

Run those in a consumer repository. `lvgl-micropython` and `lvgl-circuitpython`
verify the generated C, the LVGL submodule and `lv_conf.h` against the pinned
commit in their builds; `lvgl-python` vendors the generated C, stubs, config,
helpers and LVGL, and records the resolved commit in its package source.
MicroPython and CircuitPython consume the exact generated source in their own
build systems and publish no wheels.

## The docs site

The LVGL documentation for all four repositories is built from `docs/` here.

```bash
pip install -r docs/requirements.txt
sphinx-build -W --keep-going -b html docs _site
```

`-W` fails on any warning, as Read the Docs does. When you move a page, fix the
links to it in the other three repositories' READMEs too.
