# SR3 reader test fixtures

These CMG SR3 sample files are from
[nikolai-andrianov/sr3_reader](https://github.com/nikolai-andrianov/sr3_reader),
revision `96ddf866701642d68a37b771344bbea4c110b954`:

- `cartesian_grid_example.sr3`
- `coreflood_geochem.sr3`

The upstream repository describes these as a Cartesian-grid simulation and a
geochemical coreflood simulation, respectively. They are provided under the
MIT License; see [LICENSE](LICENSE).

The tests read only the `WELLS` category. Reading every category from the
coreflood sample produces a very large merged table, while its WELLS data is
sufficient to check the reader against real simulator output.
