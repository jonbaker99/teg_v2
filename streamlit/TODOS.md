# streamlit — To-dos

The Streamlit app is **stable and deployed**. Changes here are maintenance-only; new analytical work goes in `teg_analysis/`.

---

## Known issues

- [ ] **`DEBUG = True` left on in commentary scripts** — `streamlit/commentary/generate_round_report.py` and `generate_tournament_commentary_v2.py` both have `DEBUG = True` hardcoded. Low impact (debug prints only) but should be cleaned up.

## Maintenance

Nothing currently outstanding. The Streamlit app is feature-frozen; parity with new analysis is provided by `teg_analysis/`.
