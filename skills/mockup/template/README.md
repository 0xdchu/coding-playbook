# Mockup template

Copy this folder into the product's repo (usually `labs/app/` or `app-mockup/`), then replace the copy and data.
Keep the structure; it is what the check script and the gallery expect.

```
index.html    shell: gallery + screen view, web/mobile, light/dark
styles.css    tokens and components; replace colours and fonts with the product's own
data.js       SEED: screens, demo items, theme, device
screens.js    one render function per screen, plus the gallery
app.js        router, theme, device, loading → complete actions
check.mjs     the proof: routes, theme, hover, loading, overflow, console
vercel.json   noindex header
```

## Adapt

1. In `data.js`, replace `product`, `screens` (id, title, group, desc) and the demo `items`.
2. In `screens.js`, replace the copy in `login`, `board`, `settings`; add one function per new screen and register it in `RENDER`.
3. In `styles.css`, replace `:root` tokens and the font links in `index.html`.
4. Keep every interactive control inside `data-action`, `data-approve`, `data-go` or `data-theme-set`; `app.js` delegates from there.
5. Every async action must set busy, wait, then render the completed state.
6. The 390px frame sits inside a desktop viewport, so `@media` queries never fire inside it. Write frame-only rules as
   `.device-mobile ...` (or container queries on an inner wrapper); the `@media` blocks in `styles.css` are for real phones.
7. Rewrite the screen ids and selectors in `check.mjs` for the real screens; keep each assertion's intent.
8. Screens are full-bleed under the chrome. Wrap a screen in `.screen-wrap` if the product wants card margins.

## Use a design system (optional)

If the repo carries `design-systems/`, copy `<system>/tokens.css` and `<system>/components.css` next to this folder,
link them before `styles.css` in `index.html`, and use their classes. The template's own tokens remain the fallback
when no system is chosen. `design-systems/README.md` lists the systems and which screens each fits.

## Run and check

```sh
npm install
node check.mjs        # exit 0 = pass; screenshots in .check/
python3 -m http.server 8910   # or open index.html directly
```

## Deploy

Static, no build. On Vercel, connect the repo and set **Root Directory** to the folder, build and install commands
empty, **Output Directory** `.`; add `vercel.json` for the noindex header. Without a build step, a project whose
Output Directory defaults to `public` fails with `No Output Directory named "public"`.
