<div align="center">

# 👟 HINDSOLE

### *Every step, in hindsight.*

**A premium sneaker drop e-commerce platform** — a curated catalog for collectors, not a discount outlet.

[![Django](https://img.shields.io/badge/Django-5.0-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Tailwind](https://img.shields.io/badge/Tailwind_CSS-3-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![HTMX](https://img.shields.io/badge/HTMX-1.x-3D72D7?style=for-the-badge&logo=htmx&logoColor=white)](https://htmx.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

</div>

---

## ✨ Overview

HINDSOLE is a full-stack Django storefront built around the way sneaker retail actually works — per-size, per-colorway stock, a real cart → checkout → order pipeline, and an admin experience built for fast catalog management. Currency is **INR (₹)**, with India as the default shipping locale.

## 📋 Table of contents

- [Features](#-features)
- [Tech stack](#-tech-stack)
- [Project layout](#-project-layout)
- [Setup](#-setup)
- [Developing templates + Tailwind](#-working-on-templates--tailwind-together)
- [Design tokens](#-design-tokens)
- [Responsiveness testing](#-responsiveness-testing-notes)
- [Admin notes](#-admin-notes)

---

## 🚀 Features

| | |
|---|---|
| 🛍️ **Catalog** | Brands, categories, tags, per-colorway image galleries, size × colorway stock tracking |
| 🛒 **Cart** | Session + DB-backed cart with seamless anonymous → logged-in merge on login |
| 💳 **Checkout** | Shipping → review → mock payment → order, with stock locking against oversells |
| 📦 **Orders** | Full price/size/colorway snapshot per order item, order history, cancellation restock |
| 🎨 **UI** | Bento-grid homepage, HTMX-instant filtering, Alpine-powered galleries & dark mode |
| 🔐 **Auth** | Custom email-based `User` model, address book, profile with default shoe size |
| 🇮🇳 **Locale** | INR pricing, India-first shipping defaults |

## 🛠 Tech stack

| Layer | Choice |
|---|---|
| **Backend** | Django 5.0 (LTS) · Django ORM · custom `User` model (email login) |
| **Database** | PostgreSQL-ready (`JSONField`, indexes) with automatic SQLite fallback for local dev |
| **Frontend** | Django Templates + Tailwind CSS v3 (mobile-first) |
| **Interactivity** | HTMX (cart, filtering, pagination) + Alpine.js (galleries, menus, dark mode, bottom sheets) |

## 📁 Project layout

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

## ⚙️ Setup

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

### 6. Run

```bash
python manage.py runserver
```

Visit **`http://127.0.0.1:8000/`** for the storefront and **`http://127.0.0.1:8000/admin/`** for the catalog admin.

---

## 🎨 Working on templates + Tailwind together

Run these in two terminals while developing:

```bash
npm run watch:css
python manage.py runserver
```

Tailwind scans every `*.html` under `templates/` (see `tailwind.config.js` → `content`), so any new utility class you type in a template is picked up automatically — no separate "register this class" step needed.

---

## 🎨 Design tokens

Defined in `tailwind.config.js` and `static/css/input.css`:

- **Color:** warm off-white/charcoal neutral scale (`neutral-50`…`950`) + a single burnt-orange accent (`accent-500`, `#C3501A`) used only for CTAs, urgency labels, and active states — never as a base UI color.
- **Type:** `Fraunces` (display/serif, wordmark + headings) + `Inter` (UI/body). Fluid sizes (`text-fluid-*`) use `clamp()` so headings scale smoothly from mobile to desktop without breakpoint-jump.
- **Dark mode:** class-based (`darkMode: "class"`), toggled via the header sun/moon icon, persisted in `localStorage` and (for logged-in users) on the `User.dark_mode_enabled` field.

---

## 📱 Responsiveness testing notes

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

## 🗂 Admin notes

- `Product` admin includes inline editing for both `ProductVariant` (size × colorway × stock) and `ProductImage` (per-colorway gallery) — the two things that change most often for a sneaker catalog.
- `ProductVariant` is also registered standalone for quick cross-catalog stock audits.
- Run `python manage.py seed_products --flush` to wipe and regenerate the demo catalog from scratch.

---

<div align="center">

Built with 🧡 as part of the CodeAlpha internship program.

</div>
