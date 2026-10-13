# CyberScope presentation preview

Two slides: **Problem Statement** and **Design & Methodology**. The methodology is an illustrative animation of the **proposed architecture**, not a live connection to the device or blockchain.

From the repository root:

```sh
python3 -m http.server 8000 --directory presentation --bind 127.0.0.1
```

Open <http://localhost:8000>. All fonts, scripts and styles are local; the deck needs no internet connection. `index.html` can also be opened directly, but speaker view needs the local server.

- Arrow keys or the bottom-right controls: change slides.
- **F**: fullscreen. **S**: speaker view. **Esc**: overview.
- **Pause / Resume**: control the 30-second diagram loop.
- Animation suspends while another slide, overview, blackout or browser tab is visible.
- Reduced-motion preferences replace moving particles with discrete state changes.

The loop registers a known-good baseline, accepts unchanged runtime state, detects an added USB device, rejects data, alerts the administrator and depicts approved restoration. SHA-256 is hashing, not encryption. Digests and sensor readings are illustrative. The baseline is never replaced by a tampered runtime digest.

Problem statistics retain the wording and context of the [Dragos 2026 OT Cybersecurity Year in Review](https://www.dragos.com/ot-cybersecurity-year-in-review). The methodology narration comes from the supplied scripts and `../based.md`; speaker notes distinguish the proposed architecture from current implementation.

Dependencies: Reveal.js **5.2.1** (MIT; `vendor/LICENSE`), Space Grotesk variable font (SIL OFL; `fonts/OFL.txt`). Vendored Reveal.js files came from jsDelivr's npm package. Space Grotesk came from the Google Fonts repository.

The browser check is `verify.cjs`. It requires Playwright as a verification tool, not a deck runtime dependency:

```sh
NODE_PATH=/private/tmp/cyberscope-preview-tools/node_modules node presentation/verify.cjs
```

Run the local server first. Verification captures are under `.impeccable/review/`.
