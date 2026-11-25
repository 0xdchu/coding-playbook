**FAIL**

1. **MAJOR** — `windows/src/Ambysto.Lean.App/MainWindow.xaml.cs:204` (handler shared by `MainWindow.xaml:101` and `:122`): `OnScanClick` now requires `profileTicked`, but Scan again uses the same handler and stays enabled (`MainWindow.Overview.cs:91`). Untick C:, scan a folder, then click Scan again: nothing happens and nothing says why. There is no way back to the cards without restarting the app. This breaks the accepted departure ("keeps its ASP-14 behaviour"), and no test clicks it.

2. **MINOR, realistic** — `docs/spec/01-measure-and-map.md:50`: says "Scan (and Scan again) scans the ticked drives" and omits the departure. A builder working from the spec alone would tie Scan again to the ticks.

3. **MINOR, realistic** — test gaps in `OverviewPolishTests.cs`:
   - `:803` passes vacuously: the start panel is collapsed during a scan, so no card is found. Removing `IsEnabled` at `MainWindow.Overview.cs:96` or `:507` would survive; the root check and a move are unpinned.
   - Nothing tests the focus ring (dark, High Contrast, inside the card).
   - Nothing covers a real click on the disabled circle, Enter on a card, or the disabled look of other cards' boxes.

**Checked by reading, no issue found**
- **Dividers:** a divider is drawn only when its following item has a gap before it, so none sits at a line start or end. They are Raw, not hit-testable, with no peer; `LeanRuleBrush` by default and GrayText in High Contrast.
- **Other WrapPanels:** the legend and duplicate tabs are arranged as before (`CenterLines` is off, same returned height).
- **Card:** one CheckBox with the drive name, ticked from `profileTicked`, which also survives the High Contrast rebuild; other cards are disabled and unticked.
- **Scan paths:** only the two Scan buttons, the folder picker and `--scan` reach `ScanAsync`. No keyboard accelerator exists, and the tick handler starts nothing.
- **Hint line:** switches to the new text and keeps the link.
- **Focus ring:** a 2 px border inside the card's root grid, ink in dark; I could not confirm it on screen.

**Run (all PASS)**
- `windows-choke-points.sh`
- `windows-choke-points-fixtures.sh` (66/66)
- `windows-packages.sh`
- `windows-packages-fixtures.sh` (16/16)
- `copy-lint.sh`
- `windows-theme-colours.sh`

The builder left the test files unchanged.

**Not run**
- Release build and the VM suites: no `dotnet` on this host, and the main session drives the VM.
- Screenshots.
- Mutation checks.
