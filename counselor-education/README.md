# M.S. in Counselor Education Landing Page

A single-page, static recruitment site for the M.S. in Counselor Education at William Carey University, Tradition Campus. Plain HTML and CSS, no build step, no framework, no dependencies.

## What's in this folder

| File | Purpose |
|------|---------|
| `index.html` | The full landing page |
| `styles.css` | All styling, mobile first |
| `CNAME.placeholder` | Rename to `CNAME` and fill in your custom domain (GitHub Pages only) |

There is no JavaScript. The FAQ accordion uses native `<details>` elements.

## Before you go live: placeholders to fill in

Search `index.html` for the word `PLACEHOLDER`. Every one must be resolved before launch:

1. **Hero image** and **proof section images**: replace the dashed placeholder boxes with real photos (`<img>` tags with alt text).
2. **Three testimonials**: replace with real graduates' own words, names, and context tags, with their written permission. Do not publish the placeholder quotes.
3. **Admission requirements**: pull the current bachelor's degree and GPA thresholds from the WCU admissions criteria page.
4. **Apply now link**: point the `href` at the WCU application page.
5. **Contact form endpoint**: see below.

## The contact form

The form is pre-wired for Netlify Forms with the `data-netlify="true"` attribute.

- **On Netlify**: it works automatically. After deploying, go to your site's dashboard, open Forms, and add a notification that emails submissions to the department address.
- **On GitHub Pages** (or any host without form handling): Netlify Forms will not work. Either point the form's `action` attribute at a form service endpoint of your choice, or delete the `<form>` and uncomment the `mailto:` fallback link just below it (and put the real department email in it).

## Deploy to GitHub Pages

1. Push this folder's contents to a repository (either at the repo root, or keep the folder and set Pages to serve from it).
2. In the repository, go to **Settings > Pages**.
3. Under **Build and deployment**, choose **Deploy from a branch**, pick your branch, and set the folder (`/` for root, or `/docs` if you move these files into a `docs` folder).
4. Save. The site will be live at `https://<username>.github.io/<repo>/` within a minute or two.

### Custom domain on GitHub Pages

1. Rename `CNAME.placeholder` to `CNAME` and replace its contents with just your domain on one line, for example: `counseling.example.edu`
2. Commit and push.
3. At your domain registrar, add a CNAME record pointing your domain (or subdomain) at `<username>.github.io`.
4. Back in **Settings > Pages**, enter the domain under **Custom domain** and enable **Enforce HTTPS** once the certificate is issued.

## Deploy to Netlify

1. Go to your Netlify dashboard and drag this folder onto the deploy drop zone (or connect the repository and set the publish directory to this folder).
2. The site deploys immediately; the contact form is detected and activated automatically.
3. Under **Forms > Notifications**, add an email notification to the department address.

### Custom domain on Netlify

1. In your site's dashboard, go to **Domain management > Add a domain**.
2. Follow the prompts to add your purchased domain and update the DNS records at your registrar (Netlify shows you exactly what to add).
3. Netlify provisions HTTPS automatically. You do not need the `CNAME` file on Netlify; it is only for GitHub Pages.
