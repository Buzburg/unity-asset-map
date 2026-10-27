# Release verification — unity-asset-map v0.1.1

Verified locally on October 27, 2026, Linux x86-64. Toolchains: Python 3.14.8, Rust 1.98.1, Node.js 26.8.1, Go 1.27.1 and Mojo 1.1.0, as applicable. CI covers additional versions/platforms where configured; consult the workflow run for the release commit rather than an older green run.

## Checks

```sh
python -m unittest discover -s tests -v
python -m mypy .
python -m ruff check .
python -m build
```

**Local result: PASS.** 5 integration tests, strict type checks, lint, source/wheel builds and installed-wheel demo report acceptance.

The Python build command requires the `build` package; Unity checks also require `mypy` and `ruff`. Native Mojo experiments are optional and require Mojo 1.1.0. CLI acceptance used disposable fixtures and no real customer data.

## Release changes

Refresh the product story and verify the installable package and offline report workflow.

The README and repository summary now explain the supported behavior, installation, and limits without unverified speed or security promises.

## Limits

Only supported text GUID references are indexed. Binary assets, runtime dependencies and a real Unity editor integration are outside this scanner’s scope.

Git history was checked for common credential/key patterns. Matches in Envghost were synthetic scanner fixtures; no live credentials were identified by that scan. This is a limited pattern check, not a comprehensive security certification.
