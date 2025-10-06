# Tournament Commentary Generator - Command Cheat Sheet

## Story Notes Only

**Single tournament:**
```bash
python generate_tournament_commentary_v2.py 17
```

**Multiple tournaments:**
```bash
python generate_tournament_commentary_v2.py --range 11 15
```

**Partial tournament (e.g., 2 rounds complete):**
```bash
python generate_tournament_commentary_v2.py 17 --partial 2
```

---

## Reports Only (story notes must already exist)

**Main report for one tournament:**
```bash
python generate_tournament_commentary_v2.py 17 --main-report-only
```

**Main reports for multiple tournaments (batched, cached):**
```bash
python generate_tournament_commentary_v2.py --range 11 15 --main-report-only
```

**Brief summary for one tournament:**
```bash
python generate_tournament_commentary_v2.py 17 --brief-summary-only
```

**Brief summaries for multiple tournaments (batched, cached):**
```bash
python generate_tournament_commentary_v2.py --range 11 15 --brief-summary-only
```

**Both reports for multiple tournaments (batched, cached):**
```bash
python generate_tournament_commentary_v2.py --range 11 15 --generate-reports
```

---

## Full Pipeline (story notes + reports)

**Single tournament:**
```bash
python generate_tournament_commentary_v2.py 17 --full-pipeline
```

**Multiple tournaments (batched, cached - RECOMMENDED):**
```bash
python generate_tournament_commentary_v2.py --range 11 15 --full-pipeline
```

---

## Special Cases

**Sequential processing (one TEG at a time, rarely needed):**
```bash
python generate_tournament_commentary_v2.py --range 11 15 --full-pipeline --sequential
```

---

## Key Notes

- **Default behavior:** Multiple TEGs are batched by type for optimal prompt caching (saves tokens)
- **Single TEGs:** Always processed sequentially (nothing to batch)
- **Report-only commands:** Story notes must already exist or they will error
- **Cache benefit:** Second and subsequent reports in a batch get ~90% token discount