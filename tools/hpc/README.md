# tools/hpc/

One-time cluster helpers (the run pipeline itself is `./hsol run`):

- `discover_vasp_modules.sh` - search module systems for VASP, compiler and MPI modules and
  resolve binaries; writes a report under `/tmp/hsol_vasp_discovery_<timestamp>/`.
- `check_vasp_installation.sh` - load a module stack, check the binary and its libraries, and
  optionally run a one-atom VASP calculation (`--run-smoke true --potcar ...`) to confirm VASP
  starts and exits cleanly; reports the VASP version.

See [`docs/hpc_setup.md`](../../docs/hpc_setup.md).
