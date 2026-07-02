# HINDSOLE

*Every step, in hindsight.*

A premium sneaker drop e-commerce platform built with Django, Tailwind CSS, HTMX, and Alpine.js. A curated catalog for collectors — not a discount outlet.

---

## Tech stack

- **Backend:** Django 5.0 (LTS), Django ORM, custom `User` model (email login)
- **Database:** PostgreSQL-ready (`JSONField`, indexes) with automatic SQLite fallback for local dev
- **Frontend:** Django Templates + Tailwind CSS v3 (mobile-first)
- **Interactivity:** HTMX (cart, filtering, pagination) + Alpine.js (galleries, menus, dark mode, bottom sheets)

## Project layout

```
config/          settings, root urls
accounts/        custom User, Address, auth views, profile
products/        Brand, Category, Tag, Product, ProductVariant, ProductImage
cart/            session+DB cart, merge-on-login logic
orders/          checkout flow, Order/OrderItem (price/size snapshot)
templates/       base shell + per-app templates
static/css       Tailwind input/output
static/js        Alpine helper directives
```

---

## Setup

### 1. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# edit .env — at minimum, set a real DJANGO_SECRET_KEY
```

Leave `DATABASE_URL` unset to use SQLite automatically. To use PostgreSQL instead, set:

```
DATABASE_URL=postgres://user:password@localhost:5432/hindsole
```

### 4. Install frontend tooling & build CSS

```bash
npm install
npm run build:css          # one-off build → static/css/output.css
# or, while developing:
npm run watch:css          # rebuilds on every template/class change
```

### 5. Migrate & seed

```bash
python manage.py migrate
python manage.py seed_products       # demo catalog: brands, colorways, sizes, stock
python manage.py createsuperuser
```

Optionally, add one more product photographed with real product photography
(everything else in the seed catalog uses generated placeholder images):

```bash
python manage.py seed_unsplash_demo  # downloads real photos from Unsplash — needs internet access
```

This requires outbound internet access to `images.unsplash.com` and won't
work in network-restricted environments (CI, some sandboxes). Every photo
it downloads is individually selected from Unsplash's free, commercial-use
license with no visible brand logos, consistent with this project's use of
fictional brand names. See the command's docstring
(`products/management/commands/seed_unsplash_demo.py`) for photo credits
and licensing details, and pass `--flush` to replace it if you re-run the
command.

### 6. Run

```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000/` for the storefront and `http://127.0.0.1:8000/admin/` for the catalog admin.

---

## Working on templates + Tailwind together

Run these in two terminals while developing:

```bash
npm run watch:css
python manage.py runserver
```

Tailwind scans every `*.html` under `templates/` (see `tailwind.config.js` → `content`), so any new utility class you type in a template is picked up automatically — no separate "register this class" step needed.

---

## Design tokens

Defined in `tailwind.config.js` and `static/css/input.css`:

- **Color:** warm off-white/charcoal neutral scale (`neutral-50`…`950`) + a single burnt-orange accent (`accent-500`, `#C3501A`) used only for CTAs, urgency labels, and active states — never as a base UI color.
- **Type:** `Fraunces` (display/serif, wordmark + headings) + `Inter` (UI/body). Fluid sizes (`text-fluid-*`) use `clamp()` so headings scale smoothly from mobile to desktop without breakpoint-jump.
- **Dark mode:** class-based (`darkMode: "class"`), toggled via the header sun/moon icon, persisted in `localStorage` and (for logged-in users) on the `User.dark_mode_enabled` field.

---

## Responsiveness testing notes

The brief's breakpoints map onto Tailwind's `screens` config like this:

| Breakpoint | Width | Tailwind prefix |
|---|---|---|
| Mobile | 320–480px | (base, unprefixed) |
| Mobile large | 481–767px | `sm:` |
| Tablet | 768–1023px | `md:` |
| Laptop | 1024–1439px | `lg:` |
| Desktop | 1440px+ | `xl:` |

What to check manually (or via Chrome DevTools device toolbar / Playwright) at each breakpoint:

- **Homepage bento grid** — single column (hero first) → 2-col at `sm:` → 4-col at `lg:`.
- **Mega-menu vs hamburger** — mega-menu only appears at `lg:`+; below that, the hamburger opens the full-screen slide-in panel (`templates/partials/mobile_nav.html`).
- **Listing page filters** — sidebar at `lg:`+, bottom-sheet trigger below it (`templates/products/list.html`).
- **PDP gallery** — swipeable horizontal scroll-snap gallery below `lg:`, thumbnail rail + click/tap-to-zoom main image at `lg:`+.
- **Sticky "Add to Bag" bar** — visible only below `lg:` on the PDP (`templates/products/detail.html`); desktop uses the inline button in the info column instead.
- **Touch targets** — anything tappable uses the `.tap-target` utility (min 44×44px); check icon buttons in the header and mini-cart at the smallest viewport.
- **Safe-area insets** — test on an actual notched-device simulator (or Chrome's device toolbar with a notched preset) to confirm the header/footer/sticky bar respect `env(safe-area-inset-*)`.
- **`prefers-reduced-motion`** — toggle this OS setting and confirm fade-ins/transitions collapse to near-instant (handled globally in `static/css/input.css`).

If you have Playwright available, a quick smoke pass:

```bash
# example: capture each breakpoint for visual review
playwright screenshot --viewport-size=375,800  http://127.0.0.1:8000/ mobile.png
playwright screenshot --viewport-size=820,1100 http://127.0.0.1:8000/ tablet.png
playwright screenshot --viewport-size=1440,900 http://127.0.0.1:8000/ desktop.png
```

---

## Payment: mock checkout → Stripe upgrade path

Checkout currently uses a **mock payment** (`orders/views.py::checkout_review` creates the `Order` directly with `payment_method="mock_card"` and a fake `payment_reference`). No real money moves.

To wire in real payments later:

1. `pip install stripe`, add `STRIPE_SECRET_KEY` / `STRIPE_PUBLISHABLE_KEY` to `.env` and `settings.py`.
2. On `checkout_review` GET, create a Stripe `PaymentIntent` for `cart.total` and pass its `client_secret` to the template.
3. Replace the "Place Order" button with Stripe Elements (or Stripe Checkout redirect); on success, call the existing order-creation code from a webhook (`checkout.session.completed` / `payment_intent.succeeded`) instead of directly from the POST handler, so orders are only created once payment is confirmed server-side.
4. Store the real `payment_reference` (Stripe's `PaymentIntent` ID) instead of the `MOCK-...` placeholder.

---

## Admin notes

- `Product` admin includes inline editing for both `ProductVariant` (size × colorway × stock) and `ProductImage` (per-colorway gallery) — the two things that change most often for a sneaker catalog.
- `ProductVariant` is also registered standalone for quick cross-catalog stock audits.
- Run `python manage.py seed_products --flush` to wipe and regenerate the demo catalog from scratch.

## Known simplifications (by design, for a portfolio/demo scope)

- Seed product images are generated inline (colored SVG placeholders) rather than real photography — swap real images in via the admin's `ProductImage` inline.
- Because seed images are vector SVGs, `srcset`/multiple resolutions don't apply to them. With real raster photography, add `django-imagekit` (or similar) to generate resized variants on upload and extend `templates/products/_card.html` / `_gallery_and_sizes.html` with `srcset`/`sizes` attributes pointing at those variants.
- Tax is a flat configurable rate (`TAX_RATE` in `.env`), not jurisdiction-aware.
- Email sending uses Django's console backend by default in development (password reset emails print to the terminal) — configure `EMAIL_BACKEND` / SMTP settings for production.
