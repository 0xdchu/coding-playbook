**FAIL**

1. **MAJOR**, `windows/src/Ambysto.Lean.App/MainWindow.xaml.cs:204` (and `MainWindow.xaml:101`): Scan again uses the same click handler as the Scan circle, `OnScanClick`. That handler now does nothing unless `profileTicked` is true. The accepted departure says Scan again is not tied to the ticks, and `SetScanControlsEnabled` (`MainWindow.Overview.cs:188`) leaves it enabled. Because the button is enabled, the user can click it, and the click is silently ignored.
   - **Steps:** untick C:, use Scan a folder and pick a folder on C:, then click Scan again on the results view. Nothing happens and no message appears.
   - **Why the user is stuck:** once `tree` is set, the start screen never comes back, so they cannot tick C: again until they restart the app.
   - This is exactly the case the departure was accepted for: a user who scanned a folder with C: unticked.

2. **MINOR (realistic)**, `docs/spec/01-measure-and-map.md:50`:
   - The spec says "**Scan** (and **Scan again**) scans the ticked drives". That goes against the accepted departure, where only the Scan circle follows the ticks.
   - The ASP-18 note was pasted into the middle of the ASP-14 note. The ASP-14 sentence after it, "A folder on that drive can be scanned…", now follows the divider text, so "that drive" no longer has a clear subject.

3. **MINOR (realistic)**, test gaps in `windows/tests/Ambysto.Lean.UiTests/OverviewPolishTests.cs`:
   - No test clicks Scan again after a folder scan with nothing ticked. That test would have caught issue 1.
   - No test checks the card's own focus ring: that it is visible in dark and High Contrast, sits inside the card's bounds, and does not show on pointer focus.
   - No test checks that the other WrapPanels (the legend and the duplicate type tabs) look the same as before. I read the code instead: with `CenterLines` off and no `BandDivider` child, the layout is the same as before, and the returned height is the same.

**What I checked and found correct:**
- **Dividers:** none at the start or end of a line, `Raw`, not hit-testable, `LeanRule` normally and `GrayText` in High Contrast. None of the band's items is ever collapsed, so a collapsed item can't leave a stray divider.
- **Card:** Space toggles and the card has no Invoke pattern. It is ticked at start and the tick is not saved. It is off while a scan, a move or the root check runs (`ScanOrMoveBusy`, and `UpdateMoveControls` covers `checkingRoot`). Other drives' cards are disabled and unticked. Ticking starts nothing, Enter has no handler, and `--scan` is not changed.
- **Focus ring:** drawn inside the card, in the ink colour normally and the system colour in High Contrast.

**Commands run:**
- `scripts/copy-lint.sh`: PASS
- `scripts/windows-choke-points.sh`: PASS, no forbidden uses
- `scripts/windows-packages.sh`: PASS
- A grep for new suppressions (`#pragma warning`, `SuppressMessage`, `NoWarn`): none found.

**Not run:**
- `vm-gates.sh` (Release build, OverviewPolishTests, the start-screen classes) and the installer proof: the VM is driven by the main session.
- The screenshots and the High Contrast visual check: they need the VM console.
- The choke-point fixtures script.
