# Polynesia Connect — sitemap

*[Version française plus bas](#version-française)*

Automatic XML sitemap for [www.polynesiaconnect.com](https://www.polynesiaconnect.com), rebuilt every **Monday and Thursday** by GitHub Actions and served by GitHub Pages:

**https://patryk-hd.github.io/polynesiaconnect-sitemap/sitemap.xml**

`crawl.py` visits the site like a search engine (politely: 4 requests at a time) and keeps only the pages that load, are indexable and are their own canonical page: business profiles, events, jobs, classifieds, real estate, categories, cities and static pages. Location × category combination pages, account pages, empty sections and personal accounts are left out. `lastmod` is the day a page's title, description or main heading last changed (`state.json`).

The site's `robots.txt` points to this sitemap (`Sitemap:` line), which is how search engines accept a sitemap hosted on another domain. `changes.json` lists the pages added, changed and removed by the last run.

Run by hand: Actions → Sitemap → Run workflow. Locally: `python3 crawl.py`.

---

## Version française

Sitemap XML automatique de [www.polynesiaconnect.com](https://www.polynesiaconnect.com), reconstruit chaque **lundi et jeudi** par GitHub Actions et publié par GitHub Pages :

**https://patryk-hd.github.io/polynesiaconnect-sitemap/sitemap.xml**

`crawl.py` parcourt le site comme un moteur de recherche (poliment : 4 requêtes à la fois) et ne garde que les pages qui s'affichent, indexables et canoniques : fiches entreprises, événements, offres d'emploi, annonces, immobilier, catégories, communes et pages fixes. Les pages de combinaisons lieu × catégorie, les pages de compte, les rubriques vides et les comptes de particuliers sont exclus. `lastmod` = le jour où le titre, la description ou le titre principal de la page a changé (`state.json`).

Le `robots.txt` du site pointe vers ce sitemap (ligne `Sitemap:`) : c'est ainsi que les moteurs acceptent un sitemap hébergé sur un autre domaine. `changes.json` liste les pages ajoutées, modifiées et retirées au dernier passage.

Lancer à la main : Actions → Sitemap → Run workflow. En local : `python3 crawl.py`.
