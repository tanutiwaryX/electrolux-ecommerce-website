# ElectroLux — MCA First-Semester Project

A responsive premium electronics e-commerce demonstration built with Python Flask, Flask-SQLAlchemy, SQLite, HTML, CSS and JavaScript. It includes customer accounts, a session cart, demo checkout, order tracking and an administrator dashboard.

> **Academic demo only:** checkout does not collect card details and does not process real payments. Shipment status is maintained manually in the admin panel. This is not production-hardened commerce software.

## Features
- Responsive storefront with categories, featured products, product detail pages, keyword search, price filters, sorting and pagination.
- Customer registration/login with Werkzeug password hashing, profile editing, cart management and order history.
- Demo checkout saves shipping information and order items to SQLite; stock is reduced on order and restored if an admin cancels it.
- Admin dashboard, product CRUD, order status management and customer list.
- CSRF protection for POST forms, ORM queries, validation and role-based access decorators.
- Database and sample catalogue are created automatically on first launch. Seeding checks existing records to avoid duplicate products on restart.

## Requirements
- Python 3.10 or newer (Python 3.11+ recommended)
- VS Code (recommended)
- Internet connection for remote Unsplash product photography and Google Fonts. A local SVG placeholder is used if a product image fails to load.

## Windows + VS Code setup

1. **Extract the ZIP.** In VS Code choose **File → Open Folder** and select `ElectroLux_MCA_Project`.
2. **Open the terminal in the project root.** Choose **Terminal → New Terminal**. Make sure the current folder contains both `app.py` and `requirements.txt`. If needed, run `cd path\to\ElectroLux_MCA_Project`.
3. Create the virtual environment:
   ```powershell
   py -m venv .venv
   ```
4. Activate it in PowerShell:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
   If PowerShell blocks activation, use a one-session policy bypass:
   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\.venv\Scripts\Activate.ps1
   ```
   **Command Prompt alternative:**
   ```bat
   .venv\Scripts\activate.bat
   ```
5. Install dependencies:
   ```powershell
   python -m pip install -r requirements.txt
   ```
6. Start the app:
   ```powershell
   python app.py
   ```
7. Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser. The SQLite database is automatically created at `instance/electrolux.db` on first launch.

## Demo administrator account
- **Email:** `admin@electrolux.demo`
- **Password:** `ElectroLuxDemo!2026`

Sign in using the normal Sign in page; administrator accounts are sent to the admin dashboard. Change the demo password for any shared environment. The password is stored as a Werkzeug secure hash, never as plain text. If `DEMO_ADMIN_PASSWORD` is set before the very first database seed, that value is used instead.

## Environment configuration
Copy `.env.example` to `.env` if desired, then set a long random `SECRET_KEY`. Example:
```env
SECRET_KEY=replace-with-a-long-random-secret
DATABASE_URL=
DEMO_ADMIN_PASSWORD=use-a-strong-demo-password
```
- `SECRET_KEY`: required for secure sessions in any deployed environment. The built-in fallback is for local classroom use only; do not deploy with it.
- `DATABASE_URL`: optional. Leave empty to use the local SQLite file. The app creates its parent `instance` directory automatically.
- `DEMO_ADMIN_PASSWORD`: optional seed-time admin password. Changing this after the admin account has already been created does not reset the existing password.
- `FLASK_DEBUG=true`: optional local debugging only. Keep disabled for shared or deployed use.

## Troubleshooting

### `requirements.txt` not found
The terminal is not in the project root. Run `dir` (PowerShell/Command Prompt) and verify `app.py` and `requirements.txt` appear. In VS Code use **File → Open Folder** to open the extracted `ElectroLux_MCA_Project` folder, then open a new terminal. Do not run pip from the ZIP viewer or a parent folder.

### Python is not recognized
Install Python from [python.org](https://www.python.org/downloads/windows/) and enable **Add Python to PATH** during setup. Close and reopen VS Code. Test `py --version` or `python --version`. On Windows, `py` may work even when `python` does not; activate the environment and then use `python`.

### Port 5000 is already in use
Stop the other application using port 5000, or change the final line in `app.py` to `app.run(port=5001, debug=...)`, then visit `http://127.0.0.1:5001`. Do not run multiple copies of this app simultaneously against the same database.

### PowerShell says scripts are disabled
Use the temporary process-scoped execution-policy commands shown in the activation step, or use the Command Prompt activation alternative.

### Product images do not load
The site uses remote Unsplash image URLs. An internet connection is needed for these images; failed images fall back to a local ElectroLux placeholder. Product browsing and checkout still work without remote images.

### Database or import error
Ensure the virtual environment is activated and run `python -m pip install -r requirements.txt` again. The app creates `instance/electrolux.db` automatically. To reset demo data, stop the app and delete `instance/electrolux.db`, then run `python app.py` again (this deletes local demo orders/accounts).

## Project structure
```text
ElectroLux_MCA_Project/
├── app.py
├── requirements.txt
├── README.md
├── .env.example
├── .gitignore
├── instance/                  # created automatically on first run
├── static/
│   ├── css/style.css
│   ├── js/main.js
│   └── img/product-placeholder.svg
└── templates/
    ├── base.html
    ├── _product_card.html
    ├── index.html
    ├── products.html
    ├── product_detail.html
    ├── auth.html
    ├── cart.html
    ├── checkout.html
    ├── orders.html
    ├── order_detail.html
    ├── account.html
    ├── error.html
    └── admin/
        ├── base_admin.html
        ├── dashboard.html
        ├── products.html
        ├── product_form.html
        ├── orders.html
        └── customers.html
```

## Academic extension ideas
Add unit tests with pytest, email verification, product reviews, an audit log, or a payment gateway sandbox only after reviewing its security and privacy requirements. This version intentionally uses a local demo checkout.


## Visual design refresh
The storefront uses a premium editorial style: deep midnight/navy hero surfaces, electric-blue accents, softer product image stages, more spacious cards, refined form controls, and a responsive admin studio. The design remains CSS-only and does not add frontend package dependencies.
