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

Run the unit tests (no hardware required):

```bash
pytest
ruff check src/ tests/
```

## Hardware verification PRs are very welcome

The library has not yet been hardware-verified on a Melody. If you have one,
please open an issue or PR with:

- Output of `melody-peq dump`
- USB product string (so we can confirm the identity-check substring is right)
- Confirmation that `apply` followed by `save_to_user` persists after reboot

## Code style

- `ruff` is the linter and formatter of record.
- Public API: type hints required.
- Keep the controller and protocol layers cleanly separated — no `usb.core`
  imports in `protocol.py`.

## Testing

All non-hardware code paths should have unit tests. Hardware-dependent tests
are out of scope for CI.
