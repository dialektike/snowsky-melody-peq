# Contributing

Thanks for considering a contribution.

## Scope

This project's scope is intentionally narrow: **parametric EQ control on the
FiiO SnowSky Melody**. Out-of-scope contributions:

- Support for other FiiO devices (K13, BTR17, etc.). The protocol is similar
  but device-specific quirks belong in separate projects.
- Non-EQ controls (SPDIF toggle, DAC filter, firmware update). These are
  available in the official FiiO Control app and intentionally not in scope
  here for safety reasons.
- Audio I/O. This is a control-plane library only.

If you need any of the above, fork freely under MIT.

## Development setup

```bash
git clone https://github.com/dialektike/snowsky-melody-peq
cd snowsky-melody-peq
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Run the local checks (no hardware required):

```bash
pytest
ruff check src/ tests/
mypy src/
```

All three should pass cleanly before opening a PR.

## Hardware verification PRs are very welcome

The library has been verified end-to-end on macOS with one SnowSky Melody
— including `save_to_user` persistence across USB power cycles. The
detailed findings (USER slot activation IDs `7..9`, `get_preset()`
Personal-indicator semantics, etc.) live in `CHANGELOG.md` and
`docs/PROTOCOL.md`. **A second unit on different firmware or a different
OS may behave differently**, so additional verification PRs are still
very welcome.

The end-to-end procedure lives in
[`docs/HARDWARE_TESTING.md`](docs/HARDWARE_TESTING.md) (Korean version:
[`docs/HARDWARE_TESTING.ko.md`](docs/HARDWARE_TESTING.ko.md)). It walks
through using `examples/hardware_test.py` together with the FiiO web UI
as visual ground-truth. Please follow that order on a first pass.

When you open an issue or PR, please include:

- Output of `melody-peq dump`
- USB product string (`python -c "import hid; print(hid.enumerate(0x2972,0))"`)
  so we can confirm the identity-check word-boundary regex still matches
- Screenshots of the FiiO web UI for any test where your unit's
  behaviour differs from what `docs/HARDWARE_TESTING.md` predicts
- Confirmation that `apply` followed by `save_to_user` persists after a
  USB power cycle on your unit
- Any preset-ID mappings or response bytes that differ from what
  `docs/PROTOCOL.md` already documents

## Code style

- `ruff` is the linter of record (settings in `pyproject.toml`).
- `mypy` is the type checker of record. Don't introduce new type errors.
- Public API: type hints required. Scalar getters return `T | None` when
  the device might not respond — never collapse `None` to a default value.
- Keep the controller and protocol layers cleanly separated — `protocol.py`
  must stay free of `hid` (or any other backend-specific) imports.
- `Band` constructor validates ranges. If a new code path can produce
  out-of-range values, surface that with a clear `ValueError` at the
  boundary rather than letting it wrap silently in the wire encoding.

## Testing

All non-hardware code paths should have unit tests. Hardware-dependent tests
are out of scope for CI. When you add a defensive check (range validation,
oversize rejection, "no response" handling), add a matching test that mocks
the relevant boundary — see `tests/test_getters_no_response.py` and
`tests/test_types.py` for the patterns to follow.
