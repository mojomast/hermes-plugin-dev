# hello-hermes

Minimal native Hermes plugin template. One tool (`hello_hermes`), one bundled skill.

Disclosure: no network, subprocesses, background threads or credentials.

```bash
pip install pytest pyyaml && pytest -q              # offline, no Hermes needed
hermes plugins doctor . --ci                          # real runtime contracts
hermes plugins validate . --install-deps              # same gate as catalog CI
ln -s "$PWD" ~/.hermes/plugins/hello-hermes && hermes plugins enable hello-hermes
```

Tested with Hermes vX.Y.Z.

## Safety contract
This example is entirely offline: it performs no network requests, spawns no subprocesses, reads no credentials, and writes no runtime files. All registered results, including invalid operations, are JSON strings. If extending it, follow the security-boundaries, pane transport and live-acceptance references before adding URLs, files, online mode or UI.
